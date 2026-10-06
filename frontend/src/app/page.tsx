"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "@/components/ThemeProvider";

type ConversationMember = {
  user_id: number;
  role: string;
  display_name: string;
  avatar_url: string | null;
};

type Conversation = {
  id: number;
  type: string;
  name: string | null;
  avatar_url: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  members: ConversationMember[];
};

type Message = {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  created_at: string;
};

type UserProfile = {
  id: number;
  display_name: string;
  phone: string;
  about: string;
  avatar_url: string | null;
};

type Contact = {
  id: number;
  contact_user_id: number;
  display_name: string;
  phone: string;
  avatar_url: string | null;
};

function formatTime(dateString: string) {
  const d = new Date(dateString);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }
  if (now.getTime() - d.getTime() < 7 * 24 * 60 * 60 * 1000) {
    return d.toLocaleDateString([], { weekday: 'long' });
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function getInitials(name: string | null) {
  if (!name) return "?";
  const words = name.trim().split(" ");
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

type FilterType = "All" | "Unread" | "Groups" | "Contacts";

export default function Home() {
  const router = useRouter();
  const { isDarkMode, toggleTheme } = useTheme();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("All");
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showAddContact, setShowAddContact] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  const [newContactPhone, setNewContactPhone] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvRef = useRef<Conversation | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);

  // Online Presence & Typing
  const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());
  const [typingUsers, setTypingUsers] = useState<Map<number, string>>(new Map());
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Group Creation State
  const [showNewGroup, setShowNewGroup] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selectedContactIds, setSelectedContactIds] = useState<Set<number>>(new Set());

  // Group Details Sidebar State
  const [showGroupDetails, setShowGroupDetails] = useState(false);

  // Settings State
  const [editName, setEditName] = useState("");
  const [editAbout, setEditAbout] = useState("");
  const [editAvatar, setEditAvatar] = useState("");

  useEffect(() => {
    activeConvRef.current = activeConv;
  }, [activeConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    let mounted = true;
    let websocket: WebSocket | null = null;

    const init = async () => {
      try {
        const profileRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/profile`, {credentials: "include"});
        if (profileRes.ok) {
           const pData = await profileRes.json();
           setCurrentUser(pData);
           setEditName(pData.display_name || "");
           setEditAbout(pData.about || "");
           setEditAvatar(pData.avatar_url || "");
        } else if (profileRes.status === 401) {
           router.push("/login");
           return;
        }

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/`, {credentials: "include"});
        if (!mounted) return;
        if (res.ok) {
          const data = await res.json();
          setConversations(data);
        }

        // Fetch contacts for group creation
        const contactsRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/contacts/`, {credentials: "include"});
        if (contactsRes.ok) {
            const cData = await contactsRes.json();
            setContacts(cData);
        }
        
        websocket = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!);
        
        websocket.onmessage = (event) => {
          const wsData = JSON.parse(event.data);
          
          if (wsData.type === "presence") {
             setOnlineUsers(prev => {
                const next = new Set(prev);
                if (wsData.status === "online") next.add(wsData.user_id);
                else next.delete(wsData.user_id);
                return next;
             });
          }
          else if (wsData.type === "new_message") {
            const msg = wsData.message;
            setMessages((prev) => {
              if (activeConvRef.current && msg.conversation_id === activeConvRef.current.id) {
                // If it's the active conversation, mark as read immediately
                fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/${msg.conversation_id}/read`, {method: 'POST', credentials: 'include'});
                return [...prev, msg];
              }
              return prev;
            });
            fetchConversations();
          }
          else if (wsData.type === "typing") {
             if (activeConvRef.current && wsData.conversation_id === activeConvRef.current.id) {
                 const typing_user_id = wsData.user_id;
                 setTypingUsers(prev => {
                     const next = new Map(prev);
                     next.set(typing_user_id, "typing...");
                     return next;
                 });
                 setTimeout(() => {
                     setTypingUsers(prev => {
                         const next = new Map(prev);
                         next.delete(typing_user_id);
                         return next;
                     });
                 }, 3000);
             }
          }
        };
        
        websocket.onclose = (event) => {
          if (event.code === 1008 && mounted) {
            router.push("/login");
          }
        };

        setWs(websocket);
      } catch (err) {
        console.error(err);
      }
    };

    init();
    
    return () => {
      mounted = false;
      if (websocket) websocket.close();
    };
  }, [router]);

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/`, {credentials: "include"});
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadMessages = async (conv: Conversation) => {
    setActiveConv(conv);
    setShowGroupDetails(false); // reset pane
    
    // Optimistically clear unread_count
    setConversations(prev => prev.map(c => c.id === conv.id ? { ...c, unread_count: 0 } : c));
    
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/${conv.id}/read`, {method: "POST", credentials: "include"});
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/${conv.id}/messages`, {credentials: "include"});
      const data = await res.json();
      setMessages(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !ws || !activeConv) return;
    
    ws.send(JSON.stringify({
      type: "message",
      conversation_id: activeConv.id,
      content: newMessage.trim()
    }));
    
    setNewMessage("");
  };

  const handleTyping = (e: React.ChangeEvent<HTMLInputElement>) => {
      setNewMessage(e.target.value);
      if (!ws || !activeConv) return;
      ws.send(JSON.stringify({
          type: "typing",
          conversation_id: activeConv.id
      }));
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/contacts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: newContactPhone }),
        credentials: "include"
      });
      if (res.ok) {
        const contact = await res.json();
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/direct`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contact_user_id: contact.contact_user_id }),
          credentials: "include"
        });
        setShowAddContact(false);
        setNewContactPhone("");
        fetchConversations();
      } else {
        alert("Contact not found or already added.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!groupName.trim() || selectedContactIds.size === 0) return;
      try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/conversations/group`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ name: groupName, member_ids: Array.from(selectedContactIds) }),
              credentials: "include"
          });
          if (res.ok) {
              setShowNewGroup(false);
              setGroupName("");
              setSelectedContactIds(new Set());
              fetchConversations();
          }
      } catch (err) {
          console.error(err);
      }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/profile`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ display_name: editName, about: editAbout, avatar_url: editAvatar }),
            credentials: "include"
        });
        if (res.ok) {
            setCurrentUser(prev => prev ? { ...prev, display_name: editName, about: editAbout, avatar_url: editAvatar } : null);
            setShowSettings(false);
        }
    } catch (err) {
        console.error(err);
    }
  };

  const handleLogout = async () => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/logout`, { method: "POST", credentials: "include" });
    router.push("/login");
  };

  const sortedConversations = [...conversations].sort((a, b) => {
    const tA = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
    const tB = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
    return tB - tA;
  });

  const filteredConversations = sortedConversations.filter(c => {
    const matchesSearch = c.name?.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;
    
    if (activeFilter === "Groups") return c.type === "group";
    if (activeFilter === "Contacts") return c.type === "direct";
    if (activeFilter === "Unread") return false;
    
    return true;
  });

  // Render Avatar
  const renderAvatar = (url: string | null, name: string | null, isGroup = false, sizeClass = "w-12 h-12", isOnline = false) => {
      return (
          <div className={`relative flex-shrink-0 rounded-full ${sizeClass} bg-gray-200 overflow-hidden flex items-center justify-center`}>
              {url ? (
                  <img src={url} alt={name || "Avatar"} className="w-full h-full object-cover" />
              ) : (
                  <span className={`font-semibold text-white ${isGroup ? 'bg-indigo-500' : 'bg-blue-500'} w-full h-full flex items-center justify-center`}>
                      {getInitials(name)}
                  </span>
              )}
              {isOnline && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-orange-500 rounded-full border-2 border-white shadow-sm"></div>
              )}
          </div>
      );
  };

  const isMobile = typeof window !== "undefined" && window.innerWidth < 640;

  return (
    <div className="flex h-screen bg-[var(--background)] overflow-hidden">
      
      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
           <div className="bg-[var(--surface)] p-6 rounded-2xl w-full max-w-md shadow-xl border border-[var(--border)] overflow-y-auto max-h-[90vh]">
              <div className="flex justify-between items-center mb-6">
                 <h2 className="text-xl font-bold">Settings</h2>
                 <button onClick={() => setShowSettings(false)} className="text-[var(--text-muted)] hover:text-red-500">✕</button>
              </div>
              
              <div className="flex items-center gap-4 mb-6">
                 {renderAvatar(editAvatar, currentUser?.display_name || "?", false, "w-16 h-16")}
                 <div>
                    <h3 className="font-semibold text-lg">{currentUser?.display_name}</h3>
                    <p className="text-sm text-[var(--text-muted)]">{currentUser?.phone}</p>
                 </div>
              </div>

              <form onSubmit={handleSaveProfile} className="space-y-4">
                 <div>
                    <label className="block text-sm font-medium mb-2">Choose Avatar</label>
                    <div className="flex gap-2">
                       {[1, 2, 3, 4, 5].map(i => (
                          <div 
                             key={i} 
                             onClick={() => setEditAvatar(`/avatars/avatar${i}.svg`)}
                             className={`cursor-pointer border-2 rounded-full p-1 ${editAvatar === `/avatars/avatar${i}.svg` ? 'border-[var(--primary)]' : 'border-transparent'}`}
                          >
                             <img src={`/avatars/avatar${i}.svg`} alt={`Avatar ${i}`} className="w-10 h-10 rounded-full" />
                          </div>
                       ))}
                    </div>
                 </div>
                 <div>
                    <label className="block text-sm font-medium mb-1">Display Name</label>
                    <input type="text" value={editName} onChange={e=>setEditName(e.target.value)} className="input-field py-2" />
                 </div>
                 <div>
                    <label className="block text-sm font-medium mb-1">About</label>
                    <input type="text" value={editAbout} onChange={e=>setEditAbout(e.target.value)} className="input-field py-2" />
                 </div>
                 
                 <hr className="border-[var(--border)] my-4" />
                 
                 <div className="space-y-2 text-sm">
                    <button type="button" className="w-full text-left p-2 hover:bg-[var(--surface-hover)] rounded">🔒 Privacy (Coming Soon)</button>
                    <button type="button" className="w-full text-left p-2 hover:bg-[var(--surface-hover)] rounded">🔔 Notifications (Coming Soon)</button>
                    <button type="button" className="w-full text-left p-2 hover:bg-[var(--surface-hover)] rounded">📞 Linked Devices (Coming Soon)</button>
                 </div>

                 <button type="submit" className="btn-primary w-full mt-4 py-2">Save Profile</button>
                 <button type="button" onClick={handleLogout} className="w-full text-red-500 py-2 hover:underline mt-2">Log Out</button>
              </form>
           </div>
        </div>
      )}

      {/* Sidebar */}
      <div className={`${isMobile && activeConv ? 'hidden' : 'flex'} w-full sm:w-[22rem] border-r border-[var(--border)] flex-col bg-[var(--surface)]`}>
        <div className="p-4 flex justify-between items-center">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setShowSettings(true)}>
             {renderAvatar(currentUser?.avatar_url || null, currentUser?.display_name || "ME", false, "w-8 h-8")}
             <h2 className="text-xl font-bold">Chats</h2>
          </div>
          <div className="flex gap-1 relative">
            <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-[var(--surface-hover)] transition-colors" title="Toggle Theme">
              {isDarkMode ? '🌞' : '🌙'}
            </button>
            <button onClick={() => setShowAddMenu(!showAddMenu)} className="p-2 rounded-full hover:bg-[var(--surface-hover)] transition-colors" title="New Chat">
              <svg className="w-5 h-5 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            </button>
            
            {showAddMenu && (
               <div className="absolute top-10 right-0 bg-[var(--surface)] border border-[var(--border)] shadow-xl rounded-lg py-2 w-48 z-20">
                  <button onClick={() => { setShowAddContact(true); setShowNewGroup(false); setShowAddMenu(false); }} className="w-full text-left px-4 py-2 hover:bg-[var(--surface-hover)] text-sm">Add Contact</button>
                  <button onClick={() => { setShowNewGroup(true); setShowAddContact(false); setShowAddMenu(false); }} className="w-full text-left px-4 py-2 hover:bg-[var(--surface-hover)] text-sm">New Group</button>
                  <hr className="my-1 border-[var(--border)]" />
                  <button onClick={handleLogout} className="w-full text-left px-4 py-2 hover:bg-[var(--surface-hover)] text-sm text-red-500">Logout</button>
               </div>
            )}
          </div>
        </div>
        
        {/* Search */}
        <div className="px-4 pb-2">
           <div className="relative">
             <input
               type="text"
               placeholder="🔍 Search"
               value={searchQuery}
               onChange={(e)=>setSearchQuery(e.target.value)}
               className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg py-1.5 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-shadow"
             />
           </div>
        </div>
        
        {/* Filters */}
        <div className="px-4 pb-3 flex gap-2 overflow-x-auto no-scrollbar">
          {(["All", "Unread", "Groups", "Contacts"] as FilterType[]).map((f) => (
            <button 
              key={f} 
              onClick={() => setActiveFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors whitespace-nowrap ${activeFilter === f ? 'bg-[var(--primary)] text-white' : 'bg-[var(--background)] border border-[var(--border)] text-[var(--text-muted)] hover:bg-[var(--surface-hover)]'}`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Add Contact Modal Panel */}
        {showAddContact && (
          <div className="p-4 border-b border-t border-[var(--border)] bg-[var(--background)]">
            <div className="flex justify-between mb-2">
              <span className="text-xs font-semibold text-[var(--text-muted)]">Add new contact</span>
              <button onClick={() => setShowAddContact(false)} className="text-xs text-red-500 hover:underline">Cancel</button>
            </div>
            <form onSubmit={handleAddContact} className="flex gap-2">
              <input 
                type="text" 
                value={newContactPhone}
                onChange={(e)=>setNewContactPhone(e.target.value)}
                placeholder="Phone (+1...)" 
                className="input-field py-1.5 text-sm"
              />
              <button type="submit" className="btn-primary py-1.5 px-3 text-sm">Add</button>
            </form>
          </div>
        )}

        {/* Create Group Modal Panel */}
        {showNewGroup && (
          <div className="p-4 border-b border-t border-[var(--border)] bg-[var(--background)] max-h-64 overflow-y-auto">
            <div className="flex justify-between mb-2">
              <span className="text-xs font-semibold text-[var(--text-muted)]">Create New Group</span>
              <button onClick={() => { setShowNewGroup(false); setSelectedContactIds(new Set()); }} className="text-xs text-red-500 hover:underline">Cancel</button>
            </div>
            <form onSubmit={handleCreateGroup} className="space-y-3">
              <input 
                type="text" 
                value={groupName}
                onChange={(e)=>setGroupName(e.target.value)}
                placeholder="Group Subject" 
                className="input-field py-1.5 text-sm"
                required
              />
              <div className="space-y-1">
                 <span className="text-xs text-[var(--text-muted)]">Select members:</span>
                 {contacts.map(c => (
                     <label key={c.id} className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={selectedContactIds.has(c.contact_user_id)} onChange={(e)=>{
                            const next = new Set(selectedContactIds);
                            if (e.target.checked) next.add(c.contact_user_id);
                            else next.delete(c.contact_user_id);
                            setSelectedContactIds(next);
                        }} />
                        {c.display_name}
                     </label>
                 ))}
              </div>
              <button type="submit" className="btn-primary py-1.5 px-3 text-sm w-full">Create Group</button>
            </form>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {filteredConversations.length === 0 ? (
            <div className="p-8 text-center text-sm text-[var(--text-muted)]">
              No conversations found.
            </div>
          ) : (
            filteredConversations.map((c) => {
              // Determine if online (for direct chats)
              let isOnline = false;
              if (c.type === "direct") {
                  const otherMember = c.members.find(m => m.user_id !== currentUser?.id);
                  if (otherMember && onlineUsers.has(otherMember.user_id)) {
                      isOnline = true;
                  }
              }
              
              return (
              <div 
                key={c.id} 
                onClick={() => loadMessages(c)}
                className={`p-3 flex items-center gap-3 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors border-b border-[var(--border)] ${activeConv?.id === c.id ? 'bg-[var(--surface-hover)]' : ''}`}
              >
                {renderAvatar(c.avatar_url, c.name, c.type === "group", "w-12 h-12", isOnline)}
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline mb-1">
                    <h3 className="font-semibold truncate text-[var(--foreground)] text-[15px]">{c.name || "Unknown"}</h3>
                    <span className="text-[11px] text-[var(--text-muted)] whitespace-nowrap ml-2">
                      {c.last_message_at ? formatTime(c.last_message_at) : ""}
                    </span>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <p className={`text-[13px] truncate ${c.unread_count > 0 ? 'text-[var(--foreground)] font-semibold' : 'text-[var(--text-muted)]'}`}>
                      {c.last_message || "No messages yet"}
                    </p>
                    {c.unread_count > 0 && (
                        <div className="bg-[var(--primary)] text-white text-[10px] font-bold px-2 py-0.5 rounded-full ml-2">
                            {c.unread_count}
                        </div>
                    )}
                  </div>
                </div>
              </div>
            )
            })
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      {activeConv ? (
      <div className={`${isMobile && !activeConv ? 'hidden' : 'flex'} flex-1 flex flex-col bg-[var(--surface)] relative`}>
            <div className="p-3 border-b border-[var(--border)] bg-[var(--background)] flex items-center justify-between shadow-sm z-10 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors" onClick={() => setShowGroupDetails(true)}>
              <div className="flex items-center gap-3">
                 {isMobile && (
                     <button onClick={(e) => { e.stopPropagation(); setActiveConv(null); }} className="p-2 mr-1">
                         <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/></svg>
                     </button>
                 )}
                 
                 {(() => {
                      let isOnline = false;
                      if (activeConv.type === "direct") {
                          const otherMember = activeConv.members.find(m => m.user_id !== currentUser?.id);
                          if (otherMember && onlineUsers.has(otherMember.user_id)) isOnline = true;
                      }
                      return renderAvatar(activeConv.avatar_url, activeConv.name, activeConv.type === "group", "w-10 h-10", isOnline);
                 })()}

                 <div>
                   <h2 className="text-[16px] font-bold leading-tight">{activeConv.name || "Unknown"}</h2>
                   <p className="text-[12px] text-[var(--text-muted)]">
                     {activeConv.type === 'group' ? `${activeConv.members.length} members • Tap for info` : (
                         onlineUsers.has(activeConv.members.find(m => m.user_id !== currentUser?.id)?.user_id || -1) ? <span className="text-orange-500 font-medium">Online</span> : "Last seen recently"
                     )}
                   </p>
                 </div>
              </div>
              <div className="flex gap-3 text-[var(--text-muted)]">
                 <button title="Voice Call" onClick={(e)=>{e.stopPropagation(); alert("Voice calls coming soon");}}><svg className="w-5 h-5 hover:text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg></button>
                 <button title="Video Call" onClick={(e)=>{e.stopPropagation(); alert("Video calls coming soon");}}><svg className="w-5 h-5 hover:text-[var(--primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg></button>
              </div>
            </div>
            
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto flex flex-col gap-3">
              {messages.map((m) => {
                const isMe = m.sender_id === currentUser?.id;
                const showSender = activeConv.type === 'group' && !isMe;
                const senderName = showSender ? activeConv.members.find(x => x.user_id === m.sender_id)?.display_name : "";
                
                return (
                  <div key={m.id} className={`max-w-[85%] sm:max-w-[70%] flex flex-col ${isMe ? 'self-end items-end' : 'self-start items-start'}`}>
                    {showSender && (
                      <span className="text-[11px] text-[var(--text-muted)] mb-1 ml-1 font-medium">{senderName || "Unknown"}</span>
                    )}
                    <div className={`rounded-2xl px-4 py-2 shadow-sm ${isMe ? 'bg-[var(--primary)] text-white rounded-br-sm' : 'bg-[var(--message-in)] text-[var(--foreground)] rounded-bl-sm border border-[var(--border)]'}`}>
                      <p className="text-[15px] leading-relaxed">{m.content}</p>
                    </div>
                    <div className="flex items-center gap-1 mt-1 px-1">
                      <span className="text-[11px] text-[var(--text-muted)]">
                        {formatTime(m.created_at)}
                      </span>
                      {isMe && (
                         <span className="text-blue-500 text-[12px] ml-1 leading-none font-bold">✓✓</span>
                      )}
                    </div>
                  </div>
                );
              })}
              {/* Typing indicators */}
              {Array.from(typingUsers.entries()).map(([typing_user_id, txt]) => {
                  const typingUser = activeConv.members.find(m => m.user_id === Number(typing_user_id));
                  if (typingUser) {
                      return <span key={typing_user_id} className="text-xs text-[var(--text-muted)] italic animate-pulse">{typingUser.display_name} is typing...</span>
                  }
                  return null;
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 bg-[var(--background)] border-t border-[var(--border)]">
              <form onSubmit={handleSendMessage} className="flex gap-3 items-center max-w-4xl mx-auto">
                <button type="button" className="text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors p-2" title="Attach file (coming soon)">
                   <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/></svg>
                </button>
                <input
                  type="text"
                  value={newMessage}
                  onChange={handleTyping}
                  placeholder="Send a message..."
                  className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-full px-5 py-2.5 focus:outline-none focus:ring-1 focus:ring-[var(--primary)] transition-shadow text-[15px]"
                />
                <button type="submit" disabled={!newMessage.trim()} className="bg-[var(--primary)] text-white rounded-full w-10 h-10 flex items-center justify-center p-0 flex-shrink-0 disabled:opacity-50 hover:opacity-90 transition-opacity">
                  <svg className="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                  </svg>
                </button>
              </form>
            </div>
      </div>
      ) : (
      <div className={`${isMobile ? 'hidden' : 'flex'} flex-1 flex flex-col items-center justify-center bg-[var(--surface)]`}>
            <div className="w-24 h-24 bg-[var(--primary)] rounded-full mb-6 flex items-center justify-center opacity-10">
              <svg className="w-12 h-12 text-[var(--primary)]" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.002 21a2 2 0 002 2h16a2 2 0 002-2V7.514l-10 6.666L2 7.514V21z" />
                <path d="M2.002 4.486A2 2 0 014.002 3h16a2 2 0 012 1.486L12 11.152 2.002 4.486z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-2">Signal Clone</h2>
            <p className="text-[var(--text-muted)] text-center max-w-sm mb-4">
              Select a chat to start messaging or add a new contact by phone number.
            </p>
            <p className="text-xs text-[var(--text-muted)] border border-[var(--border)] rounded px-3 py-1">
              End-to-End Encryption Simulated
            </p>
      </div>
      )}

      {/* Group/Contact Details Pane */}
      {showGroupDetails && activeConv && (
          <div className="w-80 border-l border-[var(--border)] bg-[var(--background)] flex flex-col h-full overflow-y-auto">
             <div className="p-4 flex items-center gap-3 border-b border-[var(--border)] sticky top-0 bg-[var(--background)] z-10">
                 <button onClick={() => setShowGroupDetails(false)} className="text-[var(--text-muted)] hover:text-red-500">✕</button>
                 <h2 className="font-bold">Details</h2>
             </div>
             <div className="p-6 flex flex-col items-center border-b border-[var(--border)]">
                 {renderAvatar(activeConv.avatar_url, activeConv.name, activeConv.type === "group", "w-24 h-24 mb-4")}
                 <h2 className="text-xl font-bold text-center">{activeConv.name || "Unknown"}</h2>
                 <p className="text-sm text-[var(--text-muted)]">{activeConv.type === "group" ? `${activeConv.members.length} members` : 'Direct Message'}</p>
             </div>
             
             <div className="p-4">
                 <h3 className="text-sm font-semibold text-[var(--text-muted)] mb-3">Members</h3>
                 <div className="space-y-4">
                     {activeConv.members.map(m => {
                         const isOnline = onlineUsers.has(m.user_id);
                         return (
                             <div key={m.user_id} className="flex items-center gap-3">
                                 {renderAvatar(m.avatar_url, m.display_name, false, "w-10 h-10", isOnline)}
                                 <div className="flex-1 min-w-0">
                                     <h4 className="font-semibold text-sm truncate text-[var(--foreground)]">{m.display_name} {m.user_id === currentUser?.id ? "(You)" : ""}</h4>
                                     <p className="text-xs text-[var(--text-muted)]">{isOnline ? "Online" : "Last seen recently"}</p>
                                 </div>
                                 {m.role === "admin" && (
                                     <span className="text-[10px] uppercase font-bold text-[var(--primary)] bg-blue-100 dark:bg-blue-900 px-2 py-0.5 rounded">Admin</span>
                                 )}
                             </div>
                         );
                     })}
                 </div>
                 
                 {activeConv.type === "group" && (
                     <button onClick={() => alert("Add members UI coming soon")} className="mt-4 text-sm text-[var(--primary)] hover:underline flex items-center gap-2">
                         <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/></svg>
                         Add members
                     </button>
                 )}
             </div>
          </div>
      )}

    </div>
  );
}
