# Sample Academic Documents

Sample ASU academic advising documents for testing the Bedrock Knowledge Base RAG pipeline. These are **not official ASU content** — they are realistic samples for development and testing.

## Documents

| File | Description |
|------|-------------|
| `cse-course-catalog.md` | CSE course catalog excerpt with prerequisites |
| `bs-computer-science-requirements.md` | BS in Computer Science degree requirements |
| `academic-standing-policy.md` | Academic standing, probation, and advising policies |

## Upload to S3

Upload documents to the `docs/` prefix in the Documents Bucket:

```bash
# Get the bucket name from CDK stack outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name BackendStack \
  --query "Stacks[0].Outputs[?OutputKey=='DocumentsBucketName'].OutputValue" \
  --output text)

# Upload all sample documents
aws s3 cp backend/sample-docs/ s3://$BUCKET_NAME/docs/ --recursive --exclude "README.md"
```

## Sync Knowledge Base

After uploading, trigger a Knowledge Base ingestion job to index the new documents:

```bash
# Get the Knowledge Base ID from CDK stack outputs
KB_ID=$(aws cloudformation describe-stacks \
  --stack-name BackendStack \
  --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseId'].OutputValue" \
  --output text)

# Get the data source ID
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id $KB_ID \
  --query "dataSourceSummaries[0].dataSourceId" \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

## Notes

- The CDK stack triggers an initial KB sync on deployment via a CustomResource (`TriggerKbSync`). If documents are already in the bucket at deploy time, they will be indexed automatically.
- The Knowledge Base data source is configured to only read from the `docs/` prefix. Files outside this prefix are ignored.
- Chunking is configured as fixed-size: 525 tokens with 15% overlap.
- After ingestion completes (typically 1-2 minutes for small document sets), the chatbot can retrieve relevant passages from these documents.
