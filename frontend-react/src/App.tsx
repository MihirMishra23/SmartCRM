import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button } from '@mui/material';
import AddContact from './components/AddContact';
import ContactList from './components/ContactList';

function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Smart CRM
          </Typography>
          <Button color="inherit" component={Link} to="/">
            Contacts
          </Button>
          <Button color="inherit" component={Link} to="/add-contact">
            Add Contact
          </Button>
        </Toolbar>
      </AppBar>

      <Container sx={{ mt: 4 }}>
        <Routes>
          <Route path="/" element={<ContactList />} />
          <Route path="/add-contact" element={<AddContact />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
