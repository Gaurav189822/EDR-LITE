import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Alerts from './pages/Alerts'
import Dashboard from './pages/Dashboard'
import DetectionRules from './pages/DetectionRules'
import Processes from './pages/Processes'
import ProcessTree from './pages/ProcessTree'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/processes" element={<Processes />} />
        <Route path="/rules" element={<DetectionRules />} />
        <Route path="/process-tree/:id" element={<ProcessTree />} />
      </Routes>
    </Layout>
  )
}

export default App