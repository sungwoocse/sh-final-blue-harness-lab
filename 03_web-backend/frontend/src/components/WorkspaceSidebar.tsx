import { useParams, useLocation } from 'react-router-dom';
import { NavLink } from '@/components/NavLink';
import { cn } from '@/lib/utils';
import { 
  LayoutDashboard, 
  Code2, 
  Settings 
} from 'lucide-react';

export const WorkspaceSidebar = () => {
  const { workspaceId } = useParams();
  const location = useLocation();

  const links = [
    {
      to: `/workspaces/${workspaceId}`,
      label: 'Overview',
      icon: LayoutDashboard,
    },
    {
      to: `/workspaces/${workspaceId}/functions`,
      label: 'Functions',
      icon: Code2,
    },
    {
      to: `/workspaces/${workspaceId}/settings`,
      label: 'Settings',
      icon: Settings,
    },
  ];

  return (
    <nav className="flex flex-col gap-1 p-4">
      {links.map((link) => {
        const Icon = link.icon;
        const isActive = location.pathname === link.to;
        
        return (
          <NavLink
            key={link.to}
            to={link.to}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              isActive 
                ? "bg-accent text-accent-foreground font-medium" 
                : "text-muted-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {link.label}
          </NavLink>
        );
      })}
    </nav>
  );
};
