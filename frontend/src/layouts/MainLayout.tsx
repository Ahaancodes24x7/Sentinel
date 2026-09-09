import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from '../components/layout/Sidebar';
import { Topbar } from '../components/layout/Topbar';

export function MainLayout() {
  const location = useLocation();

  return (
    <div className="field-grid scanlines flex h-screen overflow-hidden bg-bg">
      {/* Ambient glow: two slow-drifting pools of light so the ground is never
          a flat void. Sits behind everything and takes no pointer events. */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="drift absolute -left-40 -top-40 h-[36rem] w-[36rem] rounded-full bg-hivis/[0.045] blur-[120px]" />
        <div
          className="drift absolute -bottom-52 right-[-10rem] h-[32rem] w-[32rem] rounded-full bg-info/[0.04] blur-[120px]"
          style={{ animationDelay: '-9s' }}
        />
      </div>

      <Sidebar />

      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <Topbar />

        <main className="min-h-0 flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="p-5"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
