import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import ProgrammeList from './components/ProgrammeList';
import ProgrammeDetail from './components/ProgrammeDetail';
import DiscoveryPanel from './components/DiscoveryPanel';
import AbapAnalysisPanel from './components/AbapAnalysisPanel';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/programmes" element={<ProgrammeList />} />
        <Route path="/programmes/:id" element={<ProgrammeDetail />} />
        <Route path="/programmes/:id/discovery" element={<DiscoveryPanel />} />
        <Route path="/programmes/:id/analysis" element={<AbapAnalysisPanel />} />
      </Route>
    </Routes>
  );
}

export default App;
