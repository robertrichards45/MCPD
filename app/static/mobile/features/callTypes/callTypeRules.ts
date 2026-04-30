export type CallTypeRule = {
  slug: string;
  title: string;
  shortLabel: string;
  description: string;
  statutes: string[];
  recommendedForms: string[];
  optionalForms: string[];
  checklistItems: string[];
};

export const callTypeRules: Record<string, CallTypeRule> = {
  'domestic-disturbance': {
    slug: 'domestic-disturbance',
    title: 'Domestic Disturbance',
    shortLabel: 'Domestic',
    description: 'Primary domestic response, scene control, initial statements, and follow-up paperwork prep.',
    statutes: ['Assault / battery review', 'Protective-order review'],
    recommendedForms: [
      'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
      'OPNAV 5580 2 Voluntary Statement',
      'NAVMC 11130 Statement of Force Use of Detention',
      'OPNAV 5580 22Evidence Custody Document',
    ],
    optionalForms: ['DD Form 2701 VWAP', 'ENCLOSURE CHECKLIST FILLABLE'],
    checklistItems: [
      'Separate involved parties',
      'Document injuries and scene condition',
      'Confirm witness and victim statements',
      'Notify supervisor if escalation or arrest is involved',
    ],
  },
  'traffic-accident': {
    slug: 'traffic-accident',
    title: 'Traffic Accident',
    shortLabel: 'Traffic',
    description: 'Collision response, roadway safety, vehicle data capture, and tow/impound preparation.',
    statutes: ['Traffic enforcement review', 'Installation roadway policy'],
    recommendedForms: [
      'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
      'OPNAV 5580 2 Voluntary Statement Traffic',
      'TA FIELD SKETCH NEW',
    ],
    optionalForms: ['DD Form 2506Vehicle Impoundment Report', 'OPNAV 5580 12 DON VEHICLE REPORT'],
    checklistItems: [
      'Stabilize traffic and scene hazards',
      'Capture driver and vehicle data',
      'Document injuries and medical response',
      'Identify tow or impound decision',
    ],
  },
  'suspicious-person': {
    slug: 'suspicious-person',
    title: 'Suspicious Person',
    shortLabel: 'Suspicious',
    description: 'Field contact and articulable-facts workflow for suspicious behavior and security concerns.',
    statutes: ['Detention authority review', 'Trespass / access review'],
    recommendedForms: ['OPNAV 5580 21Field Interview Card', 'OPNAV 5580 2 Voluntary Statement'],
    optionalForms: ['OPNAV 5580 22Evidence Custody Document'],
    checklistItems: [
      'Record the reason for contact',
      'Capture identifiers and witness information',
      'Document disposition and release / detention outcome',
    ],
  },
  'trespass-after-warning': {
    slug: 'trespass-after-warning',
    title: 'Trespass After Warning',
    shortLabel: 'Trespass',
    description: 'Return-after-warning workflow with authority review and citation/notice support.',
    statutes: ['Trespass authority review', 'Installation access policy'],
    recommendedForms: ['OPNAV 5580 2 Voluntary Statement', 'UNSECURED BUILDING NOTICE'],
    optionalForms: ['OPNAV 5580 21Field Interview Card'],
    checklistItems: [
      'Confirm prior warning details',
      'Record location restrictions',
      'Document witness confirmation',
      'Capture final enforcement action',
    ],
  },
  'theft': {
    slug: 'theft',
    title: 'Theft',
    shortLabel: 'Theft',
    description: 'Property crime workflow focused on ownership, recovered items, and evidence trail.',
    statutes: ['Property crime review', 'Evidence handling review'],
    recommendedForms: ['OPNAV 5580 22Evidence Custody Document', 'OPNAV 5580 2 Voluntary Statement'],
    optionalForms: ['OPNAV 5580 21Field Interview Card', 'DD Form 2701 VWAP'],
    checklistItems: [
      'Verify owner and value information',
      'Document recovered property',
      'Preserve evidence chain',
      'Capture suspect opportunity and access',
    ],
  },
};

export function getCallTypeRule(slug: string): CallTypeRule | null {
  return callTypeRules[slug] || null;
}

export function listCallTypeRules(): CallTypeRule[] {
  return Object.values(callTypeRules);
}
