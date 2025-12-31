import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoginPage } from './pages/LoginPage'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { PlansPage } from './pages/PlansPage'
import { PlanDetailPage } from './pages/PlanDetailPage'
import { TasksPage } from './pages/TasksPage'
import { TaskDetailPage } from './pages/TaskDetailPage'
import { SettingsPage } from './pages/SettingsPage'
import { ClaudeCodeConsolePage } from './pages/ClaudeCodeConsolePage'
import './App.css'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <div className="App">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />

            {/* Protected routes with layout */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
              <Route path="/projects/:projectId/plans" element={<PlansPage />} />
              <Route path="/projects/:projectId/plans/:planId" element={<PlanDetailPage />} />
              <Route path="/projects/:projectId/tasks" element={<TasksPage />} />
              <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/debug/claude-code-console" element={<ClaudeCodeConsolePage />} />
            </Route>
          </Routes>
        </div>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
