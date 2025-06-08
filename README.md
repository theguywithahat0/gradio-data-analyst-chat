# Data Analyst Chat Interface

A modern Gradio-based web interface for interacting with the GCP Data Analyst Agent. Provides chat functionality, file uploads, result exports, and conversation history for users from C-level executives to data scientists.

## 🚀 Features

- **💬 Chat Interface**: Clean, intuitive chat with the AI data analyst
- **📁 File Upload**: Support for CSV, Excel, JSON, Parquet files
- **📊 Export Results**: Export conversations in JSON, CSV, or HTML format
- **📜 History Management**: Persistent conversation history with Firestore
- **🔐 Google SSO**: Secure authentication via Identity-Aware Proxy
- **👥 Multi-User**: User-specific conversations and file handling
- **📱 Responsive**: Works on desktop and mobile devices

## 🏗️ Architecture

```
User Browser → IAP → Cloud Run → Gradio App → Vertex AI Agent → BigQuery
                                    ↓
                                Firestore (Chat History)
                                    ↓
                                Cloud Storage (Files)
```

## 🛠️ Local Development

### Prerequisites

- Python 3.11+
- Google Cloud SDK
- Access to GCP project with Vertex AI enabled

### Setup

1. **Clone and navigate to directory**:
   ```bash
   cd gradio-data-analyst-chat
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Set up Google Cloud authentication**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

5. **Run locally**:
   ```bash
   python -m app.main
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Required |
| `GOOGLE_CLOUD_LOCATION` | Region for Vertex AI | `europe-west1` |
| `AGENT_NAME` | Reasoning Engine agent name | Optional |
| `USE_IAP` | Enable IAP authentication | `true` |
| `ALLOWED_DOMAINS` | Comma-separated allowed domains | Required |
| `USE_FIRESTORE` | Use Firestore for history | `true` |
| `PORT` | Application port | `8080` |

## 🐳 Docker Deployment

### Build and run locally:

```bash
# Build the image
docker build -t gradio-chat-app .

# Run the container
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -v ~/.config/gcloud:/home/gradio/.config/gcloud:ro \
  gradio-chat-app
```

### Environment setup for container:

```bash
# Create environment file
cp .env.example .env

# Run with environment file
docker run --env-file .env -p 8080:8080 gradio-chat-app
```

## ☁️ Cloud Run Deployment

### Using gcloud CLI:

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT/gradio-chat-app
gcloud run deploy gradio-chat-app \
  --image gcr.io/YOUR_PROJECT/gradio-chat-app \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT
```

### Using Cloud Build:

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/gradio-chat-app', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/gradio-chat-app']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'gradio-chat-app'
      - '--image'
      - 'gcr.io/$PROJECT_ID/gradio-chat-app'
      - '--region'
      - 'europe-west1'
      - '--platform'
      - 'managed'
```

## 🔐 Authentication Setup

### Identity-Aware Proxy (Production)

1. **Enable IAP**:
   ```bash
   gcloud iap web enable --resource-type=cloud-run \
     --service=gradio-chat-app \
     --region=europe-west1
   ```

2. **Add allowed users/groups**:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member='domain:yourdomain.com' \
     --role='roles/iap.httpsResourceAccessor'
   ```

### Development Mode

Set `USE_IAP=false` in your `.env` file to use mock authentication.

## 📁 File Upload Support

| Format | Extensions | Features |
|--------|------------|----------|
| CSV | `.csv` | Encoding detection, data type inference |
| Excel | `.xlsx`, `.xls` | Multi-sheet support, data analysis |
| JSON | `.json` | Nested structure analysis |
| Parquet | `.parquet` | Optimized for large datasets |
| Text | `.txt` | Line and character counting |

**Size Limit**: 100MB (configurable via `MAX_FILE_SIZE`)

## 💾 Data Storage

### Chat History
- **Production**: Cloud Firestore
- **Development**: Local JSON files
- **Structure**: User-specific conversations with metadata

### File Uploads
- **Location**: `./uploads/{user_id}/` 
- **Naming**: `{timestamp}_{original_name}`
- **Cleanup**: Manual (can be automated)

### Exports
- **Location**: `./exports/`
- **Formats**: JSON, CSV, HTML
- **Retention**: 7 days (configurable)

## 🔧 Configuration

### Firestore Setup

1. **Enable Firestore**:
   ```bash
   gcloud firestore databases create --region=europe-west1
   ```

2. **Set up collections**:
   - `chat_conversations`: Conversation metadata
   - `chat_messages`: Individual messages

### Agent Configuration

The app automatically detects if a Vertex AI Reasoning Engine is configured:

- **With Agent**: Full functionality with real AI responses
- **Without Agent**: Demo mode with mock responses

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   gcloud auth application-default login
   gcloud auth list  # Verify active account
   ```

2. **Firestore Permissions**:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member='serviceAccount:YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com' \
     --role='roles/datastore.user'
   ```

3. **File Upload Issues**:
   - Check `MAX_FILE_SIZE` environment variable
   - Verify file extensions are supported
   - Ensure upload directory permissions

### Debug Mode

Enable detailed logging by setting log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Usage Examples

### For C-Level Executives

**Simple Questions**:
- "Show me our top 10 customers by revenue this quarter"
- "What's our monthly growth trend?"
- "Which regions are performing best?"

### For Data Scientists

**Advanced Queries**:
- "Create a correlation analysis between customer age and purchase frequency"
- "Build a machine learning model to predict customer churn"
- "Generate a cohort analysis for user retention"

### File Analysis

1. **Upload** your CSV/Excel file
2. **Wait** for automatic analysis
3. **Ask** questions about the data
4. **Export** results and insights

## 🔄 Updates and Maintenance

### Updating Dependencies

```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt  # Update lockfile
```

### Database Cleanup

```bash
# Clean old exports (7 days)
python -c "from app.utils import ExportManager; ExportManager().cleanup_old_exports()"
```

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:

1. **Application Issues**: Check logs and configuration
2. **Agent Issues**: Verify Vertex AI Reasoning Engine deployment
3. **Authentication Issues**: Check IAP and domain configuration
4. **Infrastructure Issues**: Refer to terraform module documentation

## 🚀 Next Steps

1. **Deploy Infrastructure**: Use the `gcp-data-analyst-agent` Terraform module
2. **Deploy Agent**: Manual Vertex AI Reasoning Engine deployment
3. **Deploy Interface**: This Gradio application
4. **Configure Access**: Set up IAP and user permissions
5. **Train Users**: Provide examples and documentation 