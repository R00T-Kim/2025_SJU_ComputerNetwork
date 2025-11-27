import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'http://localhost:8080';

function App() {
    const [step, setStep] = useState('login');
    const [nick, setNick] = useState('');
    const [channel, setChannel] = useState('#general');
    const [channels, setChannels] = useState(['#general']);
    const [onlineUsers, setOnlineUsers] = useState([]);

    const [inputMsg, setInputMsg] = useState('');
    const [messages, setMessages] = useState([]);
    const [lastId, setLastId] = useState(0);
    const [selectedFile, setSelectedFile] = useState(null);

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => { scrollToBottom(); }, [messages]);

    // 초기 데이터 로드
    useEffect(() => {
        if(step === 'chat') {
            fetchChannels();
            fetchUsers();
            const userInterval = setInterval(fetchUsers, 5000);
            return () => clearInterval(userInterval);
        }
    }, [step]);

    const fetchChannels = async () => {
        try {
            const res = await axios.get(`${API_URL}/channels`);
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
            return true;
        } catch (err) {
            console.error("입장 실패:", err);
            alert(`채널 입장 실패: ${targetChannel}\n서버가 켜져있나요?`);
            return false;
        }
    };

    // 채널 생성 (핵심 수정: 생성 후 바로 입장)
    const createChannel = async () => {
        const newCh = prompt("새 채널 이름 (예: #coding)");
        if(newCh) {
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
        let isMounted = true;

        const poll = async () => {
            try {
                const res = await axios.get(`${API_URL}/events`, {
                    params: { channel, since: lastId }
                });
                if(!isMounted) return;

                const { events, latest } = res.data;
                if (events && events.length > 0) {
                    setMessages(prev => {
                        const newEvents = events.filter(e => !prev.some(p => p.id === e.id));
                        return [...prev, ...newEvents];
                    });
                    setLastId(latest);
                } else {
                    if(latest > lastId) setLastId(latest);
                }
            } catch (err) {
                // 폴링 에러는 조용히 넘어가거나 콘솔에만 출력
                // console.error(err);
            }
        };

        const interval = setInterval(poll, 1000);
        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, [step, channel, lastId]);

    const handleFileChange = (e) => {
        if(e.target.files.length > 0) setSelectedFile(e.target.files[0]);
    };

    // 메시지 전송
    const sendMessage = async (e) => {
        e.preventDefault();

        // 아무것도 없으면 리턴
        if (!inputMsg.trim() && !selectedFile) return;

        let imgUrl = null;
        if (selectedFile) {
            const formData = new FormData();
            formData.append('file', selectedFile);
            try {
                const res = await axios.post(`${API_URL}/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                imgUrl = res.data.url;
            } catch (err) {
                alert("파일 업로드 실패! 서버 로그를 확인하세요.");
                console.error(err);
                return;
            }
        }

        try {
            await axios.post(`${API_URL}/message`, {
                nick,
                channel,
                text: imgUrl || inputMsg,
                msg_type: imgUrl ? 'image' : 'text'
            });
            setInputMsg('');
            setSelectedFile(null);
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

    return (
        <div className="app-container">
            <div className="sidebar">
                <div className="section-title">CHANNELS <button onClick={createChannel}>+</button></div>
                {channels.map(ch => (
                    <div key={ch} className={`item ${channel===ch?'active':''}`} onClick={()=>joinChannel(ch)}>
                        {ch.startsWith('!dm') ? '💬 DM' : ch}
                    </div>
                ))}

                <div className="section-title" style={{marginTop:'20px'}}>USERS</div>
                {onlineUsers.map(u => (
                    <div key={u} className="item user-item" onClick={()=>startDM(u)}>
                        🟢 {u} {u===nick && '(me)'}
                    </div>
                ))}
            </div>

            <div className="chat-area">
                <div className="chat-header">
                    {channel.startsWith('!dm') ? channel : channel}
                </div>
                <div className="message-list">
                    {messages.map((msg) => {
                        if (msg.type === 'join' || msg.type === 'part') {
                            return <div key={msg.id} className="system-msg">-- {msg.nick}님이 {msg.type === 'join' ? '입장' : '퇴장'}했습니다 --</div>
                        }
                        const isMe = msg.nick === nick;
                        return (
                            <div key={msg.id} className={`msg-row ${isMe ? 'mine' : ''}`}>
                                {!isMe && <div className="sender">{msg.nick}</div>}
                                <div className="bubble">
                                    {msg.msg_type === 'image' ? (
                                        <img src={msg.text} alt="uploaded" className="chat-img" />
                                    ) : (
                                        msg.text
                                    )}
                                </div>
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>

                <form className="input-area" onSubmit={sendMessage}>
                    <input type="file" id="file" style={{display:'none'}} onChange={handleFileChange} />
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