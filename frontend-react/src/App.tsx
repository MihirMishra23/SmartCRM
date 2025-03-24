import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button, Box } from '@mui/material';
import AddContact from './components/AddContact';
import ContactList from './components/ContactList';
import Homepage from './components/Homepage';
import EmailList from './components/EmailList';

function App() {
  return (
    <Router>
      <AppBar position="fixed" sx={{ width: '100%', zIndex: 1100 }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Smart CRM
          </Typography>
          <Button color="inherit" component={Link} to="/">
            Home
          </Button>
          <Button color="inherit" component={Link} to="/contacts">
            Contacts
          </Button>
          <Button color="inherit" component={Link} to="/add-contact">
            Add Contact
          </Button>
          <Button color="inherit" component={Link} to="/emails">
            Emails
          </Button>
        </Toolbar>
      </AppBar>

      {/* Dynamic spacing to accommodate AppBar height */}
      <Box sx={{ height: (theme) => theme.mixins.toolbar.minHeight }} />


      <Container
        maxWidth={false}
        sx={{
          width: '100%',
          minHeight: 'calc(100vh - 64px)',
          backgroundColor: '#fafafa',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <Routes>
          <Route path="/" element={<Homepage />} />
          <Route path="/contacts" element={<ContactList />} />
          <Route path="/add-contact" element={<AddContact />} />
          <Route path="/emails" element={<EmailList />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
