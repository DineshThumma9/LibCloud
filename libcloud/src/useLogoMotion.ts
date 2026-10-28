import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import type { Logo } from './schemas';

export function useLogoMotion(logos: Logo[]) {
  const motionRefs = useRef<Map<string, SVGGElement>>(new Map());
  const enteredIds = useRef<Set<string>>(new Set());

  // Animate newly added logos (entrance animation)
  useEffect(() => {
    if (!logos || logos.length === 0) {
      enteredIds.current.clear();
      return;
    }

    const newNodes: SVGGElement[] = [];
    logos.forEach((logo) => {
      if (!enteredIds.current.has(logo.id)) {
        const el = motionRefs.current.get(logo.id);
        if (el) {
          newNodes.push(el);
          enteredIds.current.add(logo.id);
        }
      }
    });

    if (newNodes.length > 0) {
      gsap.fromTo(
        newNodes,
        { scale: 0, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.45,
          stagger: 0.03,
          ease: 'back.out(1.6)',
          overwrite: 'auto',
        }
      );
    }
  }, [logos]);

  const setMotionRef = (id: string, el: SVGGElement | null) => {
    if (el) {
      motionRefs.current.set(id, el);
    } else {
      motionRefs.current.delete(id);
    }
  };

  const handlePointerEnter = (id: string) => {
    const el = motionRefs.current.get(id);
    if (el) {
      gsap.to(el, {
        scale: 1.18,
        duration: 0.22,
        ease: 'power2.out',
        overwrite: 'auto',
      });
    }
  };

  const handlePointerLeave = (id: string) => {
    const el = motionRefs.current.get(id);
    if (el) {
      gsap.to(el, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.out',
        overwrite: 'auto',
      });
    }
  };

  return {
    setMotionRef,
    handlePointerEnter,
    handlePointerLeave,
  };
}
