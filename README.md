# Storage Assistant

An AI-powered desktop application that helps you manage and clean up your storage space using natural language commands.

## Features

- Scan directories for file metadata (size, last modified, etc.)
- Find duplicate files using SHA-256 hashing
- Analyze space usage by directory
- Natural language interface powered by OpenAI GPT
- Modern GUI using CustomTkinter
- Safe file deletion with Recycle Bin support

## Requirements

- Python 3.8 or higher
- OpenAI API key

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/storage_assistant.git
cd storage_assistant
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

4. Create a `.venv` on a version (Not Supported with 3.13 Yet):
```
# In your project folder
py -3.10 -m venv .venv
# or
python3.10 -m venv .venv
```

## Usage
**Note**
The app currently works only on Windows with elevated (admin) privileges

1. Build the application with PyInstaller, then run the application (`/dist/StorageAssistant.exe`) OR Run `main.py`:
```bash
pyinstaller main.spec
```

2. Enter the directory you want to scan (defaults to Downloads folder)

3. Type your query in natural language, for example:
- "Show me files larger than 1GB"
- "Find duplicate files"
- "Delete files older than 6 months"
- "What's taking up the most space?"

## Example Queries

- "List all files larger than 500MB in my Downloads folder"
- "Find duplicate videos in my Videos folder"
- "Delete temporary files older than 30 days"
- "Show me the largest directories"
- "Find all .log files"

## Safety Features

- Files are moved to the Recycle Bin instead of permanent deletion
- Confirmation required before deletion
- Progress bar shows scanning status
- Error handling for permission issues

## Contributing

Feel free to submit issues and enhancement requests! 

Please create PR's and use a new branch to preserve system integrity

## 🛠️ Build Instructions

### 1. 🔧 Compile with Nuitka

To build the application using Nuitka with `tkinter` support, run:

```bash
 nuitka main.py --onefile --standalone --enable-plugin=tk-inter --windows-disable-console --output-dir=build --include-data-file=.env=.env --windows-uac-admin          
```
**Note** 
Ensure .env exists before running the command
