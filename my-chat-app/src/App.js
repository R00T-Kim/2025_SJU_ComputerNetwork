import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || `${window.location.protocol}//${window.location.hostname}:8080`;

function App() {
    const [step, setStep] = useState('login');
    const [nick, setNick] = useState('');
    const [channel, setChannel] = useState('# 일반');
    const [channels, setChannels] = useState(['# 일반']);
    const [onlineUsers, setOnlineUsers] = useState([]); // [{nick, active}]

    const [inputMsg, setInputMsg] = useState('');
    const [messages, setMessages] = useState([]);
    const [lastId, setLastId] = useState(0);
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadQueue, setUploadQueue] = useState([]); // {id, name, progress, status, channel}

    const messagesEndRef = useRef(null);
    const lastIdRef = useRef(0);
    const fileInputRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => { scrollToBottom(); }, [messages]);

    const isImageFile = (file) => {
        if (!file) return false;
        const mime = file.type || '';
        const ext = (file.name.split('.').pop() || '').toLowerCase();
        const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'];
        return mime.startsWith('image/') || imageExts.includes(ext);
    };

    const getDMPartner = (ch) => {
        if (!ch.startsWith('!dm_')) return null;
        const names = ch.replace('!dm_', '').split('_');
        const partner = names.find(n => n !== nick) || names[0];
        return partner || ch;
    };

    // 포커스 상태를 서버에 알리기
    useEffect(() => {
        if (step !== 'chat') return;
        const sendPresence = (active) => {
            if (!nick) return;
            const payload = { nick, active };
            axios.post(`${API_URL}/presence`, payload, { timeout: 1000 }).catch(() => {});
        };
        const handleVisibility = () => {
            const active = document.visibilityState === 'visible';
            sendPresence(active);
        };
        const handleFocus = () => sendPresence(true);
        const handleBlur = () => sendPresence(false);

        document.addEventListener('visibilitychange', handleVisibility);
        window.addEventListener('focus', handleFocus);
        window.addEventListener('blur', handleBlur);

        // 초기 상태 전송
        handleVisibility();

        return () => {
            document.removeEventListener('visibilitychange', handleVisibility);
            window.removeEventListener('focus', handleFocus);
            window.removeEventListener('blur', handleBlur);
        };
    }, [step, nick]);

    // 초기 데이터 로드
    useEffect(() => {
        if(step === 'chat') {
            fetchChannels();
            fetchUsers();
            const interval = setInterval(() => {
                fetchUsers();
                fetchChannels();
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [step]);

    const fetchChannels = async () => {
        try {
            const res = await axios.get(`${API_URL}/channels`, { params: { nick } });
            if(res.data.channels) setChannels(res.data.channels);
        } catch(e) { console.error("채널 목록 로드 실패", e); }
    };

    const fetchUsers = async () => {
        try {
            const res = await axios.get(`${API_URL}/users`);
            if(res.data.users) setOnlineUsers(res.data.users);
        } catch(e) {}
    };

    // 로그인
    const handleLogin = async () => {
        if (!nick.trim()) return alert("닉네임을 입력해주세요!");
        // 바로 입장 시도
        const success = await joinChannel(channel);
        if(success) setStep('chat');
    };

    // 채널 입장 (핵심 수정: async/await 처리 및 에러 핸들링)
    const joinChannel = async (targetChannel) => {
        try {
            await axios.post(`${API_URL}/join`, { nick, channel: targetChannel });
            setChannel(targetChannel);
            setMessages([]);
            setLastId(0);
            lastIdRef.current = 0;
            return true;
        } catch (err) {
            console.error("입장 실패:", err);
            alert(`채널 입장 실패: ${targetChannel}\n서버가 켜져있나요?`);
            return false;
        }
    };

    // 채널 생성 (핵심 수정: 생성 후 바로 입장)
    const createChannel = async () => {
        const raw = prompt("새 채널 이름 (예: 공부방)");
        const trimmed = raw ? raw.trim() : "";
        if(trimmed) {
            const newCh = trimmed.startsWith("#") ? trimmed : `# ${trimmed}`;
            // 목록에 먼저 추가하고 입장을 시도
            const success = await joinChannel(newCh);
            if(success) {
                setChannels(prev => [...new Set([...prev, newCh])]);
            }
        }
    };

    // DM 시작
    const startDM = (targetUser) => {
        if(targetUser === nick) return;
        const sorted = [nick, targetUser].sort().join('_');
        joinChannel(`!dm_${sorted}`);
    };

    // 폴링 로직
    useEffect(() => {
        if (step !== 'chat') return;
        let canceled = false;
        let inFlight = false;
        let timerId = null;

        const updateLastId = (val) => {
            lastIdRef.current = val;
            setLastId(val);
        };

        const poll = async () => {
            if (canceled || inFlight) return;
            inFlight = true;
            try {
                const res = await axios.get(`${API_URL}/events`, {
                    params: { channel, since: lastIdRef.current, nick }
                });
                if(canceled) return;

                const { events, latest } = res.data;
                if (events && events.length > 0) {
                    setMessages(prev => {
                        const newEvents = events.filter(e => !prev.some(p => p.id === e.id));
                        return [...prev, ...newEvents];
                    });
                    updateLastId(latest);
                } else if(latest > lastIdRef.current) {
                    updateLastId(latest);
                }
            } catch (err) {
                // 폴링 에러는 조용히 넘어가거나 콘솔에만 출력
            } finally {
                inFlight = false;
                if (!canceled) {
                    timerId = setTimeout(poll, 1000);
                }
            }
        };

        poll();
        return () => {
            canceled = true;
            if (timerId) clearTimeout(timerId);
        };
    }, [step, channel]);

    const handleFileChange = (e) => {
        if(e.target.files.length > 0) setSelectedFile(e.target.files[0]);
    };

    const clearFileSelection = () => {
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    // 페이지 종료 시 서버에 leave 알림 (sendBeacon + keepalive fetch fallback)
    useEffect(() => {
        if (step !== 'chat') return;
        const sendLeave = () => {
            if (!nick) return;
            const payload = JSON.stringify({ nick });
            const blob = new Blob([payload], { type: 'application/json' });
            if (navigator.sendBeacon) {
                navigator.sendBeacon(`${API_URL}/leave`, blob);
            } else {
                fetch(`${API_URL}/leave`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: payload,
                    keepalive: true,
                }).catch(() => {});
            }
        };
        const handler = () => sendLeave();
        window.addEventListener('beforeunload', handler);
        window.addEventListener('pagehide', handler);
        return () => {
            window.removeEventListener('beforeunload', handler);
            window.removeEventListener('pagehide', handler);
        };
    }, [step, nick]);

    // 메시지 전송
    const sendMessage = async (e) => {
        e.preventDefault();
        const currentChannel = channel;
        const fileToSend = selectedFile;
        const textInput = inputMsg;

        // 아무것도 없으면 리턴
        if (!textInput.trim() && !fileToSend) return;

        let uploadMeta = null;
        let msgType = 'text';
        let textToSend = textInput;

        // 전송을 시작하면 선택된 파일을 바로 해제해 다음 전송에 끌려가지 않게 함
        if (fileToSend) clearFileSelection();

        if (fileToSend) {
            const uploadId = `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
            const fileName = fileToSend.name;
            setUploadQueue(prev => [...prev, { id: uploadId, name: fileName, progress: 0, status: 'uploading', channel: currentChannel }]);

            const formData = new FormData();
            formData.append('file', fileToSend);
            try {
                const res = await axios.post(`${API_URL}/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (evt) => {
                        if (!evt.total) return;
                        const pct = Math.round((evt.loaded * 100) / evt.total);
                        setUploadQueue(prev => prev.map(item => item.id === uploadId ? { ...item, progress: pct } : item));
                    }
                });
                uploadMeta = {
                    url: res.data.url,
                    filename: res.data.filename || fileToSend.name
                };
                textToSend = uploadMeta.url;
                msgType = isImageFile(fileToSend) ? 'image' : 'file';
                setUploadQueue(prev => prev.map(item => item.id === uploadId ? { ...item, progress: 100, status: 'done' } : item));
                setTimeout(() => {
                    setUploadQueue(prev => prev.filter(item => item.id !== uploadId));
                }, 1500);
            } catch (err) {
                setUploadQueue(prev => prev.map(item => item.id === uploadId ? { ...item, status: 'error' } : item));
                setTimeout(() => {
                    setUploadQueue(prev => prev.filter(item => item.id !== uploadId));
                }, 3000);
                alert("파일 업로드 실패! 서버 로그를 확인하세요.");
                console.error(err);
                return;
            }
        }

        try {
            const payload = {
                nick,
                channel,
                text: textToSend,
                msg_type: msgType
            };
            if (uploadMeta?.filename) {
                payload.file_name = uploadMeta.filename;
            }

            await axios.post(`${API_URL}/message`, payload);
            setInputMsg('');
            clearFileSelection();
        } catch (err) {
            console.error("메시지 전송 실패", err);
            alert("메시지 전송 실패!");
        }
    };

    if (step === 'login') {
        return (
            <div className="login-container">
                <div className="login-box">
                    <h2>🚀 Team Chat</h2>
                    <input type="text" placeholder="사용할 닉네임" value={nick}
                           onChange={e=>setNick(e.target.value)}
                           onKeyPress={e=>e.key==='Enter' && handleLogin()} />
                    <button onClick={handleLogin}>입장하기</button>
                </div>
            </div>
        );
    }

    const currentUploads = uploadQueue.filter(u => u.channel === channel);

    return (
        <div className="app-container">
            <div className="sidebar">
                <div className="section-title">CHANNELS <button onClick={createChannel}>+</button></div>
                {channels.map(ch => (
                    <div
                        key={ch}
                        className={`item ${channel===ch?'active':''}`}
                        onClick={()=>joinChannel(ch)}
                    >
                        {ch.startsWith('!dm')
                            ? `# ${getDMPartner(ch)}`
                            : ch}
                    </div>
                ))}

                <div className="section-title" style={{marginTop:'20px'}}>USERS</div>
                {onlineUsers.map(u => (
                    <div key={u.nick} className="item user-item" onClick={()=>startDM(u.nick)}>
                        <span className="status-dot" style={{color: u.active ? '#2ecc71' : '#e74c3c'}}>●</span>
                        &nbsp;{u.nick} {u.nick===nick && '(me)'}
                    </div>
                ))}
            </div>

            <div className="chat-area">
                <div className="chat-header">
                    {channel.startsWith('!dm') ? (getDMPartner(channel)) : channel}
                </div>
                {currentUploads.length > 0 && (
                    <div className="upload-queue">
                        {currentUploads.map(item => (
                            <div key={item.id} className={`upload-item ${item.status}`}>
                                <span className="upload-name">{item.name}</span>
                                <span className="upload-status">
                                    {item.status === 'error' ? '실패' : `${item.progress || 0}%`}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
                <div className="message-list">
                    {messages.map((msg) => {
                        if (msg.type === 'join' || msg.type === 'part') {
                            return null; // 시스템 메시지는 표시하지 않음
                        }
                        const isMe = msg.nick === nick;
                        const fileName = msg.file_name || (msg.text ? msg.text.split('/').pop() : '');
                        return (
                            <div key={msg.id} className={`msg-row ${isMe ? 'mine' : ''}`}>
                                {!isMe && <div className="sender">{msg.nick}</div>}
                                {msg.msg_type === 'image' ? (
                                    <div className="bubble">
                                        <a href={msg.text} target="_blank" rel="noreferrer">
                                            <img src={msg.text} alt={fileName || "uploaded"} className="chat-img" />
                                        </a>
                                        {fileName && <div className="file-name">{fileName}</div>}
                                    </div>
                                ) : msg.msg_type === 'file' ? (
                                    <div className="bubble">
                                        <a href={msg.text} target="_blank" rel="noreferrer" download={fileName}>
                                            📎 {fileName || '첨부 파일'}
                                        </a>
                                    </div>
                                ) : (
                                    <div className="bubble">{msg.text}</div>
                                )}
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>

                <form className="input-area" onSubmit={sendMessage}>
                    <input type="file" id="file" style={{display:'none'}} onChange={handleFileChange} ref={fileInputRef} />
                    <label htmlFor="file" className="file-btn" style={{color: selectedFile ? '#4a90e2' : '#777'}}>
                        {selectedFile ? '✅' : '📎'}
                    </label>
                    <input
                        type="text"
                        placeholder={selectedFile ? `${selectedFile.name} 전송 대기중...` : "메시지 입력..."}
                        value={inputMsg}
                        onChange={e=>setInputMsg(e.target.value)}
                    />
                    <button type="submit">전송</button>
                </form>
            </div>
        </div>
    );
}

export default App;
