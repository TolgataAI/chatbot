import { Routes, Route, Link } from 'react-router-dom'
import Admin from './pages/Admin'
import Chat from './pages/Chat'

function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">Personal Chatbot</div>
        <div className="nav-links">
          <Link to="/">Chat</Link>
          <Link to="/admin">Admin</Link>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
