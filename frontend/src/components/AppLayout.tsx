import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Breadcrumbs } from './Breadcrumbs'
import { UserProfile } from './UserProfile'

export function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <header className="app-header">
          <Breadcrumbs />
          <UserProfile />
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
