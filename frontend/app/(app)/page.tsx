import { ChatScreen } from "@/components/chat/ChatScreen";

// The landing page and the conversation are one screen: with no messages it
// shows the hero, and the composer settles to the bottom once a chat starts.
export default function HomePage() {
  return <ChatScreen />;
}
