import React from 'react';

/**
 * Inline SVG icon set.
 *
 * Deliberately hand-rolled rather than pulled from lucide-react: the installed
 * lucide version exports a different surface than this code needs, and a single
 * 24-line icon file removes a runtime dependency from the critical render path.
 * All icons inherit currentColor and are hidden from assistive tech by default.
 */

type IconProps = {
  size?: number;
  className?: string;
  strokeWidth?: number;
};

const base = (size: number, className?: string) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  xmlns: 'http://www.w3.org/2000/svg',
  className,
  'aria-hidden': true as const,
  focusable: 'false' as const,
});

const stroke = (w: number) => ({
  stroke: 'currentColor',
  strokeWidth: w,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
});

export const IconGauge: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M12 20a8 8 0 1 1 8-8" {...stroke(strokeWidth)} />
    <path d="m12 12 4.5-3.5" {...stroke(strokeWidth)} />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" />
  </svg>
);

export const IconChat: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M20 14a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Z" {...stroke(strokeWidth)} />
  </svg>
);

export const IconGraph: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <circle cx="6" cy="7" r="2.2" {...stroke(strokeWidth)} />
    <circle cx="18" cy="7" r="2.2" {...stroke(strokeWidth)} />
    <circle cx="12" cy="17.5" r="2.2" {...stroke(strokeWidth)} />
    <path d="M7.8 8.4 10.6 15.6M16.2 8.4 13.4 15.6M8.2 7h7.6" {...stroke(strokeWidth)} />
  </svg>
);

export const IconAlert: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M10.3 3.9 2.6 17.1A1.9 1.9 0 0 0 4.3 20h15.4a1.9 1.9 0 0 0 1.7-2.9L13.7 3.9a1.9 1.9 0 0 0-3.4 0Z" {...stroke(strokeWidth)} />
    <path d="M12 9.5v4M12 16.6v.4" {...stroke(strokeWidth)} />
  </svg>
);

export const IconUpload: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M21 15v3.5A2.5 2.5 0 0 1 18.5 21h-13A2.5 2.5 0 0 1 3 18.5V15" {...stroke(strokeWidth)} />
    <path d="M12 15V3M7.5 7.5 12 3l4.5 4.5" {...stroke(strokeWidth)} />
  </svg>
);

export const IconChart: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M3 21h18" {...stroke(strokeWidth)} />
    <rect x="5" y="12" width="3.5" height="6" rx="1" {...stroke(strokeWidth)} />
    <rect x="10.2" y="8" width="3.5" height="10" rx="1" {...stroke(strokeWidth)} />
    <rect x="15.4" y="4" width="3.5" height="14" rx="1" {...stroke(strokeWidth)} />
  </svg>
);

export const IconFlask: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M10 3v6.2L4.6 18a1.8 1.8 0 0 0 1.5 2.8h11.8a1.8 1.8 0 0 0 1.5-2.8L14 9.2V3" {...stroke(strokeWidth)} />
    <path d="M8.6 3h6.8M7.6 14.5h8.8" {...stroke(strokeWidth)} />
  </svg>
);

export const IconDocs: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" {...stroke(strokeWidth)} />
    <path d="M14 3v5h5M8.5 13h7M8.5 16.5h4.5" {...stroke(strokeWidth)} />
  </svg>
);

export const IconRoute: React.FC<IconProps> = ({ size = 18, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <circle cx="6" cy="5.5" r="2.2" {...stroke(strokeWidth)} />
    <circle cx="6" cy="18.5" r="2.2" {...stroke(strokeWidth)} />
    <path d="M6 7.7v8.6M10 5.5h5a3 3 0 0 1 0 6H11a3 3 0 0 0 0 6h6" {...stroke(strokeWidth)} />
  </svg>
);

export const IconChevron: React.FC<IconProps & { direction?: 'up' | 'down' | 'left' | 'right' }> = ({
  size = 16,
  className,
  strokeWidth = 2,
  direction = 'down',
}) => {
  const rotation = { down: 0, left: 90, up: 180, right: 270 }[direction];
  return (
    <svg {...base(size, className)} style={{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.2s' }}>
      <path d="m6 9 6 6 6-6" {...stroke(strokeWidth)} />
    </svg>
  );
};

export const IconSend: React.FC<IconProps> = ({ size = 16, className, strokeWidth = 1.8 }) => (
  <svg {...base(size, className)}>
    <path d="M4.5 12h6M20 12 4.4 19.2a.5.5 0 0 1-.7-.6L5.6 12 3.7 5.4a.5.5 0 0 1 .7-.6Z" {...stroke(strokeWidth)} />
  </svg>
);

export const IconSearch: React.FC<IconProps> = ({ size = 16, className, strokeWidth = 1.8 }) => (
  <svg {...base(size, className)}>
    <circle cx="11" cy="11" r="6.5" {...stroke(strokeWidth)} />
    <path d="m16 16 4 4" {...stroke(strokeWidth)} />
  </svg>
);

export const IconTrash: React.FC<IconProps> = ({ size = 15, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M4 7h16M9.5 7V5.5a1.5 1.5 0 0 1 1.5-1.5h2a1.5 1.5 0 0 1 1.5 1.5V7" {...stroke(strokeWidth)} />
    <path d="M6.5 7v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2V7M10.5 11v6M13.5 11v6" {...stroke(strokeWidth)} />
  </svg>
);

export const IconCheck: React.FC<IconProps> = ({ size = 15, className, strokeWidth = 2.2 }) => (
  <svg {...base(size, className)}>
    <path d="m5 12.5 4.5 4.5L19 7" {...stroke(strokeWidth)} />
  </svg>
);

export const IconClose: React.FC<IconProps> = ({ size = 15, className, strokeWidth = 2 }) => (
  <svg {...base(size, className)}>
    <path d="m6 6 12 12M18 6 6 18" {...stroke(strokeWidth)} />
  </svg>
);

export const IconRefresh: React.FC<IconProps> = ({ size = 15, className, strokeWidth = 1.8 }) => (
  <svg {...base(size, className)}>
    <path d="M20 11a8 8 0 1 0-2.3 6.3" {...stroke(strokeWidth)} />
    <path d="M20 4.5V11h-6.5" {...stroke(strokeWidth)} />
  </svg>
);

export const IconMenu: React.FC<IconProps> = ({ size = 20, className, strokeWidth = 1.9 }) => (
  <svg {...base(size, className)}>
    <path d="M4 7h16M4 12h16M4 17h16" {...stroke(strokeWidth)} />
  </svg>
);

export const IconShield: React.FC<IconProps> = ({ size = 16, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <path d="M12 3 5 6v5.5c0 4.3 2.9 8.2 7 9.5 4.1-1.3 7-5.2 7-9.5V6Z" {...stroke(strokeWidth)} />
    <path d="m9 12 2 2 4-4" {...stroke(strokeWidth)} />
  </svg>
);

export const IconClock: React.FC<IconProps> = ({ size = 15, className, strokeWidth = 1.7 }) => (
  <svg {...base(size, className)}>
    <circle cx="12" cy="12" r="8.5" {...stroke(strokeWidth)} />
    <path d="M12 7.5V12l3 2" {...stroke(strokeWidth)} />
  </svg>
);

export const IconSpark: React.FC<IconProps> = ({ size = 16, className, strokeWidth = 1.6 }) => (
  <svg {...base(size, className)}>
    <path d="m12 3 1.9 5.4L19 10.3l-5.1 1.9L12 17.6l-1.9-5.4L5 10.3l5.1-1.9Z" {...stroke(strokeWidth)} />
    <path d="M18.5 16.5 19 18l1.5.5-1.5.5-.5 1.5-.5-1.5L16.5 18l1.5-.5Z" {...stroke(strokeWidth)} />
  </svg>
);
