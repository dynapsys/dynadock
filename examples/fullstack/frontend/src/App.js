import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [todos, setTodos] = useState([]);
  const [newTodo, setNewTodo] = useState('');
  const [showLogin, setShowLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchProfile();
      fetchTodos();
    }
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/profile`);
      setUser(response.data);
      setIsLoggedIn(true);
    } catch (error) {
      console.error('Error fetching profile:', error);
      localStorage.removeItem('token');
    }
  };

  const fetchTodos = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/todos`);
      setTodos(response.data);
    } catch (error) {
      toast.error('Failed to fetch todos');
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = showLogin ? 'login' : 'register';
    
    try {
      const response = await axios.post(`${API_URL}/api/auth/${endpoint}`, formData);
      localStorage.setItem('token', response.data.token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
      setUser(response.data.user);
      setIsLoggedIn(true);
      toast.success(`Successfully ${showLogin ? 'logged in' : 'registered'}!`);
      fetchTodos();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Authentication failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setIsLoggedIn(false);
    setUser(null);
    setTodos([]);
    toast.info('Logged out successfully');
  };

  const addTodo = async (e) => {
    e.preventDefault();
    if (!newTodo.trim()) return;

    try {
      const response = await axios.post(`${API_URL}/api/todos`, { title: newTodo });
      setTodos([response.data, ...todos]);
      setNewTodo('');
      toast.success('Todo added!');
    } catch (error) {
      toast.error('Failed to add todo');
    }
  };

  const toggleTodo = async (id, completed) => {
    try {
      const response = await axios.put(`${API_URL}/api/todos/${id}`, { completed: !completed });
      setTodos(todos.map(todo => todo.id === id ? response.data : todo));
    } catch (error) {
      toast.error('Failed to update todo');
    }
  };

  const deleteTodo = async (id) => {
    try {
      await axios.delete(`${API_URL}/api/todos/${id}`);
      setTodos(todos.filter(todo => todo.id !== id));
      toast.success('Todo deleted!');
    } catch (error) {
      toast.error('Failed to delete todo');
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="App">
        <div className="auth-container">
          <h1>🚀 DynaDock Fullstack</h1>
          <form onSubmit={handleAuth} className="auth-form">
            <h2>{showLogin ? 'Login' : 'Register'}</h2>
            {!showLogin && (
              <input
                type="text"
                placeholder="Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
            />
            <button type="submit">{showLogin ? 'Login' : 'Register'}</button>
            <p onClick={() => setShowLogin(!showLogin)}>
              {showLogin ? "Don't have an account? Register" : "Already have an account? Login"}
            </p>
          </form>
        </div>
        <ToastContainer />
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <h1>🚀 DynaDock Todo App</h1>
        <div className="user-info">
          <span>Welcome, {user?.name || user?.email}!</span>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </header>
      
      <main className="app-main">
        <form onSubmit={addTodo} className="todo-form">
          <input
            type="text"
            placeholder="Add a new todo..."
            value={newTodo}
            onChange={(e) => setNewTodo(e.target.value)}
          />
          <button type="submit">Add Todo</button>
        </form>

        <div className="todos-container">
          {todos.length === 0 ? (
            <p className="no-todos">No todos yet. Add one above!</p>
          ) : (
            <ul className="todos-list">
              {todos.map(todo => (
                <li key={todo.id} className={`todo-item ${todo.completed ? 'completed' : ''}`}>
                  <input
                    type="checkbox"
                    checked={todo.completed}
                    onChange={() => toggleTodo(todo.id, todo.completed)}
                  />
                  <span>{todo.title}</span>
                  <button onClick={() => deleteTodo(todo.id)} className="delete-btn">×</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
      
      <ToastContainer />
    </div>
  );
}

export default App;
