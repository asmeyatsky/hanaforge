import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import ProgrammeList from './components/ProgrammeList';
import ProgrammeDetail from './components/ProgrammeDetail';
import DiscoveryPanel from './components/DiscoveryPanel';
import AbapAnalysisPanel from './components/AbapAnalysisPanel';
import DataReadinessPanel from './components/DataReadinessPanel';
import TestForgePanel from './components/TestForgePanel';
import InfrastructurePanel from './components/InfrastructurePanel';
import MigrationPanel from './components/MigrationPanel';
import CutoverPanel from './components/CutoverPanel';
import HanaBigQueryPanel from './components/HanaBigQueryPanel';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/programmes" element={<ProgrammeList />} />
        <Route path="/programmes/:id" element={<ProgrammeDetail />} />
        <Route path="/programmes/:id/discovery" element={<DiscoveryPanel />} />
        <Route path="/programmes/:id/analysis" element={<AbapAnalysisPanel />} />
        <Route path="/programmes/:id/data-readiness" element={<DataReadinessPanel />} />
        <Route path="/programmes/:id/hana-bigquery" element={<HanaBigQueryPanel />} />
        <Route path="/programmes/:id/test-forge" element={<TestForgePanel />} />
        <Route path="/programmes/:id/infrastructure" element={<InfrastructurePanel />} />
        <Route path="/programmes/:id/migration" element={<MigrationPanel />} />
        <Route path="/programmes/:id/cutover" element={<CutoverPanel />} />
      </Route>
    </Routes>
  );
}

export default App;
