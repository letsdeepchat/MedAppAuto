import React, { useState } from 'react';
import {
  Container,
  TextField,
  Button,
  Typography,
  Box,
  Card,
  CardContent,
  Alert,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Grid,
  Avatar,
  CircularProgress
} from '@mui/material';
import {
  Login as LoginIcon,
  PersonAdd as RegisterIcon,
  Send as SendIcon,
  MedicalServices as MedicalIcon,
  Chat as ChatIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';
// import './App.css';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
  },
});

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [automationStatus, setAutomationStatus] = useState('');
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    const username = e.target.username.value;
    const password = e.target.password.value;

    try {
      // For demo purposes, accept any username/password combination
      // In production, this would validate against the backend
      if (username && password) {
        const mockToken = btoa(`${username}:${Date.now()}`);
        setToken(mockToken);
        localStorage.setItem('token', mockToken);
        setAutomationStatus('Login successful!');
      } else {
        setAutomationStatus('Please enter both username and password');
      }
    } catch (error) {
      setAutomationStatus('Authentication error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim()) return;

    const userMessage = { role: 'user', content: currentMessage };
    setMessages(prev => [...prev, userMessage]);
    setChatLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: currentMessage })
      });

      const data = await response.json();

      if (response.ok) {
        const assistantMessage = { role: 'assistant', content: data.response };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Network error. Please check your connection and try again.' }]);
    } finally {
      setChatLoading(false);
      setCurrentMessage('');
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('token');
    setMessages([]);
    setAutomationStatus('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Avatar sx={{ bgcolor: 'primary.main', width: 60, height: 60, mx: 'auto', mb: 2 }}>
            <MedicalIcon sx={{ fontSize: 30 }} />
          </Avatar>
          <Typography variant="h4" component="h1" gutterBottom>
            MedAppAuto - Medical Scheduling Assistant
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Your intelligent medical appointment scheduling companion
          </Typography>
        </Box>

        {!token ? (
          <Grid container spacing={3} justifyContent="center">
            <Grid item xs={12} md={6}>
              <Card elevation={3}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                    <Avatar sx={{ bgcolor: isLogin ? 'primary.main' : 'secondary.main' }}>
                      {isLogin ? <LoginIcon /> : <RegisterIcon />}
                    </Avatar>
                  </Box>
                  <Typography variant="h5" component="h2" gutterBottom align="center">
                    {isLogin ? 'Login' : 'Register'}
                  </Typography>

                  <form onSubmit={handleAuth}>
                    <TextField
                      fullWidth
                      label="Username"
                      name="username"
                      variant="outlined"
                      margin="normal"
                      required
                    />
                    <TextField
                      fullWidth
                      label="Password"
                      name="password"
                      type="password"
                      variant="outlined"
                      margin="normal"
                      required
                    />
                    <Button
                      type="submit"
                      fullWidth
                      variant="contained"
                      sx={{ mt: 2, mb: 2 }}
                      disabled={loading}
                    >
                      {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
                    </Button>
                  </form>

                  <Button
                    fullWidth
                    variant="text"
                    onClick={() => setIsLogin(!isLogin)}
                    sx={{ mt: 1 }}
                  >
                    {isLogin ? 'Need an account? Register' : 'Already have an account? Login'}
                  </Button>

                  {automationStatus && (
                    <Alert severity={automationStatus.includes('successful') ? 'success' : 'error'} sx={{ mt: 2 }}>
                      {automationStatus}
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card elevation={3}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <ChatIcon sx={{ mr: 1 }} />
                      <Typography variant="h5" component="h2">
                        Medical Scheduling Assistant
                      </Typography>
                    </Box>
                    <Button variant="outlined" onClick={handleLogout} startIcon={<LogoutIcon />}>
                      Logout
                    </Button>
                  </Box>

                  {/* Chat Messages */}
                  <Box sx={{
                    height: 400,
                    overflowY: 'auto',
                    mb: 2,
                    p: 2,
                    bgcolor: 'grey.50',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'grey.300'
                  }}>
                    {messages.length === 0 ? (
                      <Box sx={{ textAlign: 'center', py: 4 }}>
                        <MedicalIcon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                        <Typography variant="h6" color="text.secondary">
                          Welcome to MedAppAuto!
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          I'm here to help you schedule medical appointments. How can I assist you today?
                        </Typography>
                      </Box>
                    ) : (
                      messages.map((message, index) => (
                        <Box
                          key={index}
                          sx={{
                            display: 'flex',
                            justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                            mb: 2
                          }}
                        >
                          <Box
                            sx={{
                              maxWidth: '70%',
                              p: 2,
                              borderRadius: 2,
                              bgcolor: message.role === 'user' ? 'primary.main' : 'white',
                              color: message.role === 'user' ? 'white' : 'text.primary',
                              boxShadow: 1
                            }}
                          >
                            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                              {message.content}
                            </Typography>
                          </Box>
                        </Box>
                      ))
                    )}
                    {chatLoading && (
                      <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                        <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'white', boxShadow: 1 }}>
                          <CircularProgress size={20} />
                        </Box>
                      </Box>
                    )}
                  </Box>

                  {/* Message Input */}
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <TextField
                      fullWidth
                      placeholder="Type your message here..."
                      value={currentMessage}
                      onChange={(e) => setCurrentMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={chatLoading}
                      variant="outlined"
                    />
                    <Button
                      variant="contained"
                      onClick={sendMessage}
                      disabled={!currentMessage.trim() || chatLoading}
                      sx={{ px: 3 }}
                    >
                      <SendIcon />
                    </Button>
                  </Box>

                  {automationStatus && (
                    <Alert
                      severity={automationStatus.includes('successful') || automationStatus.includes('success') ? 'success' : 'info'}
                      sx={{ mt: 2 }}
                    >
                      {automationStatus}
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Container>
    </ThemeProvider>
  );
}

export default App;