import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { BackendStack } from '../lib/backend-stack';

let template: Template;

beforeAll(() => {
  const app = new cdk.App({
    context: {
      githubToken: 'test-token',
      githubOwner: 'test-owner',
      githubRepo: 'test-repo',
      projectPrefix: 'test-guide',
    },
  });
  const stack = new BackendStack(app, 'BackendStack');
  template = Template.fromStack(stack);
});

// 34.1 Test S3 Documents Bucket has encryption, BPA, and enforceSSL
describe('S3 Documents Bucket', () => {
  test('has S3-managed encryption enabled', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketEncryption: {
        ServerSideEncryptionConfiguration: [
          {
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256',
            },
          },
        ],
      },
    });
  });

  test('has Block Public Access enabled', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test('has enforceSSL via bucket policy', () => {
    template.hasResourceProperties('AWS::S3::BucketPolicy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Deny',
            Condition: {
              Bool: { 'aws:SecureTransport': 'false' },
            },
          }),
        ]),
      },
    });
  });
});

// 34.2 Test S3 Vectors Bucket and Vector Index are created with correct dimensions
describe('S3 Vectors Bucket and Vector Index', () => {
  test('S3 Vectors Bucket custom resource is created', () => {
    template.hasResourceProperties('AWS::CloudFormation::CustomResource', {
      vectorBucketName: Match.objectLike({
        'Fn::Join': Match.arrayWith([
          '',
          Match.arrayWith([
            'test-guide-vectors-',
          ]),
        ]),
      }),
    });
  });

  test('Vector Index is created with 1024 dimensions and cosine metric', () => {
    template.hasResourceProperties('AWS::CloudFormation::CustomResource', {
      indexName: 'test-guide-vector-index',
      dimension: 1024,
      distanceMetric: 'cosine',
      dataType: 'float32',
    });
  });
});

// 34.3 Test Knowledge Base is created with S3_VECTORS storage config
describe('Knowledge Base', () => {
  test('is created with correct name and embedding configuration', () => {
    template.hasResourceProperties('AWS::CloudFormation::CustomResource', {
      knowledgeBaseName: 'test-guide-knowledge-base',
      knowledgeBaseConfiguration: Match.objectLike({
        embeddingDataType: 'FLOAT32',
        dimensions: '1024',
      }),
    });
  });

  test('references vector bucket and index ARNs', () => {
    template.hasResourceProperties('AWS::CloudFormation::CustomResource', {
      knowledgeBaseName: 'test-guide-knowledge-base',
      vectorBucketArn: Match.anyValue(),
      indexArn: Match.anyValue(),
    });
  });
});

// 34.4 Test Chat Lambda has correct runtime, timeout, memory
describe('Chat Lambda', () => {
  test('has Python 3.13 runtime', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      Runtime: 'python3.13',
    });
  });

  test('has 5 minute timeout', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      Timeout: 300,
    });
  });

  test('has 512 MB memory', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      MemorySize: 512,
    });
  });
});

// 34.5 Test Chat Lambda environment variables are set correctly
describe('Chat Lambda environment variables', () => {
  test('has required environment variables', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      Environment: {
        Variables: Match.objectLike({
          MODEL_ID: 'us.amazon.nova-lite-v1:0',
          NUM_KB_RESULTS: '5',
          MAX_TOKENS: '4096',
          TEMPERATURE: '0.7',
          LOG_LEVEL: 'INFO',
        }),
      },
    });
  });

  test('has KNOWLEDGE_BASE_ID set', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      Environment: {
        Variables: Match.objectLike({
          KNOWLEDGE_BASE_ID: Match.anyValue(),
        }),
      },
    });
  });

  test('has CORS_ALLOWED_ORIGIN set', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: 'test-guide-chat',
      Environment: {
        Variables: Match.objectLike({
          CORS_ALLOWED_ORIGIN: Match.anyValue(),
        }),
      },
    });
  });
});

// 34.6 Test ChatLambdaRole has bedrock:Retrieve and bedrock:InvokeModelWithResponseStream permissions
describe('ChatLambdaRole permissions', () => {
  test('has bedrock:Retrieve permission', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: 'bedrock:Retrieve',
            Effect: 'Allow',
          }),
        ]),
      },
    });
  });

  test('has bedrock:InvokeModelWithResponseStream permission', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: 'bedrock:InvokeModelWithResponseStream',
            Effect: 'Allow',
          }),
        ]),
      },
    });
  });
});

// 34.7 Test REST API V1 has /chat POST method with Lambda integration
describe('REST API V1', () => {
  test('REST API is created with correct name', () => {
    template.hasResourceProperties('AWS::ApiGateway::RestApi', {
      Name: 'test-guide-chat-api',
    });
  });

  test('has /chat resource', () => {
    template.hasResourceProperties('AWS::ApiGateway::Resource', {
      PathPart: 'chat',
    });
  });

  test('has POST method on /chat with Lambda proxy integration', () => {
    template.hasResourceProperties('AWS::ApiGateway::Method', {
      HttpMethod: 'POST',
      Integration: {
        Type: 'AWS_PROXY',
      },
    });
  });
});

// 34.8 Test API Gateway has access logging enabled
describe('API Gateway access logging', () => {
  test('has access log destination configured on stage', () => {
    template.hasResourceProperties('AWS::ApiGateway::Stage', {
      AccessLogSetting: {
        DestinationArn: Match.anyValue(),
      },
    });
  });

  test('has CloudWatch log group for API access logs', () => {
    template.hasResourceProperties('AWS::Logs::LogGroup', {
      LogGroupName: '/aws/apigateway/test-guide-api',
    });
  });
});

// 34.9 Test Amplify App has WEB_COMPUTE platform
describe('Amplify App', () => {
  test('has WEB_COMPUTE platform', () => {
    template.hasResourceProperties('AWS::Amplify::App', {
      Name: 'test-guide-frontend',
      Platform: 'WEB_COMPUTE',
    });
  });
});

// 34.10 Test CfnOutputs exist for ApiUrl, AmplifyUrl, KnowledgeBaseId, DocumentsBucketName
describe('CfnOutputs', () => {
  test('ApiUrl output exists', () => {
    template.hasOutput('ApiUrl', {
      Value: Match.anyValue(),
    });
  });

  test('AmplifyUrl output exists', () => {
    template.hasOutput('AmplifyUrl', {
      Value: Match.anyValue(),
    });
  });

  test('KnowledgeBaseId output exists', () => {
    template.hasOutput('KnowledgeBaseId', {
      Value: Match.anyValue(),
    });
  });

  test('DocumentsBucketName output exists', () => {
    template.hasOutput('DocumentsBucketName', {
      Value: Match.anyValue(),
    });
  });
});
