import * as cdk from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId } from 'aws-cdk-lib/custom-resources';
import { Bucket as S3VectorsBucket, Index as VectorIndex, KnowledgeBase } from 'cdk-s3-vectors';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';
import * as os from 'os';
import * as path from 'path';

export class BackendStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ---------------------------------------------------------------
    // Context variable validation
    // ---------------------------------------------------------------
    const requiredContextVars = ['githubToken', 'githubOwner', 'githubRepo', 'projectPrefix'] as const;
    const context: Record<string, string> = {};

    for (const key of requiredContextVars) {
      const value = this.node.tryGetContext(key);
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        throw new Error(
          `Missing required CDK context variable: "${key}". ` +
          `Provide it via cdk.json context block or -c ${key}=<value> on the CLI.`
        );
      }
      context[key] = value;
    }

    const { githubToken, githubOwner, githubRepo, projectPrefix } = context;

    // ---------------------------------------------------------------
    // S3 Documents Bucket — stores academic advising documents (PDF, TXT, HTML)
    // Admin upload convention: use the docs/ prefix for all documents
    //   e.g. aws s3 cp catalog.pdf s3://<bucket>/docs/catalog.pdf
    // The Bedrock Knowledge Base data source is configured to read from docs/
    // ---------------------------------------------------------------
    const documentsBucket = new s3.Bucket(this, 'DocumentsBucket', {
      bucketName: `${projectPrefix}-documents-${this.account}-${this.region}`,
      enforceSSL: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      autoDeleteObjects: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ADR: S3 access logging suppressed | Dev-lifecycle bucket with no sensitive data at rest; access is audited via CloudTrail
    NagSuppressions.addResourceSuppressions(documentsBucket, [
      { id: 'AwsSolutions-S1', reason: 'ADR: S3 access logging not required | Dev-lifecycle bucket; CloudTrail provides access auditing' },
    ]);

    // Suppress cdk-nag findings for the CDK-managed auto-delete custom resource Lambda
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/Custom::S3AutoDeleteObjectsCustomResourceProvider/Role', [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed custom resource for auto-delete uses AWSLambdaBasicExecutionRole' },
      { id: 'AwsSolutions-IAM5', reason: 'CDK-managed custom resource requires wildcard for S3 object deletion' },
    ]);
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/Custom::S3AutoDeleteObjectsCustomResourceProvider/Handler', [
      { id: 'AwsSolutions-L1', reason: 'CDK-managed custom resource Lambda runtime is controlled by CDK framework' },
    ]);

    // ---------------------------------------------------------------
    // S3 Vectors Bucket — vector store for Bedrock Knowledge Base embeddings
    // ---------------------------------------------------------------
    const vectorsBucket = new S3VectorsBucket(this, 'VectorsBucket', {
      vectorBucketName: `${projectPrefix}-vectors-${this.account}-${this.region}`,
    });

    // ---------------------------------------------------------------
    // Vector Index — 1024-dim cosine index for Titan Embed V2 embeddings
    // ---------------------------------------------------------------
    const vectorIndex = new VectorIndex(this, 'VectorIndex', {
      vectorBucketName: vectorsBucket.vectorBucketName,
      indexName: `${projectPrefix}-vector-index`,
      dimension: 1024,
      distanceMetric: 'cosine',
      dataType: 'float32',
      metadataConfiguration: {
        nonFilterableMetadataKeys: [
          'AMAZON_BEDROCK_TEXT',
          'AMAZON_BEDROCK_METADATA',
        ],
      },
    });

    // ADR: cdk-nag suppressions for cdk-s3-vectors internal constructs | Package creates custom resource Lambdas and IAM roles internally
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/VectorsBucket', [
      { id: 'AwsSolutions-IAM5', reason: 'Internal construct managed by cdk-s3-vectors package' },
      { id: 'AwsSolutions-IAM4', reason: 'Internal construct managed by cdk-s3-vectors package' },
      { id: 'AwsSolutions-L1', reason: 'Internal construct managed by cdk-s3-vectors package' },
    ], true);
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/VectorIndex', [
      { id: 'AwsSolutions-IAM5', reason: 'Internal construct managed by cdk-s3-vectors package' },
      { id: 'AwsSolutions-IAM4', reason: 'Internal construct managed by cdk-s3-vectors package' },
      { id: 'AwsSolutions-L1', reason: 'Internal construct managed by cdk-s3-vectors package' },
    ], true);

    // ---------------------------------------------------------------
    // Bedrock Knowledge Base — S3_VECTORS storage with Titan Embed V2
    // ADR: cdk-s3-vectors KnowledgeBase L3 construct | Handles custom resource for KB creation with S3_VECTORS storage type
    // ---------------------------------------------------------------
    const embeddingModelArn = `arn:aws:bedrock:${this.region}::foundation-model/amazon.titan-embed-text-v2:0`;

    const knowledgeBase = new KnowledgeBase(this, 'KnowledgeBase', {
      knowledgeBaseName: `${projectPrefix}-knowledge-base`,
      vectorBucketArn: vectorsBucket.vectorBucketArn,
      indexArn: vectorIndex.indexArn,
      knowledgeBaseConfiguration: {
        embeddingModelArn,
        embeddingDataType: 'FLOAT32',
        dimensions: '1024',
      },
      description: 'ASU academic advising knowledge base backed by S3 Vectors',
    });

    // Grant KB role read access to Documents Bucket for ingestion
    documentsBucket.grantRead(knowledgeBase.role);

    // cdk-nag suppressions for KnowledgeBase internal constructs
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/KnowledgeBase', [
      { id: 'AwsSolutions-IAM5', reason: 'ADR: S3 Vectors wildcard actions on scoped resources | Resource-level ARNs used for index and bucket; KMS wildcard required by Bedrock service' },
      { id: 'AwsSolutions-IAM4', reason: 'Internal construct managed by cdk-s3-vectors KnowledgeBase' },
      { id: 'AwsSolutions-L1', reason: 'Internal construct managed by cdk-s3-vectors KnowledgeBase' },
    ], true);

    // ---------------------------------------------------------------
    // Knowledge Base Data Source — S3 source with docs/ prefix and fixed-size chunking
    // ---------------------------------------------------------------
    const dataSource = new bedrock.CfnDataSource(this, 'KnowledgeBaseDataSource', {
      name: `${projectPrefix}-kb-data-source`,
      knowledgeBaseId: knowledgeBase.knowledgeBaseId,
      dataSourceConfiguration: {
        type: 'S3',
        s3Configuration: {
          bucketArn: documentsBucket.bucketArn,
          inclusionPrefixes: ['docs/'],
        },
      },
      // ADR: Fixed-size chunking 525 tokens / 15% overlap | Balances retrieval precision with context window for academic documents
      vectorIngestionConfiguration: {
        chunkingConfiguration: {
          chunkingStrategy: 'FIXED_SIZE',
          fixedSizeChunkingConfiguration: {
            maxTokens: 525,
            overlapPercentage: 15,
          },
        },
      },
      description: 'S3 data source for ASU academic advising documents (docs/ prefix)',
    });

    // ---------------------------------------------------------------
    // Chat Lambda — handles /chat requests (validate → retrieve → stream)
    // ---------------------------------------------------------------

    // ADR: Dynamic arch detection | Supports Apple Silicon and Intel Macs
    const hostArch = os.arch();
    const lambdaArch = hostArch === 'arm64' ? lambda.Architecture.ARM_64 : lambda.Architecture.X86_64;

    const chatLambda = new lambda.Function(this, 'ChatLambda', {
      functionName: `${projectPrefix}-chat`,
      // ADR: Python 3.13 instead of 3.12 | cdk-nag AwsSolutions-L1 requires latest runtime
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'chat')),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      architecture: lambdaArch,
      environment: {
        KNOWLEDGE_BASE_ID: knowledgeBase.knowledgeBaseId,
        MODEL_ID: 'us.amazon.nova-lite-v1:0',
        NUM_KB_RESULTS: '5',
        MAX_TOKENS: '4096',
        TEMPERATURE: '0.7',
        LOG_LEVEL: 'INFO',
        // CORS_ALLOWED_ORIGIN set after Amplify app is created (Task 9)
      },
    });

    // ---------------------------------------------------------------
    // ChatLambdaRole — least-privilege permissions for KB retrieval and model invocation
    // ---------------------------------------------------------------

    // Grant bedrock:Retrieve on the Knowledge Base ARN
    chatLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:Retrieve'],
      resources: [
        `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/${knowledgeBase.knowledgeBaseId}`,
      ],
    }));

    // ADR: Cross-region Bedrock ARNs for Nova Lite | Cross-region inference profile routes to us-east-1, us-east-2, us-west-2
    chatLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModelWithResponseStream'],
      resources: [
        'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0',
        'arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-lite-v1:0',
        'arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-lite-v1:0',
      ],
    }));

    // cdk-nag suppressions for Chat Lambda
    NagSuppressions.addResourceSuppressions(chatLambda, [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed Lambda execution role uses AWSLambdaBasicExecutionRole' },
    ], true);
    NagSuppressions.addResourceSuppressions(chatLambda, [
      { id: 'AwsSolutions-IAM5', reason: 'ADR: Cross-region Bedrock ARNs | Nova Lite cross-region inference profile routes requests to us-east-1, us-east-2, us-west-2' },
    ], true);

    // ---------------------------------------------------------------
    // REST API V1 — /chat endpoint with streaming support
    // ADR: REST API V1 over HTTP API V2 | Required for Lambda response streaming (Nov 2025)
    // ---------------------------------------------------------------

    const apiLogGroup = new logs.LogGroup(this, 'ApiAccessLogs', {
      logGroupName: `/aws/apigateway/${projectPrefix}-api`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ---------------------------------------------------------------
    // Amplify App — WEB_COMPUTE hosting for Next.js SSR frontend
    // ADR: WEB_COMPUTE platform with no customRules | SSR routing handled by Amplify compute layer; SPA rewrites break SSR
    // ---------------------------------------------------------------
    const amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: `${projectPrefix}-frontend`,
      repository: `https://github.com/${githubOwner}/${githubRepo}`,
      oauthToken: githubToken,
      platform: 'WEB_COMPUTE',
      buildSpec: [
        'version: 1',
        'applications:',
        '  - appRoot: frontend',
        '    frontend:',
        '      phases:',
        '        preBuild:',
        '          commands:',
        '            - npm ci',
        '        build:',
        '          commands:',
        '            - npm run build',
        '      artifacts:',
        '        baseDirectory: .next',
        '        files:',
        '          - "**/*"',
        '      cache:',
        '        paths:',
        '          - node_modules/**/*',
        '          - .next/cache/**/*',
      ].join('\n'),
      environmentVariables: [
        { name: 'AMPLIFY_MONOREPO_APP_ROOT', value: 'frontend' },
      ],
    });

    const amplifyAppUrl = `https://main.${amplifyApp.attrAppId}.amplifyapp.com`;

    // ---------------------------------------------------------------
    // Amplify Branch (main) — production branch with backend env vars
    // ---------------------------------------------------------------
    const amplifyMainBranch = new amplify.CfnBranch(this, 'AmplifyMainBranch', {
      appId: amplifyApp.attrAppId,
      branchName: 'main',
      enableAutoBuild: true,
      stage: 'PRODUCTION',
      environmentVariables: [
        { name: 'AMPLIFY_MONOREPO_APP_ROOT', value: 'frontend' },
        { name: 'NEXT_PUBLIC_API_URL', value: 'placeholder-replaced-below' },
      ],
    });

    // ---------------------------------------------------------------
    // Wire Amplify URL back to Chat Lambda CORS (Task 9)
    // ---------------------------------------------------------------
    chatLambda.addEnvironment('CORS_ALLOWED_ORIGIN', amplifyAppUrl);

    // ---------------------------------------------------------------
    // REST API V1 — /chat endpoint with streaming support (Task 9: CORS uses real Amplify URL)
    // ---------------------------------------------------------------
    const corsAllowedOrigins = [
      amplifyAppUrl,
      'http://localhost:3000',
    ];

    const api = new apigateway.RestApi(this, 'ChatApi', {
      restApiName: `${projectPrefix}-chat-api`,
      description: 'ASU Academic Advising Chatbot REST API with streaming support',
      deployOptions: {
        stageName: 'prod',
        accessLogDestination: new apigateway.LogGroupLogDestination(apiLogGroup),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields(),
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: corsAllowedOrigins,
        allowMethods: ['POST', 'OPTIONS'],
        allowHeaders: ['Content-Type'],
      },
      cloudWatchRole: true,
      cloudWatchRoleRemovalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const chatResource = api.root.addResource('chat');
    chatResource.addMethod('POST', new apigateway.LambdaIntegration(chatLambda, {
      proxy: true,
    }));

    // Now that the API is created, update the Amplify branch NEXT_PUBLIC_API_URL
    amplifyMainBranch.addPropertyOverride(
      'EnvironmentVariables',
      [
        { Name: 'AMPLIFY_MONOREPO_APP_ROOT', Value: 'frontend' },
        { Name: 'NEXT_PUBLIC_API_URL', Value: `${api.url}chat` },
      ],
    );

    // ADR: Public endpoint without auth | Academic advising chatbot is public by design (no login required)
    NagSuppressions.addResourceSuppressions(chatResource, [
      { id: 'AwsSolutions-APIG4', reason: 'Public academic advising endpoint — no authentication by design' },
      { id: 'AwsSolutions-COG4', reason: 'Public academic advising endpoint — no authentication by design' },
    ], true);

    // ADR: Request validation in Lambda | Input validation handled in Chat Lambda with detailed error messages
    NagSuppressions.addResourceSuppressions(api, [
      { id: 'AwsSolutions-APIG2', reason: 'Request validation handled in Chat Lambda with detailed error responses' },
    ]);

    // ADR: WAF not required | Public academic advising chatbot with low-risk data; API Gateway throttling provides sufficient protection
    NagSuppressions.addResourceSuppressions(api, [
      { id: 'AwsSolutions-APIG3', reason: 'Public academic advising chatbot — WAF not required for low-risk public endpoint' },
    ], true);

    NagSuppressions.addResourceSuppressions(api, [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed API Gateway CloudWatch role uses AWS managed policy for log pushing' },
    ], true);

    // ---------------------------------------------------------------
    // CustomResource — trigger initial KB sync on stack creation (Task 10)
    // ---------------------------------------------------------------
    const triggerKbSync = new AwsCustomResource(this, 'TriggerKbSync', {
      onCreate: {
        service: 'BedrockAgent',
        action: 'startIngestionJob',
        parameters: {
          knowledgeBaseId: knowledgeBase.knowledgeBaseId,
          dataSourceId: dataSource.attrDataSourceId,
        },
        physicalResourceId: PhysicalResourceId.of(
          `${knowledgeBase.knowledgeBaseId}-${dataSource.attrDataSourceId}-initial-sync`,
        ),
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ['bedrock:StartIngestionJob'],
          resources: [
            `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/${knowledgeBase.knowledgeBaseId}`,
          ],
        }),
      ]),
    });

    NagSuppressions.addResourceSuppressions(triggerKbSync, [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed AwsCustomResource Lambda uses AWSLambdaBasicExecutionRole' },
      { id: 'AwsSolutions-IAM5', reason: 'CDK-managed AwsCustomResource framework uses wildcard for log group creation' },
      { id: 'AwsSolutions-L1', reason: 'CDK-managed AwsCustomResource Lambda runtime is controlled by CDK framework' },
    ], true);

    // ---------------------------------------------------------------
    // CustomResource — trigger Amplify build on every deploy (Task 11)
    // ADR: AwsCustomResource with Date.now() PhysicalResourceId | Forces execution on every CDK deploy since enableAutoBuild only fires on git pushes
    // ---------------------------------------------------------------
    const triggerAmplifyBuild = new AwsCustomResource(this, 'TriggerAmplifyBuild', {
      onCreate: {
        service: 'Amplify',
        action: 'startJob',
        parameters: {
          appId: amplifyApp.attrAppId,
          branchName: 'main',
          jobType: 'RELEASE',
        },
        physicalResourceId: PhysicalResourceId.of(
          `${amplifyApp.attrAppId}-main-${Date.now()}`,
        ),
      },
      onUpdate: {
        service: 'Amplify',
        action: 'startJob',
        parameters: {
          appId: amplifyApp.attrAppId,
          branchName: 'main',
          jobType: 'RELEASE',
        },
        physicalResourceId: PhysicalResourceId.of(
          `${amplifyApp.attrAppId}-main-${Date.now()}`,
        ),
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ['amplify:StartJob'],
          resources: [
            `arn:aws:amplify:${this.region}:${this.account}:apps/${amplifyApp.attrAppId}/branches/main/jobs/*`,
          ],
        }),
      ]),
    });

    // Ensure Amplify build triggers after the branch and API are fully created
    triggerAmplifyBuild.node.addDependency(amplifyMainBranch);
    triggerAmplifyBuild.node.addDependency(api);

    NagSuppressions.addResourceSuppressions(triggerAmplifyBuild, [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed AwsCustomResource Lambda uses AWSLambdaBasicExecutionRole' },
      { id: 'AwsSolutions-IAM5', reason: 'CDK-managed AwsCustomResource framework uses wildcard for log group creation; Amplify job ARN requires wildcard for job ID' },
      { id: 'AwsSolutions-L1', reason: 'CDK-managed AwsCustomResource Lambda runtime is controlled by CDK framework' },
    ], true);

    // cdk-nag suppression for the shared AwsCustomResource singleton Lambda role
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/AWS679f53fac002430cb0da5b7982bd2287/ServiceRole/Resource', [
      { id: 'AwsSolutions-IAM4', reason: 'CDK-managed AwsCustomResource singleton Lambda uses AWSLambdaBasicExecutionRole' },
    ]);
    NagSuppressions.addResourceSuppressionsByPath(this, '/BackendStack/AWS679f53fac002430cb0da5b7982bd2287/Resource', [
      { id: 'AwsSolutions-L1', reason: 'CDK-managed AwsCustomResource singleton Lambda runtime is controlled by CDK framework' },
    ]);

    // ---------------------------------------------------------------
    // Stack Outputs (Task 12)
    // ---------------------------------------------------------------
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'REST API Gateway URL',
    });

    new cdk.CfnOutput(this, 'AmplifyUrl', {
      value: amplifyAppUrl,
      description: 'Amplify App default domain URL',
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: knowledgeBase.knowledgeBaseId,
      description: 'Bedrock Knowledge Base ID',
    });

    new cdk.CfnOutput(this, 'DocumentsBucketName', {
      value: documentsBucket.bucketName,
      description: 'S3 Documents Bucket name',
    });
  }
}
