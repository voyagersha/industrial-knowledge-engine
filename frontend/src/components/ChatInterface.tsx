import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  CircularProgress,
  Collapse,
} from '@mui/material';
import {
  Send as SendIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { chat } from '../services/api';

interface Message {
  text: string;
  isUser: boolean;
  context?: {
    type: string;
    data: any[];
    system_note?: string;
  };
  timestamp: Date;
}

// This interface is used internally by the chat function
interface ChatApiResponse {
  response: string;
  context?: {
    type: string;
    data: any[];
    system_note?: string;
  };
  error?: string;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedContext, setExpandedContext] = useState<number | null>(null);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setLoading(true);

    // Add user message
    setMessages(prev => [
      ...prev,
      {
        text: userMessage,
        isUser: true,
        timestamp: new Date()
      }
    ]);

    try {
      console.log('Sending chat request:', userMessage);
      const response: ChatApiResponse = await chat(userMessage);
      console.log('Received chat response:', response);

      if (response.error) {
        throw new Error(response.error);
      }

      if (!response.response) {
        throw new Error('Empty response received from the server');
      }

      setMessages(prev => [
        ...prev,
        {
          text: response.response,
          isUser: false,
          context: response.context,
          timestamp: new Date()
        },
      ]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = error instanceof Error ? error.message : 'An error occurred while processing your request';

      setMessages(prev => [
        ...prev,
        {
          text: `Error: ${errorMessage}. Please try again.`,
          isUser: false,
          timestamp: new Date()
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const toggleContext = (index: number) => {
    setExpandedContext(expandedContext === index ? null : index);
  };

  const formatContext = (context: Message['context']): string => {
    if (!context || !context.data) return '';

    try {
      const formattedData = {
        type: context.type,
        data: context.data,
        system_note: context.system_note
      };
      return JSON.stringify(formattedData, null, 2);
    } catch (error) {
      console.error('Error formatting context:', error);
      return 'Error formatting context data';
    }
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Chat with Your Knowledge Graph
      </Typography>

      <Box sx={{
        height: '500px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <List sx={{
          flexGrow: 1,
          overflow: 'auto',
          mb: 2,
          '& .MuiListItem-root': {
            flexDirection: 'column',
            alignItems: 'stretch',
          }
        }}>
          {messages.map((message, index) => (
            <ListItem
              key={index}
              sx={{
                mb: 1,
              }}
            >
              <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: message.isUser ? 'flex-end' : 'flex-start',
                width: '100%'
              }}>
                <Paper
                  sx={{
                    p: 2,
                    maxWidth: '80%',
                    bgcolor: message.isUser ? 'primary.main' : 'background.paper',
                    color: message.isUser ? 'white' : 'text.primary',
                    position: 'relative'
                  }}
                >
                  <Typography variant="body1" sx={{ wordBreak: 'break-word' }}>
                    {message.text}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      position: 'absolute',
                      bottom: 4,
                      right: 8,
                      opacity: 0.7
                    }}
                  >
                    {formatTimestamp(message.timestamp)}
                  </Typography>
                </Paper>

                {message.context && !message.isUser && (
                  <Box sx={{ mt: 1, alignSelf: 'flex-start', width: '100%' }}>
                    <Button
                      size="small"
                      onClick={() => toggleContext(index)}
                      endIcon={expandedContext === index ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      sx={{ textTransform: 'none' }}
                    >
                      {expandedContext === index ? 'Hide Context' : 'Show Context'}
                    </Button>
                    <Collapse in={expandedContext === index}>
                      <Paper
                        sx={{
                          mt: 1,
                          p: 2,
                          bgcolor: 'action.hover',
                          maxWidth: '100%',
                          '& pre': {
                            margin: 0,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            overflowX: 'auto'
                          }
                        }}
                      >
                        <pre>{formatContext(message.context)}</pre>
                      </Paper>
                    </Collapse>
                  </Box>
                )}
              </Box>
            </ListItem>
          ))}
        </List>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask about your work orders..."
            disabled={loading}
          />
          <Button
            variant="contained"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            sx={{ minWidth: '100px' }}
          >
            {loading ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              <>
                <SendIcon sx={{ mr: 1 }} />
                Send
              </>
            )}
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default ChatInterface;