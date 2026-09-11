import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { OilIndiaBrandmark } from '../components/common/OilIndiaBrandmark';
import heroImage from '../assets/image.png';

const settleEase = [0.22, 1, 0.36, 1] as const;

export function LandingPage() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [exiting, setExiting] = useState(false);

  function enterSentinel() {
    if (exiting) return;
    setExiting(true);
    window.setTimeout(() => navigate('/login'), reduceMotion ? 80 : 720);
  }

  const motionProps = reduceMotion
    ? {
        initial: false,
        animate: { opacity: 1, scale: 1, y: 0 },
      }
    : undefined;

  const cornerContainer: Variants = {
    hidden: {},
    show: { transition: { staggerChildren: reduceMotion ? 0 : 0.14, delayChildren: reduceMotion ? 0 : 1.15 } },
  };
  const fromTop: Variants = {
    hidden: reduceMotion ? { opacity: 1 } : { opacity: 0, y: -10 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: settleEase } },
  };
  const fromBottom: Variants = {
    hidden: reduceMotion ? { opacity: 1 } : { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: settleEase } },
  };

  return (
    <main className="relative min-h-[100svh] overflow-hidden bg-void text-ink">
      <motion.img
        src={heroImage}
        alt=""
        aria-hidden="true"
        className="absolute inset-0 h-full w-full object-cover"
        initial={reduceMotion ? false : { opacity: 0, scale: 1.09 }}
        animate={{
          opacity: exiting ? 0.12 : 0.82,
          scale: exiting ? 1.055 : 1,
        }}
        transition={{ duration: exiting ? 0.7 : 2.2, ease: settleEase }}
      />

      <motion.div
        className="absolute inset-0 bg-[linear-gradient(90deg,rgb(0_0_0_/_0.82),rgb(0_0_0_/_0.50)_45%,rgb(0_0_0_/_0.84)),linear-gradient(180deg,rgb(0_0_0_/_0.50),rgb(0_0_0_/_0.72)_70%,rgb(0_0_0_/_0.94))]"
        initial={reduceMotion ? false : { opacity: 0 }}
        animate={{ opacity: exiting ? 1 : 0.94 }}
        transition={{ duration: exiting ? 0.55 : 1.15, delay: exiting ? 0 : 0.2, ease: settleEase }}
      />

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_47%,rgb(212_255_63_/_0.11),transparent_24%),radial-gradient(circle_at_72%_22%,rgb(61_220_151_/_0.09),transparent_26%)] opacity-80" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 border-t border-hivis-edge/30 bg-gradient-to-b from-hivis/[0.035] to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(to_bottom,rgb(255_255_255_/_0.018)_0px,rgb(255_255_255_/_0.018)_1px,transparent_1px,transparent_4px)] opacity-35" />

      {/* One-shot boot sweep: a thin hi-vis line drops down the screen once on
          load, reading as "the system just switched on" before anything else
          settles into place. */}
      {!reduceMotion && (
        <motion.div
          className="pointer-events-none absolute inset-x-0 top-0 z-20 h-px bg-gradient-to-r from-transparent via-hivis to-transparent"
          initial={{ y: 0, opacity: 0.9 }}
          animate={{ y: '100vh', opacity: [0.9, 0.9, 0] }}
          transition={{ duration: 1.1, ease: 'easeIn', times: [0, 0.7, 1] }}
        />
      )}

      <motion.div
        variants={cornerContainer}
        initial="hidden"
        animate={exiting ? 'hidden' : 'show'}
        className="pointer-events-none absolute inset-0 z-10 flex flex-col justify-between p-6 sm:p-10"
      >
        <div className="flex items-start justify-between">
          <motion.div variants={fromTop} className="flex items-start gap-3">
            <span className="mt-1.5 h-px w-6 bg-ink-3/70" />
            <div className="font-mono text-[10px] uppercase leading-5 tracking-[0.2em] text-ink-3">
              <div>Oil India Limited</div>
              <div>A safer tomorrow</div>
            </div>
          </motion.div>
          <motion.div variants={fromTop}>
            <OilIndiaBrandmark />
          </motion.div>
        </div>

        <div className="flex items-end justify-end">
          <motion.div variants={fromBottom} className="flex flex-col items-end gap-2">
            <div className="flex items-start gap-3 text-right">
              <ul className="space-y-0.5 font-mono text-[10px] uppercase tracking-[0.2em]">
                <li className="text-hivis">Safer</li>
                <li className="text-hivis/85">Smarter</li>
                <li className="text-low">Stronger</li>
                <li className="text-ink-2">Together</li>
              </ul>
              <span className="mt-0.5 h-16 w-px bg-line-bright" />
            </div>
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-ink-4">Oil India Limited</span>
          </motion.div>
        </div>
      </motion.div>

      <motion.section
        className="relative z-10 flex min-h-[100svh] items-center justify-center px-6 py-12"
        animate={{ opacity: exiting ? 0 : 1, scale: exiting ? 0.985 : 1 }}
        transition={{ duration: 0.45, ease: settleEase }}
      >
        <div className="mx-auto flex w-full max-w-4xl flex-col items-center text-center">
          <motion.div
            {...motionProps}
            initial={reduceMotion ? false : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.42, ease: settleEase }}
          >
            <motion.h1
              initial={reduceMotion ? false : { letterSpacing: '0.3em', opacity: 0 }}
              animate={{ letterSpacing: '0em', opacity: 1 }}
              transition={{ duration: 1, delay: 0.78, ease: settleEase }}
              className="font-sans text-5xl font-semibold leading-none text-ink [text-shadow:0_0_28px_rgb(255_255_255_/_0.16)] sm:text-6xl lg:text-[6.5rem]"
            >
              SENTINEL
            </motion.h1>
            <div className="font-mono text-[0.72rem] font-medium uppercase tracking-[0.2em] leading-6 text-hivis sm:text-sm">
              Safety Intelligence Platform
            </div>
            <motion.div
              initial={reduceMotion ? false : { scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.6, delay: 1.15, ease: settleEase }}
              className="mx-auto mt-6 h-px w-14 origin-center bg-line-bright"
            />
            <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-ink-2 sm:text-lg">
              AI-powered safety intelligence for high-risk operations.
            </p>
          </motion.div>

          <motion.div
            {...motionProps}
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 210, damping: 20, delay: 1.15 }}
            className="mt-9"
          >
            <button
              type="button"
              onClick={enterSentinel}
              disabled={exiting}
              className="group inline-flex min-h-12 min-w-64 items-center justify-center gap-4 border border-hivis-edge bg-void/45 px-7 py-3 font-mono text-2xs font-medium uppercase text-ink backdrop-blur-sm transition-[background-color,border-color,color,transform,box-shadow] duration-200 hover:border-hivis hover:bg-hivis hover:text-on-hivis hover:shadow-[0_0_34px_rgb(212_255_63_/_0.18)] active:scale-[0.985] disabled:pointer-events-none disabled:opacity-80"
            >
              <span>Enter Sentinel</span>
              <ArrowRight
                className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1"
                strokeWidth={2.4}
              />
            </button>
          </motion.div>
        </div>
      </motion.section>
    </main>
  );
}
