import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { chat } from '../services/api';

interface Message {
  text: string;
  isUser: boolean;
  context?: string;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setLoading(true);

    // Add user message
    setMessages(prev => [...prev, { text: userMessage, isUser: true }]);

    try {
      const response = await chat(userMessage);
      setMessages(prev => [
        ...prev,
        {
          text: response.response,
          isUser: false,
          context: response.context,
        },
      ]);
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          text: 'Sorry, I encountered an error processing your request.',
          isUser: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Chat with Your Knowledge Graph
      </Typography>
      
      <Box sx={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
        <List sx={{ flexGrow: 1, overflow: 'auto', mb: 2 }}>
          {messages.map((message, index) => (
            <ListItem
              key={index}
              sx={{
                flexDirection: 'column',
                alignItems: message.isUser ? 'flex-end' : 'flex-start',
              }}
            >
              <Paper
                sx={{
                  p: 1,
                  bgcolor: message.isUser ? 'primary.main' : 'background.paper',
                  maxWidth: '80%',
                }}
              >
                <ListItemText
                  primary={message.text}
                  sx={{ 
                    '& .MuiListItemText-primary': {
                      color: message.isUser ? 'white' : 'text.primary',
                    }
                  }}
                />
              </Paper>
              {message.context && !message.isUser && (
                <Typography
                  variant="caption"
                  sx={{ mt: 1, color: 'text.secondary' }}
                >
                  Context from graph: {message.context}
                </Typography>
              )}
            </ListItem>
          ))}
        </List>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your work orders..."
            disabled={loading}
          />
          <Button
            variant="contained"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            startIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
          >
            Send
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default ChatInterface;
