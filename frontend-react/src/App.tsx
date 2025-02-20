import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button, Box } from '@mui/material';
import AddContact from './components/AddContact';
import ContactList from './components/ContactList';
import Homepage from './components/Homepage';

function App() {
  return (
    <Router>
      <AppBar position="fixed" sx={{ width: '100%', zIndex: 1100 }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Smart CRM
          </Typography>
          <Button color="inherit" component={Link} to="/contacts">
            Contacts
          </Button>
          <Button color="inherit" component={Link} to="/add-contact">
            Add Contact
          </Button>
        </Toolbar>
      </AppBar>

      {/* Dynamic spacing to accommodate AppBar height */}
      <Box sx={{ height: (theme) => theme.mixins.toolbar.minHeight }} />

      <Routes>
        <Route path="/" element={<Homepage />} />
      </Routes>

      <Container
        maxWidth="xl"
        sx={{
          mt: 4,
          px: { xs: 2, sm: 4, md: 6 }, // Responsive padding
          width: '100%',
          minHeight: 'calc(100vh - 64px)', // Full height minus AppBar
          backgroundColor: '#fafafa' // Light background for better visual separation
        }}
      >
        <Routes>
          <Route path="/contacts" element={<ContactList />} />
          <Route path="/add-contact" element={<AddContact />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
