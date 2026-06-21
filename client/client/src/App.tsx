import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { RequireAuth } from "./components/RequireAuth";

import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Invoices from "./pages/Invoices";
import InvoiceDetail from "./pages/InvoiceDetail";
import Customers from "./pages/Customers";
import Inventory from "./pages/Inventory";
import Evidence from "./pages/Evidence";
import Review from "./pages/Review";
import Readiness from "./pages/Readiness";
import Export from "./pages/Export";
import Help from "./pages/Help";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

function guard(Component: React.ComponentType) {
  return () => (
    <RequireAuth>
      <Component />
    </RequireAuth>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Landing} />
      <Route path="/auth" component={Auth} />
      <Route path="/dashboard" component={guard(Dashboard)} />
      <Route path="/invoices" component={guard(Invoices)} />
      <Route path="/invoices/:id" component={guard(InvoiceDetail)} />
      <Route path="/customers" component={guard(Customers)} />
      <Route path="/inventory" component={guard(Inventory)} />
      <Route path="/evidence" component={guard(Evidence)} />
      <Route path="/review" component={guard(Review)} />
      <Route path="/readiness" component={guard(Readiness)} />
      <Route path="/export" component={guard(Export)} />
      <Route path="/help" component={guard(Help)} />
      <Route path="/profile" component={guard(Profile)} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Router />
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
