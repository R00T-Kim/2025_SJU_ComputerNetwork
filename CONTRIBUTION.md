# Project Contribution Log

This document details the individual contributions of each team member to the "2025_SJU_ComputerNetwork - Simple HTTP Chat Project". This log serves as evidence of contribution for the individual scoring component of Homework 3 (15 pts).

---

## Team Member Contributions

### 1. 김근호 (학번: 21011659)

**Role:** 프로토콜/소켓 서버 코어 개발 (Backend Core Developer)

**Contributions:**
-   **Design & Planning:**
    -   Defined the core architecture for the TCP socket server and the event loop strategy.
    -   Designed the HTTP request/response flow to ensure RFC compliance.
-   **Backend Implementation (Python):**
    -   Implemented the raw **TCP socket server** initialization and connection acceptance loop in `server.py`.
    -   Developed the **HTTP request parser** (`http_utils.py`) to handle methods (GET, POST, OPTIONS) and headers.
    -   Implemented the routing logic to dispatch requests to appropriate handlers.
    -   Created the response formatting logic to generate standard HTTP 200 OK, 404 Not Found, etc.
-   **Testing & Debugging:**
    -   Debugged low-level socket issues and encoding/decoding errors.
-   **Documentation:**
    -   Documented the internal API endpoints and data formats for the frontend team.

---

### 2. 한현준 (학번: 21011582)

**Role:** 채널 및 데이터 관리 개발 (Data & Channel Manager)

**Contributions:**
-   **Design & Planning:**
    -   Designed the data structures for storing chat channels, user sessions, and message history.
-   **Backend Implementation (Python):**
    -   Developed `channel_manager.py` to manage state for chat rooms and connected users.
    -   Implemented the **message broadcasting logic** to ensure all clients receive updates.
    -   Implemented the **file upload/download handling functions**, ensuring files are correctly saved to the `uploads/` directory and served back to clients.
-   **Testing & Debugging:**
    -   Verified the persistence of messages in memory and the integrity of uploaded files.

---

### 3. 한상민 (학번: 21011673)

**Role:** 프론트엔드 및 API 통합 개발 (Frontend & Integration Developer)

**Contributions:**
-   **Design & Planning:**
    -   Designed the user interface (UI) layout and user experience (UX) flow for the chat application.
-   **Frontend Implementation (React.js):**
    -   Built the core React components: Sidebar (Channel/User list), Chat Area, and Message Bubbles.
    -   Implemented the **API integration layer** using `axios` to communicate with the Python backend.
    -   Developed the **Long-polling mechanism** to receive real-time message updates.
    -   Implemented client-side logic for **Direct Messages (DM)**, nickname management, and file selection/upload UI.
-   **Testing & Debugging:**
    -   Conducted cross-browser testing and fixed UI rendering issues.

---

### 4. 이규민 (학번: 21011650)

**Role:** 품질 보증 및 문서화 (QA & Documentation Specialist)

**Contributions:**
-   **Design & Planning:**
    -   Established the testing protocols and release criteria.
-   **Testing & Debugging:**
    -   Led the **System Integration Testing (SIT)**, verifying the interaction between the React frontend and Python backend.
    -   Identified bugs in the connection teardown process and reported them for fixing.
-   **Deployment & Configuration:**
    -   Wrote the cross-platform startup scripts: **`start.bat` (Windows)** and **`start.sh` (macOS/Linux)** to automate the build and run process.
-   **Documentation:**
    -   Authored and finalized the **`README.md`** (Usage Guide, Team Info) and **`CONTRIBUTION.md`**.
    -   Prepared the demonstration scenario and presentation materials.