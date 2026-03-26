import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Channels from './pages/Channels';
import Summaries from './pages/Summaries';
import EmailSettings from './pages/EmailSettings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/channels" element={<Channels />} />
          <Route path="/summaries" element={<Summaries />} />
          <Route path="/email" element={<EmailSettings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
