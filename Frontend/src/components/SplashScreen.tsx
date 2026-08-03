import { motion } from "motion/react";
import beacLogo from "../../assets/logo_BEAC.png";

export default function SplashScreen() {
  return (
    <motion.div
      initial={{ opacity: 1 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35, ease: "easeInOut" }}
      className="fixed inset-0 z-100 flex items-center justify-center bg-[radial-gradient(circle_at_top_right,#1a428a_0%,#0D2D5E_70%)] select-none"
      aria-hidden="true"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center gap-4"
      >
        <div className="w-20 h-20 md:w-24 md:h-24 flex items-center justify-center">
          <img src={beacLogo} alt="Logo BEAC" className="w-full h-full object-contain" />
        </div>
        <div className="flex flex-col items-center leading-tight">
          <span className="font-sans font-extrabold text-xl md:text-2xl text-[#C8971A] tracking-tight">
            BEAC
          </span>
          <span className="text-[11px] md:text-xs text-white/70 tracking-[0.2em] font-semibold font-sans uppercase">
            Assistant IA
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
}
