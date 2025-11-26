// src/App.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

// 백엔드 주소 (Python raw socket server)
const API_URL = 'http://localhost:8080';

function App() {
    const [step, setStep] = useState('login'); // login | chat
    const [nick, setNick] = useState('');
    const [channel, setChannel] = useState('#general'); // 기본 채널
    const [inputMsg, setInputMsg] = useState('');
    const [messages, setMessages] = useState([]);
    const [lastId, setLastId] = useState(0);
    const [channels, setChannels] = useState(['#general', '#random', '#dev']); // 데모용 채널 목록

    const messagesEndRef = useRef(null);

    // 자동 스크롤
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // 로그인 (채널 입장)
    const handleLogin = async () => {
        if (!nick.trim()) return alert("닉네임을 입력하세요.");
        try {
            // 1. 채널 입장 요청
            await axios.post(`${API_URL}/join`, { nick, channel });
            setStep('chat');
            // 2. 초기 데이터 로딩 및 폴링 시작
        } catch (err) {
            alert("서버 연결 실패! 백엔드가 켜져있나요?");
            console.error(err);
        }
    };

    // 메시지 전송
    const sendMessage = async (e) => {
        e.preventDefault();
        if (!inputMsg.trim()) return;

        try {
            await axios.post(`${API_URL}/message`, {
                nick,
                channel,
                text: inputMsg
            });
            setInputMsg('');
        } catch (err) {
            console.error("전송 실패", err);
        }
    };

    // 주기적 폴링 (새 메시지 확인)
    useEffect(() => {
        if (step !== 'chat') return;

        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`${API_URL}/events`, {
                    params: { channel, since: lastId }
                });

                const { events, latest } = res.data;

                if (events && events.length > 0) {
                    // 중복 방지 및 상태 업데이트
                    setMessages(prev => {
                        // 이미 있는 ID는 제외 (혹시 모를 중복 방지)
                        const newEvents = events.filter(e => !prev.some(p => p.id === e.id));
                        return [...prev, ...newEvents];
                    });
                    setLastId(latest);
                } else {
                    // 이벤트가 없어도 최신 ID 동기화 (서버가 latest를 줄 경우)
                    if(latest > lastId) setLastId(latest);
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 1000); // 1초마다 갱신

        return () => clearInterval(interval);
    }, [step, channel, lastId]);

    // 채널 변경 핸들러 (현재는 단순 UI 전환)
    const changeChannel = async (newChannel) => {
        // 기존 채널 퇴장(선택사항) 후 새 채널 입장 로직 추가 가능
        setChannel(newChannel);
        setMessages([]); // 메시지 초기화
        setLastId(0);    // 처음부터 다시 받기
        await axios.post(`${API_URL}/join`, { nick, channel: newChannel });
    };

    // --- 렌더링 ---
    if (step === 'login') {
        return (
            <div className="login-container">
                <div className="login-box">
                    <h2>🚀 Team Project Chat</h2>
                    <input
                        type="text"
                        placeholder="닉네임을 입력하세요"
                        value={nick}
                        onChange={(e) => setNick(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                    />
                    <button onClick={handleLogin}>입장하기</button>
                </div>
            </div>
        );
    }

    return (
        <div className="app-container">
            {/* 사이드바 (채널 목록) */}
            <div className="sidebar">
                <div className="sidebar-header">Chat Channels</div>
                <div className="channel-list">
                    {channels.map(ch => (
                        <div
                            key={ch}
                            className={`channel-item ${channel === ch ? 'active' : ''}`}
                            onClick={() => changeChannel(ch)}
                        >
                            # {ch}
                        </div>
                    ))}
                </div>
                <div className="user-info">
                    <div className="avatar"></div>
                    <div>{nick}</div>
                </div>
            </div>

            {/* 채팅 영역 */}
            <div className="chat-area">
                <div className="chat-header">
                    # {channel}
                </div>

                <div className="message-list">
                    {messages.map((msg) => {
                        if (msg.type === 'join' || msg.type === 'part') {
                            return (
                                <div key={msg.id} className="system-message">
                                    -- {msg.nick}님이 {msg.type === 'join' ? '입장했습니다' : '나갔습니다'} --
                                </div>
                            )
                        }
                        const isMe = msg.nick === nick;
                        return (
                            <div key={msg.id} className={`message ${isMe ? 'mine' : 'others'}`}>
                                {!isMe && <span className="message-sender">{msg.nick}</span>}
                                <div className="bubble">
                                    {msg.text}
                                </div>
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>

                <div className="input-area">
                    <form className="input-wrapper" onSubmit={sendMessage}>
                        <input
                            type="text"
                            placeholder={`Message #${channel}`}
                            value={inputMsg}
                            onChange={(e) => setInputMsg(e.target.value)}
                        />
                    </form>
                </div>
            </div>
        </div>
    );
}

export default App;