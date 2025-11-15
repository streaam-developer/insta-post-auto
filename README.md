# Instagram Reel Automation System

A comprehensive automation system for scheduling and posting Instagram reels with a web-based dashboard for monitoring and control.

## Features

- **Automatic Scheduling**: Posts reels every 5 hours seamlessly using Instagram API.
- **Web Dashboard**: User-friendly interface with real-time monitoring, analytics, queue management, logs, and alerts.
- **Analytics**: Detailed metrics for views, likes, shares, and engagement rates.
- **Queue Management**: Edit, reschedule, or cancel upcoming posts.
- **Authentication**: Secure user login with role-based access (admin/editor).
- **Logging**: Comprehensive logs of all activities.
- **Alerts**: Customizable notifications for successes, failures, or anomalies.
- **AI Integration**: AI-powered caption suggestions using OpenAI.
- **Robustness**: Handles API rate limits, network failures, and platform changes with retries and error handling.
- **Scalability**: Asynchronous processing and MongoDB for data storage.

## Setup Instructions

### Prerequisites

- Python 3.8+
- MongoDB Atlas account or local MongoDB
- Instagram accounts for automation
- OpenAI API key (optional, for AI suggestions)

### Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd insta-post-auto
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```
   # Instagram Accounts
   INSTA_USERNAME_1=your_username1
   INSTA_PASSWORD_1=your_password1
   INSTA_SOURCE_ACCOUNTS_1=source_account1,source_account2

   # MongoDB
   MONGO_CONNECTION_STRING=mongodb+srv://...
   MONGO_DATABASE_NAME=instagram_automation

   # Other settings
   MAX_POSTS_PER_ACCOUNT=10
   DAYS_CUTOFF=7
   SECRET_KEY=your_secret_key
   OPENAI_API_KEY=your_openai_key
   ```

4. Create initial user:
   Run Python shell:
   ```python
   from database import Database
   import os
   db = Database(os.getenv('MONGO_CONNECTION_STRING'), os.getenv('MONGO_DATABASE_NAME'))
   db.create_user('admin', 'password', 'admin')
   ```

5. Run the application:
   - For automation: `python main.py`
   - For dashboard: `python app.py`

   Access dashboard at http://localhost:5000

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Logout

### Dashboard
- `GET /` - Main dashboard (requires login)

### API
- `GET /api/accounts` - List Instagram accounts
- `GET /api/reels/<username>` - Get posted and available reels
- `GET /api/analytics/<username>` - Get analytics for account
- `GET /api/logs/<username>` - Get activity logs
- `GET /api/queue/<username>` - Get posting queue
- `POST /api/queue/<username>` - Add to queue
- `PUT /api/queue/<username>/<shortcode>` - Update queue item
- `DELETE /api/queue/<username>/<shortcode>` - Cancel queue item
- `GET /api/alerts` - Get user alerts
- `POST /api/alerts` - Create alert
- `POST /api/ai-suggest` - Get AI caption suggestion

## Troubleshooting

### Common Issues

1. **Instagram Login Failed**:
   - Ensure credentials are correct.
   - Check for 2FA; may need manual login first.
   - Verify session files are saved.

2. **MongoDB Connection Error**:
   - Check connection string and network access.
   - Ensure database name is correct.

3. **API Rate Limits**:
   - System has built-in retries and delays.
   - Monitor logs for rate limit errors.

4. **No Reels Found**:
   - Check source accounts are public and have reels.
   - Adjust MAX_POSTS_PER_ACCOUNT and DAYS_CUTOFF.

5. **Dashboard Not Loading**:
   - Ensure Flask is running on port 5000.
   - Check SECRET_KEY is set.

### Logs

All activities are logged to MongoDB. View in dashboard or query database.

### Support

For issues, check logs and ensure all dependencies are installed.

## Architecture

- **main.py**: Core automation script with scheduling.
- **app.py**: Flask web application for dashboard.
- **database.py**: MongoDB interface.
- **instagram.py**: Instagram API interactions.
- **templates/**: HTML templates for UI.

The system uses async processing for concurrent account handling and robust error recovery.