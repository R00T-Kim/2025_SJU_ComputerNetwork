# Simple HTTP Chat Project

## Project Overview

This project implements a simple chat application, developed as part of the 2025 SJU Computer Network course. It emphasizes fundamental networking concepts by building a custom HTTP server using raw TCP sockets in Python for the backend, and a modern web interface with React.js for the frontend. The application aims to demonstrate adherence to standard RFC protocols (specifically HTTP/1.1) without relying on higher-level networking frameworks, fulfilling the course requirements.

## Features

-   **Custom HTTP Server:** Implemented in Python using raw socket APIs, capable of handling HTTP requests and responses.
-   **Real-time Chat:** Supports real-time messaging between connected clients.
-   **React.js Frontend:** A dynamic and responsive web interface for chat interactions.
-   **File Upload/Download:** Capability to upload files to the server and download them via HTTP.

## Project Structure

-   `src/`: Contains the Python backend code.
    -   `server.py`: The main HTTP server implementation.
    -   `channel_manager.py`: Manages chat channels and message distribution.
    -   `http_utils.py`: Utility functions for parsing HTTP requests and formatting responses.
    -   `client.py`: (Potentially a test client or command-line client, not directly part of the web app).
-   `my-chat-app/`: Contains the React.js frontend application.
    -   `public/`: Static assets for the React app.
    -   `src/`: React source code (components, styles, etc.).
-   `docs(report)/`: Project documentation, reports, and supplementary materials.
-   `uploads/`: Directory where files uploaded through the chat application are stored.

## Prerequisites

Before running the project, ensure you have the following installed:

-   **Python 3.x:** (Tested with Python 3.11/3.13)
-   **Node.js & npm:** (Recommended latest LTS version)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/R00T-Kim/2025_SJU_ComputerNetwork.git
    cd 2025_SJU_ComputerNetwork
    ```

2.  **Install Frontend Dependencies:**
    Navigate to the frontend directory and install Node.js packages:
    ```bash
    cd my-chat-app
    npm install
    cd ..
    ```
    *(Note: The Python backend uses only standard library modules, so no `pip install` is strictly required for `requirements.txt` if it only contains comments.)*

## Running the Application

The project includes convenient scripts to start both the backend server and the frontend application simultaneously.

-   **On Windows:**
    ```bash
    start.bat
    ```
-   **On Linux/macOS:**
    ```bash
    ./start.sh
    ```

Once started, the chat application should be accessible in your web browser, typically at `http://localhost:3000` for the frontend, which will communicate with the backend running on `http://localhost:8080`.

## Usage Guide

### 1. Getting Started
-   **Login:** When the application loads, enter a nickname to identify yourself and click **"입장하기"** (Enter) to join the chat.
-   **Default Channel:** You will automatically join the `# 일반` (General) channel upon login.

### 2. Channel Management
-   **View Channels:** The sidebar lists all available chat channels under the **"CHANNELS"** section.
-   **Switch Channels:** Click on any channel name in the list to switch to that room.
-   **Create Channel:** Click the **`+`** button next to "CHANNELS". Enter a new channel name in the prompt. If you don't include a `#`, one will be added automatically (e.g., entering "study" creates `# study`).

### 3. Chat Features
-   **Send Message:** Type your message in the input box at the bottom and press **Enter** or click **"전송"** (Send).
-   **Direct Messages (DM):**
    -   The **"USERS"** section in the sidebar shows connected users.
    -   Click on a user's name to start a private Direct Message channel with them.
    -   Green/Red dots indicate the user's online/offline status.

### 4. File Sharing
-   **Upload File:** Click the **`📎`** (paperclip) icon to select a file from your computer.
-   **Send File:** Once a file is selected, the icon changes to `✅`. Click **"전송"** to upload and send it to the current channel.
-   **View/Download:**
    -   **Images:** Displayed directly in the chat bubble.
    -   **Other Files:** Appears as a link with a file name; click to download.
    -   *Note: Files are uploaded to the server's `uploads/` directory.*

## Team Information

| 학번       | 이름   | 역할           |
| :--------- | :----- | :------------- |
| 21011673   | 한상민 | 프론트엔드     |
| 21011659 | 김근호 | 역할 |
| 21011582 | 한현준 | 역할 |
| 21011650 | 이규민 | 역할 |

---
## Simple Structure Schema (Client-Server Network Diagram)

The application follows a classic client-server architecture:

```
+----------------+          HTTP Request/Response          +---------------------+
|                | <-------------------------------------> |                     |
|  Web Browser   | (e.g., GET /messages, POST /send, etc.) |  Python HTTP Server |
|  (React App)   |                                         |  (src/server.py)    |
|                |                                         |                     |
+----------------+                                         +---------------------+
       ^                                                            ^
       |                                                            |
       |                                                            |
       | (Uses WebSocket-like polling or long-polling             | (Manages chat channels and connected clients)
       | for real-time updates - details in src/channel_manager.py) |
       |                                                            |
       v                                                            v
+----------------+                                         +---------------------+
|                |                                         |                     |
|  User's Device |                                         |   Backend Storage   |
|                |                                         |  (e.g., in-memory,   |
+----------------+                                         |    file system for  |
                                                           |    uploads)         |
                                                           +---------------------+
```

-   **Client (React App):** Runs in the user's web browser, providing the user interface for sending and receiving messages. It makes HTTP requests to the Python server for various operations (e.g., fetching message history, sending new messages, uploading files).
-   **Server (Python HTTP Server):** Listens for incoming TCP connections on port 8080. It parses raw HTTP requests, processes them (e.g., adds messages to channels, stores uploaded files), and sends back HTTP responses. It utilizes `channel_manager.py` to handle chat room logic and message broadcasting.
-   **Communication Protocol:** All communication between the client and server is based on the HTTP/1.1 protocol, implemented directly over TCP sockets.