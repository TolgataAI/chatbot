import { useState, useEffect } from 'react'
import axios from 'axios'

function Admin() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notes, setNotes] = useState([])
  const [editingNote, setEditingNote] = useState(null)
  const [newNote, setNewNote] = useState({ title: '', content: '' })
  const [loading, setLoading] = useState(false)

  const token = sessionStorage.getItem('adminToken')

  useEffect(() => {
    if (token) {
      setIsAuthenticated(true)
      fetchNotes()
    }
  }, [])

  const fetchNotes = async () => {
    try {
      const response = await axios.get('/api/notes', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotes(response.data)
    } catch (err) {
      console.error('Failed to fetch notes:', err)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await axios.post('/api/auth', { password })
      if (response.data.success) {
        sessionStorage.setItem('adminToken', response.data.token)
        setIsAuthenticated(true)
        fetchNotes()
      }
    } catch (err) {
      setError('Invalid password')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    sessionStorage.removeItem('adminToken')
    setIsAuthenticated(false)
    setNotes([])
  }

  const handleAddNote = async (e) => {
    e.preventDefault()
    if (!newNote.content.trim()) return

    setLoading(true)
    try {
      const response = await axios.post('/api/notes', newNote, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotes([...notes, response.data])
      setNewNote({ title: '', content: '' })
    } catch (err) {
      console.error('Failed to add note:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateNote = async (e) => {
    e.preventDefault()
    if (!editingNote.content.trim()) return

    setLoading(true)
    try {
      const response = await axios.put(`/api/notes/${editingNote.id}`, {
        title: editingNote.title,
        content: editingNote.content
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotes(notes.map(n => n.id === editingNote.id ? response.data : n))
      setEditingNote(null)
    } catch (err) {
      console.error('Failed to update note:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm('Are you sure you want to delete this note?')) return

    try {
      await axios.delete(`/api/notes/${noteId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotes(notes.filter(n => n.id !== noteId))
    } catch (err) {
      console.error('Failed to delete note:', err)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <h2>Admin Login</h2>
        <form className="login-form" onSubmit={handleLogin}>
          <input
            type="password"
            placeholder="Enter admin password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        {error && <p className="error-message">{error}</p>}
      </div>
    )
  }

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h2>Manage Your Notes</h2>
        <button className="logout-btn" onClick={handleLogout}>Logout</button>
      </div>

      <div className="note-editor">
        <h3>{editingNote ? 'Edit Note' : 'Add New Note'}</h3>
        <form onSubmit={editingNote ? handleUpdateNote : handleAddNote}>
          <input
            type="text"
            placeholder="Note title (optional)"
            value={editingNote ? editingNote.title : newNote.title}
            onChange={(e) => editingNote
              ? setEditingNote({...editingNote, title: e.target.value})
              : setNewNote({...newNote, title: e.target.value})
            }
          />
          <textarea
            placeholder="Write your note here... (e.g., facts about yourself, your opinions, knowledge you want the chatbot to know)"
            value={editingNote ? editingNote.content : newNote.content}
            onChange={(e) => editingNote
              ? setEditingNote({...editingNote, content: e.target.value})
              : setNewNote({...newNote, content: e.target.value})
            }
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : (editingNote ? 'Update Note' : 'Add Note')}
          </button>
          {editingNote && (
            <button
              type="button"
              className="cancel-btn"
              onClick={() => setEditingNote(null)}
            >
              Cancel
            </button>
          )}
        </form>
      </div>

      <div className="notes-list">
        <h3>Your Notes ({notes.length})</h3>
        {notes.length === 0 ? (
          <p className="no-notes">No notes yet. Add your first note above!</p>
        ) : (
          notes.map(note => (
            <div key={note.id} className="note-item">
              <h4>{note.title}</h4>
              <p>{note.content}</p>
              <div className="note-actions">
                <button
                  className="edit-btn"
                  onClick={() => setEditingNote(note)}
                >
                  Edit
                </button>
                <button
                  className="delete-btn"
                  onClick={() => handleDeleteNote(note.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Admin
