import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { TopBar } from '@/components/ui/top-bar';
import { API_URL } from '@/constants/config';
import { colors, radius, space } from '@/constants/design';
import { api, type Chat, type ChatMessage } from '@/lib/api';
import { getToken } from '@/lib/auth';

type Msg = { id: string; role: 'user' | 'assistant'; content: string };

type Tab = 'new' | 'history';

export default function ChatScreen() {
  const [tab, setTab] = useState<Tab>('new');
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [loadingChats, setLoadingChats] = useState(false);
  const flatListRef = useRef<FlatList<Msg>>(null);

  const loadChats = useCallback(async () => {
    setLoadingChats(true);
    try {
      const list = await api.listChats();
      setChats(list);
    } catch {
      // silent
    } finally {
      setLoadingChats(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'history') loadChats();
  }, [tab, loadChats]);

  const openChat = async (chatId: string) => {
    try {
      const detail = await api.getChat(chatId);
      setMessages(
        detail.messages.map((m, i) => ({ id: `${chatId}-${i}`, role: m.role, content: m.content })),
      );
      setActiveChatId(chatId);
      setTab('new');
    } catch {
      // silent
    }
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');

    const userMsg: Msg = { id: `u-${Date.now()}`, role: 'user', content: text };
    const assistantMsg: Msg = { id: `a-${Date.now()}`, role: 'assistant', content: '' };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    try {
      let chatId = activeChatId;
      if (!chatId) {
        const chat = await api.createChat();
        chatId = chat.id;
        setActiveChatId(chatId);
      }

      const token = await getToken();
      const res = await fetch(`${API_URL}/chatbot/chats/${chatId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: text }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let assembled = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const chunk = line.slice(6).trim();
              if (chunk && chunk !== '[DONE]') {
                assembled += chunk;
                setMessages((prev) => [
                  ...prev.slice(0, -1),
                  { ...assistantMsg, content: assembled },
                ]);
              }
            }
          }
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { ...assistantMsg, content: 'Something went wrong. Please try again.' },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const startNewChat = () => {
    setActiveChatId(null);
    setMessages([]);
    setTab('new');
  };

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.topBarWrap}>
        <TopBar title="Chat" />
      </View>

      {/* Segmented toggle */}
      <View style={styles.toggle}>
        <ToggleBtn label="New Chat" active={tab === 'new'} onPress={() => setTab('new')} />
        <ToggleBtn label="Chats" active={tab === 'history'} onPress={() => setTab('history')} />
      </View>

      {tab === 'history' ? (
        <HistoryView
          chats={chats}
          loading={loadingChats}
          onSelect={openChat}
          onNewChat={startNewChat}
        />
      ) : (
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={8}>
          {messages.length === 0 ? (
            <View style={styles.empty}>
              <Ionicons name="chatbubble-ellipses-outline" size={48} color={colors.faint} />
              <AppText variant="subtitle" color={colors.muted}>
                Ask anything suspicious
              </AppText>
              <AppText variant="caption" style={{ textAlign: 'center' }}>
                Describe a call, message, or number you&apos;re unsure about and get a risk
                assessment.
              </AppText>
            </View>
          ) : (
            <FlatList
              ref={flatListRef}
              data={messages}
              keyExtractor={(m) => m.id}
              contentContainerStyle={styles.messageList}
              onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
              renderItem={({ item }) => <MessageBubble msg={item} />}
            />
          )}

          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              value={input}
              onChangeText={setInput}
              placeholder="Describe what's suspicious..."
              placeholderTextColor={colors.faint}
              multiline
              maxLength={1000}
              onSubmitEditing={sendMessage}
            />
            <Pressable
              onPress={sendMessage}
              disabled={!input.trim() || streaming}
              style={({ pressed }) => [
                styles.sendBtn,
                { opacity: !input.trim() || streaming ? 0.4 : pressed ? 0.7 : 1 },
              ]}>
              {streaming ? (
                <ActivityIndicator size="small" color={colors.white} />
              ) : (
                <Ionicons name="arrow-up" size={18} color={colors.white} />
              )}
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

function MessageBubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === 'user';
  return (
    <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
      <AppText
        variant="body"
        color={isUser ? colors.white : colors.ink}
        style={isUser ? undefined : { lineHeight: 22 }}>
        {msg.content || '…'}
      </AppText>
    </View>
  );
}

function HistoryView({
  chats,
  loading,
  onSelect,
  onNewChat,
}: {
  chats: Chat[];
  loading: boolean;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}) {
  if (loading) {
    return (
      <View style={styles.empty}>
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }

  if (chats.length === 0) {
    return (
      <View style={styles.empty}>
        <Ionicons name="chatbubbles-outline" size={48} color={colors.faint} />
        <AppText variant="subtitle" color={colors.muted}>
          No chats yet
        </AppText>
        <Pressable onPress={onNewChat} style={styles.newChatBtn}>
          <AppText variant="bodyStrong" color={colors.white}>
            Start a new chat
          </AppText>
        </Pressable>
      </View>
    );
  }

  return (
    <FlatList
      data={chats}
      keyExtractor={(c) => c.id}
      contentContainerStyle={{ padding: space.lg, gap: space.sm }}
      renderItem={({ item }) => (
        <Pressable
          onPress={() => onSelect(item.id)}
          style={({ pressed }) => [styles.chatRow, { opacity: pressed ? 0.7 : 1 }]}>
          <Ionicons name="chatbubble-outline" size={18} color={colors.teal} />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong" numberOfLines={1}>
              Chat {item.id.slice(0, 8)}…
            </AppText>
            <AppText variant="caption">
              {new Date(item.created_at).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </AppText>
          </View>
          <Ionicons name="chevron-forward" size={16} color={colors.faint} />
        </Pressable>
      )}
    />
  );
}

function ToggleBtn({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={[styles.toggleBtn, active && styles.toggleBtnActive]}>
      <AppText variant="bodyStrong" color={active ? colors.brand : colors.muted}>
        {label}
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  topBarWrap: { paddingHorizontal: space.xl, paddingTop: space.md, paddingBottom: space.sm },
  toggle: {
    flexDirection: 'row',
    marginHorizontal: space.xl,
    marginBottom: space.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: space.sm,
    alignItems: 'center',
    borderRadius: radius.sm,
  },
  toggleBtnActive: {
    backgroundColor: colors.brandTint,
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: space.xxl,
    gap: space.lg,
  },
  messageList: {
    padding: space.lg,
    gap: space.md,
    paddingBottom: space.xxl,
  },
  bubble: {
    maxWidth: '80%',
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    borderRadius: radius.lg,
  },
  bubbleUser: {
    alignSelf: 'flex-end',
    backgroundColor: colors.brand,
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    alignSelf: 'flex-start',
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    fontSize: 15,
    color: colors.ink,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.pill,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chatRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: space.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  newChatBtn: {
    backgroundColor: colors.brand,
    paddingHorizontal: space.xl,
    paddingVertical: space.md,
    borderRadius: radius.md,
  },
});
