from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from difflib import SequenceMatcher
from functools import lru_cache
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class LegalEntry:
    record_id: str = ''
    jurisdiction_type: str = ''
    source: str = ''
    code: str = ''
    title: str = ''
    summary: str = ''
    elements: tuple[str, ...] = ()
    source_group: str = ''
    short_title: str = ''
    plain_language_summary: str = ''
    required_elements: tuple[str, ...] = ()
    scenario_triggers: tuple[str, ...] = ()
    penalties: str = ''
    related_statutes: tuple[str, ...] = ()
    related_orders: tuple[str, ...] = ()
    enforcement_notes: str = ''
    notes: str = ''
    keywords: tuple[str, ...] = ()
    related_codes: tuple[str, ...] = ()
    minimum_punishment: str = ''
    maximum_punishment: str = ''
    offense_id: str = ''
    source_type: str = ''
    source_label: str = ''
    citation: str = ''
    title_number: str = ''
    section_number: str = ''
    chapter_number: str = ''
    article_number: str = ''
    category: str = ''
    subcategory: str = ''
    severity: str = ''
    aliases: tuple[str, ...] = ()
    synonyms: tuple[str, ...] = ()
    narrative_triggers: tuple[str, ...] = ()
    conduct_verbs: tuple[str, ...] = ()
    victim_context: tuple[str, ...] = ()
    property_context: tuple[str, ...] = ()
    injury_context: tuple[str, ...] = ()
    relationship_context: tuple[str, ...] = ()
    location_context: tuple[str, ...] = ()
    federal_context: tuple[str, ...] = ()
    military_context: tuple[str, ...] = ()
    traffic_context: tuple[str, ...] = ()
    juvenile_context: tuple[str, ...] = ()
    drug_context: tuple[str, ...] = ()
    lesser_included_offenses: tuple[str, ...] = ()
    alternative_offenses: tuple[str, ...] = ()
    overlap_notes: tuple[str, ...] = ()
    officer_notes: str = ''
    jurisdiction_conditions: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    active_flag: bool = True
    source_version: str = ''
    source_reference_url: str = ''
    source_reference: str = ''
    source_file_name: str = ''
    source_document_path: str = ''
    source_page_reference: str = ''
    official_text: str = ''
    official_citation: str = ''
    official_punishment_text: str = ''
    official_text_available: bool = False
    derived_summary: str = ''
    derived_aliases: tuple[str, ...] = ()
    derived_synonyms: tuple[str, ...] = ()
    derived_examples: tuple[str, ...] = ()
    derived_triggers: tuple[str, ...] = ()
    citation_requires_verification: bool = False
    parser_confidence: float = 0.0
    enrichment_confidence: float = 0.0
    last_updated: str = ''
    enrichment_derived: bool = False


@dataclass(frozen=True)
class LegalMatch:
    entry: LegalEntry
    score: int
    reasons: tuple[str, ...] = ()
    confidence: int = 0
    matched_terms: tuple[str, ...] = ()
    warning: str = ''
    certainty_bucket: str = 'possible'


@dataclass(frozen=True)
class QueryAnalysis:
    original_query: str
    corrected_query: str
    normalized_query: str
    source: str
    tokens: tuple[str, ...]
    phrases: tuple[str, ...]
    expanded_terms: tuple[str, ...]
    expanded_phrases: tuple[str, ...]
    concept_tags: tuple[str, ...]
    source_hints: tuple[str, ...]
    context_terms: tuple[str, ...]
    conduct_terms: tuple[str, ...]
    clauses: tuple[str, ...]
    intents: tuple[str, ...]
    article_number: str = ''
    ocga_code: str = ''
    ocga_prefix: str = ''
    stage: str = 'primary'


@dataclass(frozen=True)
class SearchEntryProfile:
    entry: LegalEntry
    field_texts: dict[str, str]
    field_tokens: dict[str, frozenset[str]]
    all_tokens: frozenset[str]
    phrase_inventory: frozenset[str]
    concept_tags: frozenset[str]
    source_hints: frozenset[str]
    source_quality: float
    intent_tags: frozenset[str]


GEORGIA_CODES = (
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-181',
        title='Speed Restrictions',
        summary='Basic speeding statute covering driving above the posted maximum lawful speed.',
        elements=(
            'The driver operated a motor vehicle.',
            'The vehicle was driven on a roadway governed by Georgia traffic law.',
            'The driver exceeded the applicable lawful speed limit.',
        ),
        notes='Traffic offense; exact penalty varies by speed and zone.',
        keywords=('speeding', '65 in a 25', 'fast', 'over limit'),
        related_codes=('OCGA 40-6-184',),
        minimum_punishment='Fine amount depends on the speed range and court disposition.',
        maximum_punishment='Higher fines, points, and enhanced penalties may apply in special zones or extreme speeds.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-390',
        title='Reckless Driving',
        summary='Driving with reckless disregard for the safety of persons or property.',
        elements=(
            'The driver operated a motor vehicle.',
            'The conduct showed reckless disregard.',
            'The reckless disregard affected persons or property.',
        ),
        notes='Misdemeanor traffic offense.',
        keywords=('reckless', 'reckless driving', 'unsafe driving'),
        related_codes=('OCGA 40-6-397',),
        minimum_punishment='Misdemeanor sentencing exposure with court-imposed fine or jail possible.',
        maximum_punishment='Up to 12 months confinement and/or misdemeanor fine range, subject to court disposition.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-49',
        title='Following Too Closely',
        summary='A driver must not follow another vehicle more closely than is reasonable and prudent.',
        elements=(
            'The driver was following another vehicle.',
            'Traffic, speed, and roadway conditions required a greater following distance.',
            'The driver failed to maintain a reasonable and prudent distance.',
        ),
        notes='Common citation in crash and aggressive driving stops.',
        keywords=('following too close', 'tailgating', 'tailgater'),
        related_codes=('OCGA 40-6-49.1',),
        minimum_punishment='Traffic citation with court-assessed fine possible.',
        maximum_punishment='Traffic misdemeanor exposure depends on local court disposition and any related crash factors.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-391',
        title='Driving Under the Influence',
        summary='Prohibits driving or being in actual physical control while under the influence of alcohol, drugs, or intoxicants.',
        elements=(
            'The person drove or was in actual physical control of a moving vehicle.',
            'The person was under the influence of alcohol, drugs, toxic vapor, or a combination.',
            'The influence rendered the person less safe to drive, or a per se prohibited concentration existed.',
        ),
        notes='Charging path depends on less-safe, per se, drugs, or refusal facts.',
        keywords=('dui', 'dui refusal', 'drunk driving', 'impaired'),
        related_codes=('OCGA 40-5-67.1', 'OCGA 40-6-392'),
        minimum_punishment='Mandatory minimum penalties depend on first or repeat offense and charging path.',
        maximum_punishment='Maximum punishment increases sharply with repeat offenses, injury, child endangerment, or aggravators.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-221',
        title='Unauthorized Use of Disabled Parking',
        summary='Prohibits parking in designated disabled parking without the required placard, plate, or authorization.',
        elements=(
            'A vehicle was parked in a designated disabled parking space.',
            'The vehicle did not display required disabled parking authorization.',
            'No lawful exception applied.',
        ),
        notes='Useful for handicap parking violations.',
        keywords=('handicap parking', 'parking in handicap without sticker', 'disabled parking'),
        related_codes=('OCGA 40-6-226',),
        minimum_punishment='Citation-level monetary penalty may apply.',
        maximum_punishment='Maximum fine depends on the exact subsection and local court disposition.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-2-8',
        title='Display of License Plate',
        summary='Requires proper display of a valid registration plate on the vehicle.',
        elements=(
            'The vehicle was required to display a Georgia plate or valid registration plate.',
            'The plate was not properly displayed, missing, or otherwise noncompliant.',
        ),
        notes='Often used with registration and tag stops.',
        keywords=('expired registration', 'no plate', 'plate display', 'tag'),
        related_codes=('OCGA 40-2-41',),
        minimum_punishment='Traffic citation with monetary fine possible.',
        maximum_punishment='Maximum penalty depends on the exact registration/plate violation and court disposition.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-20',
        title='Obedience to Traffic-Control Devices',
        summary='Requires drivers to obey official traffic-control devices unless otherwise directed by law enforcement.',
        elements=(
            'The driver operated a motor vehicle.',
            'An official traffic-control device was present and applicable.',
            'The driver failed to obey the device.',
        ),
        notes='Common for stop sign, signal, and sign-control violations.',
        keywords=('stop sign', 'ran a red light', 'traffic control device', 'ignored sign', 'red light'),
        related_codes=('OCGA 40-6-21', 'OCGA 40-6-72'),
        minimum_punishment='Traffic citation with monetary fine possible.',
        maximum_punishment='Maximum fine and points depend on the exact traffic-control violation and court disposition.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-48',
        title='Failure to Maintain Lane',
        summary='Requires a vehicle to be driven as nearly as practical entirely within a single lane.',
        elements=(
            'The driver operated a motor vehicle on a roadway divided into lanes.',
            'The driver failed to remain within a single lane as nearly as practical.',
            'No lawful reason or safe exception justified the movement.',
        ),
        notes='Commonly paired with impaired or distracted driving facts.',
        keywords=('failure to maintain lane', 'weaving', 'drifting', 'crossed lane', 'swerving'),
        related_codes=('OCGA 40-6-390', 'OCGA 40-6-391'),
        minimum_punishment='Traffic citation with monetary fine possible.',
        maximum_punishment='Maximum fine depends on the court and whether related charges are also filed.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-123',
        title='Turning Movements and Required Signals',
        summary='Requires proper signaling before turning, changing lanes, or moving right or left on a roadway.',
        elements=(
            'The driver turned, changed lanes, or moved laterally on a roadway.',
            'The movement required a signal under the circumstances.',
            'The driver failed to give the required signal properly or in time.',
        ),
        notes='Useful for signaling and lane-change stops.',
        keywords=('no turn signal', 'failed to signal', 'lane change no signal', 'turn signal'),
        related_codes=('OCGA 40-6-48',),
        minimum_punishment='Traffic citation with monetary fine possible.',
        maximum_punishment='Maximum fine depends on local court disposition.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-5-121',
        title='Driving While License Suspended or Revoked',
        summary='Prohibits operating a motor vehicle while the driver’s privilege is suspended, revoked, or canceled.',
        elements=(
            'The accused operated a motor vehicle.',
            'The accused’s driver license or driving privilege was suspended, revoked, or canceled.',
            'The accused had notice or legally sufficient knowledge of the suspension, revocation, or cancellation.',
        ),
        notes='Often triggered after status check during traffic stop.',
        keywords=('suspended license', 'revoked license', 'no valid license', 'license suspended'),
        related_codes=('OCGA 40-5-20',),
        minimum_punishment='Statutory minimum penalties depend on the driver’s history and disposition.',
        maximum_punishment='Repeat violations increase confinement and fine exposure under the statute.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-5-20',
        title='Driving Without a Valid License',
        summary='Prohibits operating a motor vehicle without being duly licensed as required by Georgia law.',
        elements=(
            'The accused operated a motor vehicle.',
            'The accused did not possess a valid driver license or qualifying authority to drive.',
            'No lawful exception applied.',
        ),
        notes='Separate from suspended/revoked license situations.',
        keywords=('no license', 'unlicensed driver', 'never licensed'),
        related_codes=('OCGA 40-5-121',),
        minimum_punishment='Traffic or misdemeanor handling depends on the exact licensing defect and court disposition.',
        maximum_punishment='Maximum punishment depends on subsection and prior history.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 40-6-271',
        title='Duty Upon Striking an Unattended Vehicle or Property',
        summary='Requires a driver to stop and provide notice after striking unattended vehicles or property.',
        elements=(
            'The accused struck an unattended vehicle or other property.',
            'The accused knew or reasonably should have known of the collision.',
            'The accused failed to stop and provide required identifying information or notice.',
        ),
        notes='Common hit-and-run style property damage charge.',
        keywords=('hit and run', 'left the scene', 'struck parked car', 'property damage and left'),
        related_codes=('OCGA 40-6-270',),
        minimum_punishment='Penalty depends on property damage facts and charging path.',
        maximum_punishment='Maximum punishment increases when related collision or damage offenses are also charged.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-23',
        title='Simple Battery',
        summary='Occurs when a person intentionally makes physical contact of an insulting or provoking nature, or intentionally causes physical harm.',
        elements=(
            'The accused intentionally made physical contact of an insulting or provoking nature, or intentionally caused physical harm.',
            'The contact or harm was unlawful.',
            'The act was committed against another person.',
        ),
        notes='Useful for lower-level unlawful touching cases.',
        keywords=('simple battery', 'grabbed', 'pushed', 'slapped', 'unwanted contact'),
        related_codes=('OCGA 16-5-20', 'OCGA 16-5-23.1'),
        minimum_punishment='Misdemeanor-level punishment typically applies absent aggravating factors.',
        maximum_punishment='Aggravating victim categories can elevate punishment beyond the base misdemeanor range.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-20',
        title='Simple Assault',
        summary='Covers attempts to commit a violent injury or acts placing another in reasonable apprehension of immediately receiving a violent injury.',
        elements=(
            'The accused attempted to commit a violent injury, or committed an act placing another in reasonable apprehension of immediately receiving a violent injury.',
            'The act was unlawful.',
            'The act was directed at another person.',
        ),
        notes='Often charged when there is no actual physical contact.',
        keywords=('simple assault', 'threatened to hit', 'swung at', 'fight but no contact'),
        related_codes=('OCGA 16-5-23', 'OCGA 16-5-21'),
        minimum_punishment='Misdemeanor-level punishment generally applies absent aggravating victim or weapon factors.',
        maximum_punishment='Certain victim classes or aggravating facts can elevate the offense and punishment.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-11-39',
        title='Disorderly Conduct',
        summary='Prohibits violent, tumultuous, obscene, or disruptive conduct under the statutory subsections.',
        elements=(
            'The accused engaged in conduct prohibited by a subsection of the statute.',
            'The conduct occurred under circumstances covered by the statute.',
            'The conduct was intentional or otherwise culpable as required by the subsection.',
        ),
        notes='Use the exact subsection facts when charging.',
        keywords=('disorderly conduct', 'causing a disturbance', 'tumultuous', 'fighting words'),
        related_codes=('OCGA 16-10-24',),
        minimum_punishment='Misdemeanor handling generally applies for standard disorderly conduct charges.',
        maximum_punishment='Maximum punishment depends on the exact subsection and any related charges.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-10-24',
        title='Obstruction of Law Enforcement Officers',
        summary='Prohibits knowingly and willfully obstructing or hindering law enforcement officers in the lawful discharge of official duties.',
        elements=(
            'The victim was a law enforcement officer acting in the lawful discharge of official duties.',
            'The accused knew or reasonably should have known that fact.',
            'The accused knowingly and willfully obstructed or hindered the officer.',
        ),
        notes='Felony variant applies when violence is used.',
        keywords=('obstruction', 'resisting', 'would not comply', 'pulled away', 'interfered with officer'),
        related_codes=('OCGA 16-11-39',),
        minimum_punishment='Nonviolent obstruction is usually charged as a misdemeanor.',
        maximum_punishment='Violent obstruction can be charged as a felony with significantly greater punishment.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-6-1',
        title='Rape',
        summary='Punishes carnal knowledge of a female forcibly and against her will, or where the female is under the statutory age.',
        elements=(
            'The accused had carnal knowledge of the victim as defined by statute.',
            'The act was committed forcibly and against the victim’s will, or under the statutory-age provision.',
            'The conduct was unlawful under OCGA 16-6-1.',
        ),
        notes='Use exact statutory language and current Georgia pattern charges for the charged theory.',
        keywords=('rape', 'forcible rape', 'sexual assault', 'nonconsensual sex'),
        related_codes=('OCGA 16-6-22', 'OCGA 16-6-5.1'),
        minimum_punishment='Punishment is set by statute and can include substantial mandatory imprisonment.',
        maximum_punishment='Maximum punishment can include life imprisonment under charged circumstances.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-6-22',
        title='Aggravated Sexual Battery',
        summary='Intentional penetration with a foreign object of another person’s sexual organ or anus without consent.',
        elements=(
            'The accused intentionally penetrated with a foreign object the sexual organ or anus of another person.',
            'The penetration was without that person’s consent.',
            'The conduct was unlawful under OCGA 16-6-22.',
        ),
        notes='Distinct from rape elements; charge depends on fact pattern and statutory definitions.',
        keywords=('aggravated sexual battery', 'sexual battery', 'nonconsensual penetration'),
        related_codes=('OCGA 16-6-1', 'OCGA 16-6-5.1'),
        minimum_punishment='Punishment is controlled by statute and carries severe felony exposure.',
        maximum_punishment='Maximum punishment can include life imprisonment under charged circumstances.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-23.1',
        title='Battery (Family Violence Context Supported)',
        summary='Battery occurs when a person intentionally causes substantial physical harm or visible bodily harm. Family violence context may apply based on relationship and charging language.',
        elements=(
            'The accused intentionally caused substantial physical harm or visible bodily harm to another.',
            'The harm was unlawful under Georgia battery law.',
            'For family violence treatment, the relationship facts must fit Georgia family violence definitions.',
        ),
        notes='Use with relationship-specific facts for family violence charging decisions.',
        keywords=('battery', 'family violence battery', 'domestic battery', 'visible injury', 'bruising'),
        related_codes=('OCGA 16-5-23', 'OCGA 19-13-1'),
        minimum_punishment='Punishment depends on charge level and any domestic/family violence treatment by statute and court.',
        maximum_punishment='Enhanced punishment can apply for repeat or aggravated family violence battery circumstances.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-7-21',
        title='Criminal Trespass',
        summary='Covers entry onto or remaining upon property without authority after notice, and certain property damage/interference conduct.',
        elements=(
            'The accused entered, remained on, or interfered with property without authority under a criminal trespass subsection.',
            'The accused had notice, intent, or other required statutory condition for the charged subsection.',
            'The conduct was unlawful under OCGA 16-7-21.',
        ),
        notes='Common for told-to-leave scenarios and unauthorized entry without full burglary elements.',
        keywords=('criminal trespass', 'trespass', 'told to leave', 'entered without permission', 'no trespass notice'),
        related_codes=('OCGA 16-7-22',),
        minimum_punishment='Typically misdemeanor-level punishment absent separate aggravating offenses.',
        maximum_punishment='Maximum punishment depends on subsection and accompanying charges.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-90',
        title='Stalking',
        summary='Prohibits following, placing under surveillance, or contacting another person without consent for the purpose of harassing and intimidating.',
        elements=(
            'The accused followed, surveilled, or contacted another person without consent.',
            'The conduct was done for the purpose of harassing and intimidating the victim.',
            'A reasonable person would suffer emotional distress, fear for safety, or fear for immediate family safety from the conduct.',
        ),
        notes='Common in domestic disputes involving repeated calls, texts, social-media contact, or following behavior.',
        keywords=('stalking', 'harassing messages', 'repeated unwanted contact', 'following ex', 'domestic stalking'),
        related_codes=('OCGA 16-5-91', 'OCGA 16-5-95'),
        minimum_punishment='Punishment depends on charging path and prior stalking history.',
        maximum_punishment='Aggravating facts and repeat history increase punishment exposure under the statute.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-91',
        title='Aggravated Stalking',
        summary='Covers stalking conduct in violation of protective conditions such as bond, probation/parole restrictions, or protective orders.',
        elements=(
            'The accused committed conduct that constitutes stalking.',
            'The conduct occurred in violation of a bond condition, probation/parole condition, temporary/permanent protective order, restraining order, or injunction.',
            'The accused knew or should have known of the prohibiting condition/order.',
        ),
        notes='Critical domestic-violence escalation charge when stalking continues after court protection is in place.',
        keywords=('aggravated stalking', 'violated protective order by contact', 'kept calling after tpo', 'domestic protective order stalking'),
        related_codes=('OCGA 16-5-90', 'OCGA 16-5-95'),
        minimum_punishment='Felony punishment applies under statutory aggravated stalking provisions.',
        maximum_punishment='Maximum punishment is governed by the aggravated stalking statute and prior record factors.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-95',
        title='Violation of Family Violence Order',
        summary='Prohibits violating valid family-violence protective orders, including no-contact, stay-away, or other protective conditions.',
        elements=(
            'A valid family violence protective order existed and was in effect.',
            'The accused had notice of the order.',
            'The accused knowingly violated a term of the order.',
        ),
        notes='Use for direct no-contact/stay-away violations in domestic cases.',
        keywords=('protective order violation', 'violated tpo', 'restraining order violation', 'family violence order violation', 'contacted protected person'),
        related_codes=('OCGA 16-5-90', 'OCGA 16-5-91'),
        minimum_punishment='Penalty depends on the specific order violation and prosecutive path.',
        maximum_punishment='Repeat violations and related conduct can increase punishment exposure.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-41',
        title='False Imprisonment',
        summary='Prohibits arresting, confining, or detaining another person without legal authority.',
        elements=(
            'The accused arrested, confined, or detained another person.',
            'The confinement or detention was against the person’s will.',
            'The accused lacked legal authority for the detention.',
        ),
        notes='Important for domestic scenarios such as blocking exits, taking keys/phone, or refusing to let victim leave.',
        keywords=('false imprisonment', 'would not let her leave', 'blocked door', 'held against will', 'locked in room'),
        related_codes=('OCGA 16-5-40', 'OCGA 16-5-45'),
        minimum_punishment='Felony punishment applies under statutory false-imprisonment provisions.',
        maximum_punishment='Maximum punishment is set by statute and can be enhanced with related offenses.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-40',
        title='Kidnapping',
        summary='Prohibits abducting or stealing away a person without lawful authority or warrant and holding that person against their will.',
        elements=(
            'The accused abducted or stole away another person.',
            'The act was done without lawful authority or warrant.',
            'The victim was held against their will.',
        ),
        notes='Consider alongside false imprisonment when movement/asportation facts are present.',
        keywords=('kidnapping', 'forced into car', 'abducted', 'took victim and would not release'),
        related_codes=('OCGA 16-5-41',),
        minimum_punishment='Felony punishment with significant statutory exposure.',
        maximum_punishment='Maximum punishment depends on aggravating facts and charged subsections.',
    ),
    LegalEntry(
        source='GEORGIA',
        code='OCGA 16-5-70',
        title='Cruelty to Children',
        summary='Covers willfully causing physical/mental pain to a child, criminal negligence causing cruel/excessive pain, and family-violence incidents in the presence of a child.',
        elements=(
            'The victim was a child as defined by statute.',
            'The accused committed conduct prohibited by the charged cruelty-to-children degree/subsection.',
            'The required intent, negligence, or family-violence-in-presence-of-child condition was met for the charged count.',
        ),
        notes='High-value domestic-call statute when children witness family violence or are directly harmed.',
        keywords=('cruelty to children', 'child witnessed domestic violence', 'injured child', 'child endangerment domestic'),
        related_codes=('OCGA 16-5-23.1', 'OCGA 16-5-20'),
        minimum_punishment='Punishment depends on charged degree and factual circumstances.',
        maximum_punishment='Higher-degree cruelty-to-children charges carry severe felony punishment exposure.',
    ),
)


UCMJ_ARTICLES = (
    LegalEntry(
        source='UCMJ',
        code='Article 86',
        title='Absence Without Leave',
        summary='Covers failure to go, going from, or absenting oneself from the appointed place of duty.',
        elements=(
            'A certain authority appointed a certain time and place of duty.',
            'The accused knew of that time and place.',
            'The accused failed to go, went from, or remained absent without authority.',
        ),
        notes='Different specifications apply depending on the exact AWOL conduct.',
        keywords=('awol', 'absence', 'failure to go'),
        related_codes=('Article 87',),
        minimum_punishment='Punishment varies by specification, duration, and whether the accused surrendered or was apprehended.',
        maximum_punishment='Maximum punishment increases significantly for longer unauthorized absence or terminated by apprehension.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 89',
        title='Disrespect Toward a Superior Commissioned Officer',
        summary='Punishes disrespectful language or behavior toward a superior commissioned officer.',
        elements=(
            'The accused did or omitted certain acts or used certain language.',
            'The conduct or language was directed toward a superior commissioned officer.',
            'The officer was then the superior commissioned officer of the accused.',
            'The accused knew the person was that superior commissioned officer.',
            'Under the circumstances, the behavior or language was disrespectful.',
        ),
        notes='Requires personal knowledge and actual disrespect.',
        keywords=('disrespect', 'superior officer', 'insubordination'),
        related_codes=('Article 90', 'Article 91'),
        minimum_punishment='Minor misconduct may result in lower-level punishment depending on forum and facts.',
        maximum_punishment='Maximum punishment depends on the forum and charged specification under the Manual for Courts-Martial.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 91',
        title='Insubordinate Conduct Toward Warrant Officer, NCO, or Petty Officer',
        summary='Addresses assault, disobedience, or disrespect toward specified military leaders.',
        elements=(
            'The victim had qualifying military status (warrant officer, NCO, or petty officer).',
            'The accused knew that status.',
            'The accused committed the charged form of insubordinate conduct.',
            'The conduct occurred while the victim was in execution of office, when required by the specification.',
        ),
        notes='Specification varies by assault, willful disobedience, or disrespect.',
        keywords=('nco disrespect', 'insubordinate', 'petty officer'),
        related_codes=('Article 89', 'Article 92'),
        minimum_punishment='Minimum exposure depends on whether the conduct was disrespect, disobedience, or assault.',
        maximum_punishment='Maximum punishment varies by specification and severity under the Manual for Courts-Martial.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 92',
        title='Failure to Obey Order or Regulation',
        summary='Punishes violation of lawful general orders, other lawful orders, or dereliction of duty.',
        elements=(
            'There was a lawful general order, regulation, or other lawful order, or a duty existed.',
            'The accused had a duty to obey or perform the duty.',
            'The accused knew or reasonably should have known of the order or duty when required by the specification.',
            'The accused violated or failed to obey the order, or was derelict in the duty.',
        ),
        notes='Most common charging article for order and duty violations.',
        keywords=('failure to obey', 'general order', 'dereliction'),
        related_codes=('Article 90', 'Article 91'),
        minimum_punishment='Punishment depends on whether the charge is order violation or dereliction.',
        maximum_punishment='Maximum punishment varies significantly based on the exact specification and whether the order was general.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 128',
        title='Assault',
        summary='Covers attempts or offers to do bodily harm, and consummated batteries.',
        elements=(
            'The accused attempted, offered, or did bodily harm to a certain person.',
            'The attempt, offer, or bodily harm was done unlawfully.',
            'For battery, the bodily harm was done with unlawful force or violence.',
        ),
        notes='Aggravated variants require additional serious bodily injury or dangerous weapon facts.',
        keywords=('assault', 'battery', 'fight'),
        related_codes=('Article 128b',),
        minimum_punishment='Simple assault and battery specifications carry lower punishment ranges than aggravated variants.',
        maximum_punishment='Maximum punishment increases with dangerous weapons, serious bodily injury, or aggravated facts.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 128b',
        title='Domestic Violence',
        summary='Punishes domestic violence offenses under the UCMJ, including violent conduct against a spouse, intimate partner, dating partner, or immediate family member under charged specifications.',
        elements=(
            'The accused committed one of the charged domestic-violence acts under the article.',
            'The victim had qualifying domestic relationship status (for example spouse/intimate partner/dating partner/family member) for the charged specification.',
            'The conduct was unlawful and met the elements of the charged domestic-violence subsection.',
        ),
        notes='Use current MCM specification language for exact domestic-violence theory and relationship definitions.',
        keywords=('domestic violence military', 'article 128b', 'service member assaulted spouse', 'military domestic assault', 'intimate partner violence'),
        related_codes=('Article 128', 'Article 130', 'Article 120'),
        minimum_punishment='Punishment depends on the charged domestic-violence specification and forum.',
        maximum_punishment='Maximum punishment varies by specification and aggravating factors under the MCM.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 130',
        title='Stalking',
        summary='Punishes stalking conduct under UCMJ specifications, including repeated threatening, harassing, or fear-inducing conduct toward a victim.',
        elements=(
            'The accused engaged in a course of conduct directed at a specific person.',
            'The conduct caused or would reasonably cause fear, emotional distress, or other charged stalking harm under the specification.',
            'The accused acted wrongfully and the conduct met the charged UCMJ stalking requirements.',
        ),
        notes='Use with repeated domestic/intimate harassment patterns and threat-based follow-up behavior.',
        keywords=('article 130 stalking', 'military stalking', 'repeated threatening contact', 'domestic stalking military'),
        related_codes=('Article 128b', 'Article 117', 'Article 134'),
        minimum_punishment='Punishment depends on charged stalking specification and forum.',
        maximum_punishment='Maximum punishment is governed by the charged article specification under the MCM.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 87',
        title='Missing Movement',
        summary='Punishes missing the movement of a ship, aircraft, or unit through neglect or design.',
        elements=(
            'The accused was required in the course of duty to move with a ship, aircraft, or unit.',
            'The accused knew of the prospective movement.',
            'The accused missed the movement through neglect or design.',
        ),
        notes='Design-based specifications carry more severe exposure.',
        keywords=('missed movement', 'missed deployment', 'missed transport'),
        related_codes=('Article 86',),
        minimum_punishment='Neglect-based missing movement carries lower punishment exposure than design-based conduct.',
        maximum_punishment='Designed or intentional missing movement carries substantially greater punishment under the MCM.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 90',
        title='Willfully Disobeying a Superior Commissioned Officer',
        summary='Punishes willful disobedience of a lawful command from a superior commissioned officer.',
        elements=(
            'The victim was the superior commissioned officer of the accused.',
            'The accused knew that status.',
            'The superior commissioned officer gave a lawful command.',
            'The accused willfully disobeyed the command.',
        ),
        notes='Requires an actual lawful command and willful disobedience.',
        keywords=('willfully disobeyed officer', 'refused command', 'disobeyed superior'),
        related_codes=('Article 89', 'Article 92'),
        minimum_punishment='Punishment depends on forum and specific facts, but the article is treated seriously.',
        maximum_punishment='Maximum punishment is significant and depends on the forum and charged specification under the MCM.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 93',
        title='Cruelty and Maltreatment',
        summary='Punishes cruelty, oppression, or maltreatment of a person subject to the accused’s orders.',
        elements=(
            'A certain person was subject to the orders of the accused.',
            'The accused was cruel toward, oppressed, or maltreated that person.',
            'The conduct was wrongful.',
        ),
        notes='Often used in abuse-of-authority or mistreatment cases.',
        keywords=('maltreatment', 'cruelty', 'abused subordinate', 'oppression'),
        related_codes=('Article 92',),
        minimum_punishment='Punishment depends on forum and severity of mistreatment.',
        maximum_punishment='Maximum punishment is substantial and increases with aggravating facts under the MCM.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 107',
        title='False Official Statements or Records',
        summary='Punishes knowingly false official statements or falsified official records.',
        elements=(
            'The accused signed, made, altered, or used an official statement or record.',
            'The statement or record was false in a certain particular.',
            'The accused knew it was false.',
            'The false statement or record was made with the required wrongful intent.',
        ),
        notes='Useful for false reports and official paperwork misconduct.',
        keywords=('false statement', 'lied on report', 'false official statement', 'falsified record'),
        related_codes=('Article 131',),
        minimum_punishment='Punishment varies by forum and the nature of the false official act.',
        maximum_punishment='Maximum punishment can be severe due to the official integrity component of the offense.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 108',
        title='Military Property of the United States',
        summary='Punishes damage, sale, loss, destruction, or wrongful disposition of military property.',
        elements=(
            'The property was military property of the United States.',
            'The accused sold, disposed of, destroyed, damaged, lost, or wrongfully suffered the property to be lost, sold, or damaged.',
            'The conduct was wrongful.',
        ),
        notes='Value and manner of loss or damage affect punishment.',
        keywords=('damaged military property', 'lost gear', 'sold equipment', 'destroyed government property'),
        related_codes=('Article 121',),
        minimum_punishment='Punishment depends heavily on value and the exact wrongful act.',
        maximum_punishment='Higher property value and intentional misconduct substantially increase punishment exposure.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 112',
        title='Drunk on Duty and Incapacitation for Duty',
        summary='Punishes wrongful intoxication or incapacitation for duty through alcohol or drugs under charged specifications.',
        elements=(
            'The accused had certain military duty status as charged.',
            'The accused was drunk or incapacitated for the proper performance of duty.',
            'The condition was wrongful and met the charged specification requirements.',
        ),
        notes='Often charged with duty-related intoxication facts; specification details matter.',
        keywords=('drunk on duty', 'incapacitated for duty', 'high on duty', 'drug impaired duty'),
        related_codes=('Article 112a', 'Article 92'),
        minimum_punishment='Punishment depends on the exact specification, duty status, and forum.',
        maximum_punishment='Maximum punishment depends on specification and circumstances under the Manual for Courts-Martial.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 112a',
        title='Wrongful Use, Possession, Distribution, Importation, Manufacture, or Introduction of Controlled Substances',
        summary='Primary military drug article covering wrongful use, possession, introduction onto installations/vessels/aircraft, distribution, manufacture, and related controlled-substance offenses.',
        elements=(
            'The accused committed the charged act involving a controlled substance (use, possession, distribution, manufacture, importation, exportation, or introduction).',
            'The act was wrongful.',
            'The substance was a controlled substance as defined by law and the Manual for Courts-Martial.',
            'Where required by specification, the accused knew the contraband nature of the substance.',
        ),
        notes='Core UCMJ drug statute; exact elements vary by the charged act and specification.',
        keywords=('article 112a', 'wrongful use', 'wrongful possession', 'distribution of controlled substance', 'drug use military', 'drug possession military', 'introduced drugs on base'),
        related_codes=('Article 80', 'Article 81', 'Article 92', 'Article 112'),
        minimum_punishment='Punishment varies by act and substance; minor use cases can be lower than distribution/trafficking-type conduct.',
        maximum_punishment='Maximum punishment can be severe, especially for distribution, manufacture, importation, or introduction offenses.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 117',
        title='Provoking Speeches or Gestures',
        summary='Punishes provoking or reproachful words or gestures likely to provoke a breach of the peace.',
        elements=(
            'The accused wrongfully used words or gestures toward a certain person.',
            'The words or gestures were provoking or reproachful.',
            'Under the circumstances, the conduct was of a nature to provoke a breach of the peace.',
        ),
        notes='Useful for verbal confrontations likely to escalate.',
        keywords=('provoking words', 'reproachful', 'taunting', 'verbal provocation'),
        related_codes=('Article 89', 'Article 91'),
        minimum_punishment='Punishment depends on the circumstances and forum.',
        maximum_punishment='Maximum punishment is lower than many violent offenses but still depends on forum and facts.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 120',
        title='Sexual Assault and Sexual Misconduct',
        summary='Covers a range of nonconsensual sexual acts and sexual misconduct offenses.',
        elements=(
            'The accused committed the charged sexual act or sexual contact.',
            'The act or contact met the statutory definitions and circumstances of the charged offense.',
            'The required lack of consent, incapacity, force, or other prohibited circumstance existed.',
        ),
        notes='Exact elements depend on the charged specification and subsection.',
        keywords=('rape', 'sexual assault', 'sexual misconduct', 'nonconsensual sexual contact', 'forcible sex'),
        related_codes=('Article 120b', 'Article 128b'),
        minimum_punishment='Punishment depends on the exact specification and forum.',
        maximum_punishment='Maximum punishment can be extremely severe, up to the highest punishments authorized for the charged specification.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 121',
        title='Larceny and Wrongful Appropriation',
        summary='Punishes wrongful taking, obtaining, withholding, or appropriation of property.',
        elements=(
            'The accused wrongfully took, obtained, or withheld certain property from the possession of the owner or another person.',
            'The property belonged to a certain person or entity.',
            'The taking was with the intent required for larceny or wrongful appropriation.',
        ),
        notes='Value and type of property affect punishment.',
        keywords=('larceny', 'stole', 'theft', 'wrongful appropriation'),
        related_codes=('Article 108',),
        minimum_punishment='Wrongful appropriation and lower-value cases carry lower punishment exposure.',
        maximum_punishment='Higher-value larceny or certain property types significantly increase punishment.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 131',
        title='Perjury and False Swearing',
        summary='Punishes knowingly false testimony or false sworn statements under the applicable specifications.',
        elements=(
            'The accused took an oath or made a statement under circumstances covered by the article.',
            'The statement was false in a material or required particular.',
            'The accused knew the statement was false.',
            'The false statement was made willfully under the charged specification.',
        ),
        notes='Materiality and oath requirements vary by specification.',
        keywords=('perjury', 'false swearing', 'lied under oath'),
        related_codes=('Article 107',),
        minimum_punishment='Punishment depends on the exact false-oath specification and forum.',
        maximum_punishment='Maximum punishment is significant because of the integrity of sworn proceedings.',
    ),
    LegalEntry(
        source='UCMJ',
        code='Article 134',
        title='General Article',
        summary='Covers disorders, neglects, and conduct of a nature to bring discredit upon the armed forces or prejudice good order and discipline.',
        elements=(
            'The accused committed or failed to commit certain acts.',
            'Under the circumstances, the conduct was prejudicial to good order and discipline or service-discrediting, or violated a listed offense under the article.',
            'The conduct was wrongful.',
        ),
        notes='The exact elements depend on the listed offense or theory charged under Article 134.',
        keywords=('general article', 'service discrediting', 'good order and discipline', 'conduct unbecoming but not officer'),
        related_codes=('Article 92', 'Article 117'),
        minimum_punishment='Punishment depends entirely on the charged theory and specification.',
        maximum_punishment='Maximum punishment varies widely because Article 134 covers many different offenses and theories.',
    ),
)


FEDERAL_USC_CODES = (
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1382',
        title='Entering Military, Naval, or Coast Guard Property',
        short_title='Military Installation Trespass',
        summary='Federal offense for going upon, reentering, or remaining on military installations for prohibited purposes or after being removed, ordered not to reenter, or barred by competent authority.',
        plain_language_summary='Use for barred-from-base returns, unlawful reentry onto military installations, or unauthorized presence on restricted military property when the federal installation-entry statute applies.',
        elements=(
            'The installation or property was military, naval, Space Force, or Coast Guard property of the United States covered by 18 USC 1382.',
            'The accused entered, reentered, remained on, or went upon the installation without authority, for a prohibited purpose, or after being ordered not to reenter or removed by competent authority.',
            'The conduct satisfied the charged installation-access prohibition under federal law.',
        ),
        required_elements=(
            'Federal military installation/property status.',
            'Unauthorized entry, reentry, or remaining after warning, removal, or barment.',
            'Competent authority and notice facts supporting exclusion/reentry theory.',
        ),
        notes='Primary federal installation-trespass/barment reentry statute. Evaluate command barment paperwork, prior warning/removal, and exact installation authority facts.',
        enforcement_notes='Preserve barment notice, debarment letter, prior warning/removal documentation, gate logs, and restricted-area signage or access-control evidence.',
        keywords=('federal installation trespass', '18 usc 1382', 'barred from base returned', 'military installation trespass', 'reentered base after warning'),
        aliases=('barred from base', 'barred from installation', 'debarred subject returned', 'military base trespass'),
        synonyms=('unauthorized reentry', 'barment violation', 'installation exclusion violation', 'federal military property trespass'),
        narrative_triggers=('trespassing on a federal installation', 'barred from military base and returned', 'unlawful entry onto military installation', 'entered federal military property after warning'),
        scenario_triggers=('barred from base', 'reentered base', 'federal installation', 'military installation', 'restricted area entry'),
        conduct_verbs=('entered', 'reentered', 'returned', 'remained', 'went upon'),
        location_context=('military installation', 'federal installation', 'base', 'restricted area', 'installation gate', 'federal military property'),
        federal_context=('federal installation', 'federal property', 'military property', 'barment', 'debarment'),
        military_context=('base', 'installation commander', 'barment letter', 'restricted military area'),
        category='Installation Access Offense',
        subcategory='Federal Military Installation Trespass',
        severity='Federal misdemeanor/federal offense review required',
        penalties='Federal penalties and prosecutive authority depend on the charged theory and applicable federal disposition.',
        related_codes=('18 USC 930', '18 USC 1361'),
        related_statutes=('18 USC 930', '18 USC 1361'),
        related_orders=('MCLBAO 5500.7',),
        minimum_punishment='Punishment depends on federal charging disposition and installation-enforcement posture.',
        maximum_punishment='Maximum punishment is governed by 18 USC 1382 and applicable federal sentencing/disposition authority.',
        source_group='Federal USC',
        source_reference='United States Code',
        source_reference_url='https://www.law.cornell.edu/uscode/text/18/1382',
        official_text_available=False,
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 922(g)',
        title='Firearm Possession by Prohibited Person',
        summary='Federal prohibition on possession of firearms/ammunition by specified prohibited categories (including felony convictions).',
        elements=(
            'The accused knowingly possessed a firearm or ammunition.',
            'At the time of possession, the accused fit a prohibited category under 18 USC 922(g).',
            'Interstate commerce nexus requirement is met under federal law.',
        ),
        notes='Federal charging decision and nexus analysis required.',
        keywords=('federal felon in possession', '922g', 'prohibited person firearm', 'federal firearm offense'),
        related_codes=('18 USC 924',),
        minimum_punishment='Punishment depends on federal charging path and criminal history.',
        maximum_punishment='Maximum punishment is governed by 18 USC 924 and related federal sentencing rules.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 641',
        title='Theft of Government Property',
        summary='Federal offense covering theft, conversion, or unauthorized disposition of U.S. government property, money, or records.',
        elements=(
            'Property or value belonged to the United States or an agency thereof.',
            'The accused stole, converted, or knowingly retained/disposed of the property without authority.',
            'The conduct was knowing and intentional under the statute.',
        ),
        notes='Useful for federal property-loss and conversion investigations.',
        keywords=('stole government property', 'federal property theft', '18 usc 641', 'u.s. property conversion'),
        related_codes=('18 USC 1361',),
        minimum_punishment='Penalty depends on value thresholds and charging specification.',
        maximum_punishment='Maximum punishment varies by value and offense theory under 18 USC 641.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1361',
        title='Willful Injury of Government Property',
        summary='Federal offense for willful injury, depredation, or attempted damage to U.S. property.',
        elements=(
            'The property belonged to the United States.',
            'The accused willfully injured, depredated, or attempted to damage that property.',
            'The conduct satisfied statutory damage/value requirements.',
        ),
        notes='Common federal reference for damage to government facilities/property.',
        keywords=('damaged government property', 'federal vandalism government property', '18 usc 1361'),
        related_codes=('18 USC 641',),
        minimum_punishment='Penalty depends on damage amount and charged specification.',
        maximum_punishment='Maximum punishment scales with value and offense circumstances.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1343',
        title='Wire Fraud',
        summary='Federal fraud offense involving schemes to defraud using interstate wire, radio, or television communications.',
        elements=(
            'The accused knowingly participated in a scheme to defraud or obtain money/property by false pretenses.',
            'The accused acted with intent to defraud.',
            'Interstate wire communications were used in furtherance of the scheme.',
        ),
        keywords=('wire fraud', 'internet fraud', 'electronic fraud', 'interstate communications fraud'),
        minimum_punishment='Punishment depends on charge specifics and federal sentencing factors.',
        maximum_punishment='Maximum punishment is governed by 18 USC 1343 and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1028',
        title='Fraud and Related Activity in Connection with Identification Documents',
        summary='Federal offense covering fraudulent production, transfer, or use of identification documents and authentication features.',
        elements=(
            'The accused knowingly produced, transferred, possessed, or used identification documents/features as prohibited by statute.',
            'The conduct matched a prohibited act under 18 USC 1028.',
            'Jurisdictional federal nexus requirements were met.',
        ),
        keywords=('identity document fraud', 'fake id', 'identity fraud', '18 usc 1028'),
        minimum_punishment='Punishment depends on subsection and offense circumstances.',
        maximum_punishment='Maximum punishment varies by subsection and aggravating factors.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1028A',
        title='Aggravated Identity Theft',
        summary='Federal offense for knowingly transferring, possessing, or using another person’s means of identification during specified felony offenses.',
        elements=(
            'The accused knowingly transferred, possessed, or used another person’s means of identification.',
            'The conduct occurred during and in relation to a predicate felony offense listed by statute.',
            'The conduct was without lawful authority.',
        ),
        keywords=('aggravated identity theft', 'stolen identity during felony', '18 usc 1028a'),
        minimum_punishment='Punishment includes mandatory federal sentencing components where applicable.',
        maximum_punishment='Maximum punishment follows statutory terms and federal sentencing rules.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 2113',
        title='Bank Robbery and Incidental Crimes',
        summary='Federal offense for taking or attempting to take property or money from banks/credit institutions by force, violence, intimidation, or specified means.',
        elements=(
            'The target institution qualified under federal statute.',
            'The accused took or attempted to take money/property by force, violence, intimidation, or other prohibited conduct.',
            'The conduct met the charged subsection under 18 USC 2113.',
        ),
        keywords=('bank robbery', 'federal bank robbery', 'rob bank', '18 usc 2113'),
        minimum_punishment='Punishment depends on charged subsection and facts.',
        maximum_punishment='Maximum punishment varies based on use of force, weapons, injury, and subsection charged.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1708',
        title='Theft or Receipt of Stolen Mail Matter',
        summary='Federal offense for theft, receipt, or unlawful possession of stolen mail or mail matter.',
        elements=(
            'Mail matter was stolen, taken, or obtained from authorized mail channels.',
            'The accused stole, possessed, received, or concealed such mail matter as prohibited.',
            'The accused acted knowingly and unlawfully.',
        ),
        keywords=('mail theft', 'stolen mail', 'mail matter offense', '18 usc 1708'),
        minimum_punishment='Punishment depends on case facts and federal sentencing considerations.',
        maximum_punishment='Maximum punishment is controlled by 18 USC 1708 and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 875(c)',
        title='Interstate Communications Threats',
        summary='Federal offense for transmitting threats in interstate or foreign communications.',
        elements=(
            'The accused transmitted a communication in interstate or foreign commerce.',
            'The communication contained a true threat as charged under statute.',
            'The accused acted knowingly and unlawfully under the charged theory.',
        ),
        keywords=('threat across state lines', 'interstate threat', '18 usc 875', 'threat by electronic communication'),
        minimum_punishment='Punishment depends on charged subsection and federal sentencing factors.',
        maximum_punishment='Maximum punishment is governed by 18 USC 875 and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 2261',
        title='Interstate Domestic Violence',
        summary='Federal offense covering interstate travel or conduct involving domestic violence under charged statutory paths.',
        elements=(
            'The accused traveled in interstate or foreign commerce, or caused/used interstate facilities as charged.',
            'The conduct involved domestic violence against a spouse, intimate partner, or dating partner as defined by statute.',
            'The charged injury/violent act elements under 18 USC 2261 were met.',
        ),
        notes='Jurisdiction requires interstate/federal nexus and relationship elements.',
        keywords=('interstate domestic violence', 'federal domestic violence', '18 usc 2261', 'crossed state lines to assault partner'),
        related_codes=('18 USC 2261A', '18 USC 2262'),
        minimum_punishment='Punishment depends on charged subsection and injury severity.',
        maximum_punishment='Maximum punishment is governed by 18 USC 2261 and applicable federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 2261A',
        title='Interstate Stalking and Related Conduct',
        summary='Federal offense covering interstate stalking, harassment, surveillance, or threatening conduct using interstate commerce channels under charged paths.',
        elements=(
            'The accused used interstate commerce travel, mail, or electronic communication facilities as charged.',
            'The accused engaged in conduct intended to kill, injure, harass, intimidate, or place under surveillance with prohibited purpose under statute.',
            'The charged fear, emotional distress, injury, or attempted injury result element was satisfied.',
        ),
        notes='Use for cross-state stalking/text harassment patterns with federal nexus.',
        keywords=('interstate stalking', 'federal stalking', '18 usc 2261a', 'threatening messages across state lines', 'harassing messages interstate'),
        related_codes=('18 USC 875(c)', '18 USC 2261', '18 USC 2262'),
        minimum_punishment='Punishment depends on charged subsection and harm facts.',
        maximum_punishment='Maximum punishment is governed by 18 USC 2261A and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 2262',
        title='Interstate Violation of Protection Order',
        summary='Federal offense covering interstate travel or conduct that violates qualifying protection orders.',
        elements=(
            'A valid protection order existed and was enforceable under federal law.',
            'The accused traveled in interstate commerce or engaged in the charged interstate conduct.',
            'The accused knowingly violated the qualifying protection order as charged.',
        ),
        notes='Applies where interstate nexus exists for protection-order violations.',
        keywords=('interstate protection order violation', 'federal protective order violation', '18 usc 2262', 'crossed state lines violating restraining order'),
        related_codes=('18 USC 2261', '18 USC 2261A'),
        minimum_punishment='Punishment depends on charged subsection and case facts.',
        maximum_punishment='Maximum punishment is governed by 18 USC 2262 and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1030',
        title='Fraud and Related Activity in Connection with Computers',
        summary='Federal computer offense statute addressing unauthorized access and related fraud/damage conduct.',
        elements=(
            'The accused intentionally accessed a protected computer without authorization or exceeded authorized access, as charged.',
            'The conduct matched a prohibited subsection under 18 USC 1030.',
            'Required intent, damage, value, or obtaining-information elements were met under the charged subsection.',
        ),
        keywords=('unauthorized computer access', 'government computer hack', 'computer fraud', '18 usc 1030'),
        minimum_punishment='Punishment depends on subsection and harm/loss factors.',
        maximum_punishment='Maximum punishment varies substantially by subsection and aggravating factors.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 930',
        title='Possession of Firearms and Dangerous Weapons in Federal Facilities',
        summary='Federal offense covering knowing possession or use of weapons in federal facilities under prohibited conditions.',
        elements=(
            'The accused knowingly possessed or used a firearm/dangerous weapon in a federal facility or federal court facility as charged.',
            'The location and circumstances met statutory requirements.',
            'No statutory defense or exception applied for the charged theory.',
        ),
        keywords=('firearm in federal facility', 'weapon in federal building', '18 usc 930'),
        minimum_punishment='Punishment depends on possession/use theory and circumstances.',
        maximum_punishment='Maximum punishment is governed by subsection and federal sentencing law.',
    ),
    LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 471',
        title='Obligations or Securities of United States (Counterfeiting)',
        summary='Federal offense for falsely making, forging, counterfeiting, or altering obligations or securities of the United States.',
        elements=(
            'The accused falsely made, forged, counterfeited, or altered obligations/securities of the United States.',
            'The conduct was done with requisite unlawful intent under statute.',
            'The act met statutory requirements of 18 USC 471.',
        ),
        keywords=('counterfeit money', 'fake currency', 'counterfeiting', '18 usc 471'),
        minimum_punishment='Punishment depends on charged conduct and federal sentencing factors.',
        maximum_punishment='Maximum punishment is governed by 18 USC 471 and federal sentencing law.',
    ),
)


LEGAL_DATA_DIR = Path(__file__).resolve().parents[1] / 'data' / 'legal'
GEORGIA_CORPUS_PATH = LEGAL_DATA_DIR / 'georgia_codes.json'
UCMJ_CORPUS_PATH = LEGAL_DATA_DIR / 'ucmj_articles.json'
BASE_ORDER_CORPUS_PATH = LEGAL_DATA_DIR / 'base_orders.json'
FEDERAL_USC_CORPUS_PATH = LEGAL_DATA_DIR / 'federal_usc_codes.json'

_CORPUS_CACHE = {
    'georgia_mtime': None,
    'ucmj_mtime': None,
    'base_order_mtime': None,
    'federal_usc_mtime': None,
    'georgia_entries': GEORGIA_CODES,
    'ucmj_entries': UCMJ_ARTICLES,
    'base_order_entries': tuple(item for item in GEORGIA_CODES if str(item.code).startswith('MCLBAO')),
    'federal_usc_entries': FEDERAL_USC_CODES,
}


def _default_minimum_punishment(source: str, code: str) -> str:
    src = (source or '').upper()
    code_u = (code or '').upper()
    if code_u.startswith('MCLBAO'):
        return 'Minimum action is handled under applicable installation/base order enforcement policy.'
    if src == 'FEDERAL_USC':
        return 'Minimum punishment depends on charged federal subsection, charging policy, and federal sentencing framework.'
    if src == 'UCMJ':
        return 'Minimum punishment depends on charged specification, forum, and applicable Manual for Courts-Martial provisions.'
    return 'Minimum punishment is controlled by the charged OCGA subsection and court disposition.'


def _default_maximum_punishment(source: str, code: str) -> str:
    src = (source or '').upper()
    code_u = (code or '').upper()
    if code_u.startswith('MCLBAO'):
        return 'Maximum action is governed by installation/base order enforcement authority and applicable command disposition.'
    if src == 'FEDERAL_USC':
        return 'Maximum punishment is governed by the charged federal statute and federal sentencing law.'
    if src == 'UCMJ':
        return 'Maximum punishment is governed by the current Manual for Courts-Martial for the charged specification.'
    return 'Maximum punishment is governed by the charged OCGA subsection and sentencing disposition.'


def _with_punishment_defaults(entry: LegalEntry) -> LegalEntry:
    min_text = (entry.minimum_punishment or '').strip()
    max_text = (entry.maximum_punishment or '').strip()
    if min_text and max_text:
        return entry
    if not min_text:
        min_text = _default_minimum_punishment(entry.source, entry.code)
    if not max_text:
        max_text = _default_maximum_punishment(entry.source, entry.code)
    return replace(entry, minimum_punishment=min_text, maximum_punishment=max_text)

SYNONYM_MAP = {
    'speed': ('speeding', 'over limit'),
    'speeding': ('speed restriction', 'over limit'),
    'dui': ('impaired', 'drunk driving', 'refusal'),
    'drunk': ('dui', 'impaired'),
    'handicap': ('disabled', 'placard'),
    'disabled': ('handicap', 'placard'),
    'tailgating': ('following too closely', 'following too close'),
    'tailgater': ('following too closely', 'following too close'),
    'awol': ('absence without leave', 'failure to go'),
    'disrespect': ('insubordinate', 'insubordination'),
    'assault': ('battery', 'bodily harm'),
    'fight': ('assault', 'battery'),
    'yelling': ('disrespect', 'insubordinate'),
    'refused': ('failure to obey', 'refusal'),
    'refusal': ('dui refusal', 'failure to obey'),
    'missing': ('awol', 'absence'),
    'plate': ('tag', 'registration'),
    'registration': ('tag', 'plate'),
    'driving': ('vehicle', 'motor vehicle'),
    'beat': ('battery', 'assault', 'physical harm'),
    'beating': ('battery', 'assault', 'physical harm'),
    'wife': ('spouse', 'domestic violence', 'family violence'),
    'husband': ('spouse', 'domestic violence', 'family violence'),
    'girlfriend': ('dating partner', 'domestic violence', 'family violence'),
    'boyfriend': ('dating partner', 'domestic violence', 'family violence'),
    'spouse': ('domestic violence', 'family violence'),
    'domestic': ('family violence', 'battery', 'assault'),
    'violence': ('family violence', 'battery', 'assault'),
    'stole': ('theft', 'robbery', 'larceny'),
    'stolen': ('theft', 'auto theft', 'vehicle theft'),
    'theft': ('stole', 'shoplifting', 'robbery'),
    'drugs': ('controlled substance', 'narcotics', 'possession'),
    'narcotics': ('drugs', 'controlled substance'),
    'fentanyl': ('controlled substance', 'opioid', 'schedule ii drug'),
    'opioid': ('controlled substance', 'narcotics'),
    'prescription': ('rx', 'controlled substance', 'fraud'),
    'rx': ('prescription', 'controlled substance'),
    'meth': ('methamphetamine', 'controlled substance'),
    'methamphetamine': ('meth', 'schedule ii drug'),
    'gun': ('firearm', 'weapon'),
    'weapon': ('firearm', 'armed'),
    'killed': ('homicide', 'murder'),
    'homicide': ('murder', 'manslaughter'),
    'mclb': ('mclb albany', 'installation', 'base'),
    'installation': ('military installation', 'federal installation', 'base'),
    'base': ('military installation', 'federal installation', 'mclb'),
    'raped': ('rape', 'sexual assault', 'nonconsensual sex'),
    'raping': ('rape', 'sexual assault', 'nonconsensual sex'),
    'rape': ('sexual assault', 'forcible rape', 'nonconsensual sex'),
    'sexual': ('sexual assault', 'sex offense', 'nonconsensual'),
    'nonconsensual': ('sexual assault', 'rape'),
    'usc': ('federal code', 'united states code'),
    'federal': ('usc', 'united states code'),
    'government property': ('federal property', 'u s property'),
}

SCENARIO_PACKS = {
    'traffic': {
        'triggers': ('traffic', 'car', 'vehicle', 'road', 'speed', 'lane', 'signal', 'stop sign', 'red light', 'base traffic', 'mclb traffic'),
        'codes': (
            'OCGA 40-6-181',
            'OCGA 40-6-20',
            'OCGA 40-6-72',
            'OCGA 40-6-221',
            'OCGA 40-6-48',
            'OCGA 40-6-123',
            'OCGA 40-6-49',
            'MCLBAO 5560.9G CH3-11',
            'MCLBAO 5560.9G CH3-16/17',
            'MCLBAO 5560.9G CH3-18',
            'MCLBAO 5560.9G CH6',
        ),
    },
    'dui': {
        'triggers': ('dui', 'drunk', 'impaired', 'alcohol', 'refusal', 'less safe'),
        'codes': (
            'OCGA 40-6-391',
            'OCGA 40-5-67.1',
            'OCGA 40-6-392',
            'OCGA 40-6-48',
        ),
    },
    'registration': {
        'triggers': ('registration', 'plate', 'tag', 'suspended license', 'no license', 'revoked'),
        'codes': (
            'OCGA 40-2-8',
            'OCGA 40-5-20',
            'OCGA 40-5-121',
        ),
    },
    'assault': {
        'triggers': ('fight', 'assault', 'battery', 'hit', 'pushed', 'slapped', 'threatened'),
        'codes': (
            'OCGA 16-5-20',
            'OCGA 16-5-23',
            'OCGA 16-5-23.1',
            'OCGA 16-5-21',
            'Article 128',
            'Article 91',
        ),
    },
    'domestic_violence': {
        'triggers': (
            'beat up',
            'beat his wife',
            'beat her',
            'domestic violence',
            'family violence',
            'spouse',
            'wife',
            'husband',
            'boyfriend',
            'girlfriend',
            'dating partner',
            'protective order',
            'restraining order',
            'stalking',
            'would not let her leave',
        ),
        'codes': (
            'OCGA 16-5-23',
            'OCGA 16-5-23.1',
            'OCGA 16-5-20',
            'OCGA 16-5-21',
            'OCGA 16-5-90',
            'OCGA 16-5-91',
            'OCGA 16-5-95',
            'OCGA 16-5-41',
            'OCGA 16-5-40',
            'OCGA 16-5-70',
            'Article 128',
            'Article 128b',
            'Article 130',
            '18 USC 2261',
            '18 USC 2261A',
            '18 USC 2262',
        ),
    },
    'sexual_offense': {
        'triggers': (
            'rape',
            'forcible rape',
            'sexual assault',
            'sexual battery',
            'nonconsensual',
            'forced sex',
            'sex offense',
        ),
        'codes': (
            'OCGA 16-6-1',
            'OCGA 16-6-22',
            'Article 120',
        ),
    },
    'public_indecency': {
        'triggers': (
            'sex in public',
            'public sex',
            'public indecency',
            'indecent exposure',
            'streaking',
            'public nudity',
            'nude in public',
            'exposed himself',
            'exposed herself',
            'lewd conduct',
            'public defecation',
            'defecating in public',
            'pooping in public',
            'pooping in the street',
        ),
        'codes': (
            'OCGA 16-6-8',
            'OCGA 16-11-39',
        ),
    },
    'disrespect': {
        'triggers': ('disrespect', 'insubordinate', 'refused command', 'yelling at supervisor', 'talking back'),
        'codes': (
            'Article 89',
            'Article 90',
            'Article 91',
            'Article 92',
            'Article 117',
        ),
    },
    'absence': {
        'triggers': ('awol', 'missing movement', 'did not report', 'absent from duty', 'failed to go'),
        'codes': (
            'Article 86',
            'Article 87',
            'Article 92',
        ),
    },
    'obstruction': {
        'triggers': ('obstruction', 'resisting', 'would not comply', 'interfered with officer', 'pulled away'),
        'codes': (
            'OCGA 16-10-24',
            'OCGA 16-11-39',
            'Article 91',
            'Article 92',
        ),
    },
    'theft_robbery': {
        'triggers': (
            'stole',
            'steal',
            'stealing',
            'theft',
            'shoplifting',
            'store theft',
            'retail theft',
            'robbery',
            'armed robbery',
            'snatched',
            'by force',
            'from person',
            'carjacking',
        ),
        'codes': (
            'OCGA 16-8-2',
            'OCGA 16-8-14',
            'OCGA 16-8-40',
            'OCGA 16-8-41',
            'Article 121',
        ),
    },
    'burglary': {
        'triggers': ('broke into', 'entered home to steal', 'entered house and stole', 'burglary', 'forced entry and theft'),
        'codes': (
            'OCGA 16-7-22',
            'OCGA 16-8-2',
        ),
    },
    'drugs': {
        'triggers': (
            'drug',
            'drugs',
            'narcotics',
            'cocaine',
            'meth',
            'methamphetamine',
            'marijuana',
            'trafficking',
            'paraphernalia',
            'fake pills',
            'counterfeit pills',
            'forged prescription',
            'prescription fraud',
            'rx fraud',
            'near school',
            'drug free zone',
            'used a child',
            'minor in drug',
            'meth lab',
            'precursor',
            'pill mill',
            'unlawful prescribing',
        ),
        'codes': (
            'OCGA 16-13-30',
            'OCGA 16-13-30.1',
            'OCGA 16-13-30.2',
            'OCGA 16-13-30.3',
            'OCGA 16-13-30.4',
            'OCGA 16-13-31',
            'OCGA 16-13-32',
            'OCGA 16-13-32.2',
            'OCGA 16-13-32.4',
            'OCGA 16-13-32.5',
            'OCGA 16-13-33',
            'OCGA 16-13-33.1',
            'OCGA 16-13-39',
            'OCGA 16-13-45',
            'OCGA 16-13-57',
            'OCGA 16-13-58',
            'OCGA 16-13-59',
            'OCGA 16-13-60',
            'OCGA 16-13-61',
            'OCGA 16-13-71',
            'OCGA 16-13-75',
            'Article 112a',
            'Article 112',
        ),
    },
    'weapons': {
        'triggers': ('gun', 'firearm', 'weapon', 'felon in possession', 'carrying weapon', 'prohibited place'),
        'codes': (
            'OCGA 16-11-126',
            'OCGA 16-11-127',
            'OCGA 16-11-131',
            'OCGA 16-11-132',
            'OCGA 16-8-41',
        ),
    },
    'homicide': {
        'triggers': ('murder', 'homicide', 'killed', 'manslaughter'),
        'codes': (
            'OCGA 16-5-1',
            'OCGA 16-5-2',
        ),
    },
    'federal_crimes': {
        'triggers': (
            'federal offense',
            'usc',
            'federal code',
            'felon with gun',
            'counterfeit money',
            'identity theft',
            'bank robbery',
            'mail theft',
            'wire fraud',
            'stolen government property',
            'damage to federal property',
            'federal facility',
            'government computer access',
            'threat across state lines',
            'interstate domestic violence',
            'interstate stalking',
            'interstate protection order violation',
        ),
        'codes': (
            '18 USC 922(g)',
            '18 USC 641',
            '18 USC 1361',
            '18 USC 2261',
            '18 USC 2261A',
            '18 USC 2262',
        ),
    },
}

INTENT_PHRASE_CODES = {
    '65 in a 25': ('OCGA 40-6-181', 'MCLBAO 5560.9G CH3-11'),
    'speeding': ('OCGA 40-6-181',),
    'reckless driving': ('OCGA 40-6-390',),
    'aggressive driving': ('OCGA 40-6-397',),
    'dui': ('OCGA 40-6-391', 'OCGA 40-5-67.1', 'OCGA 40-6-392'),
    'dui refusal': ('OCGA 40-6-391', 'OCGA 40-5-67.1', 'OCGA 40-6-392'),
    'refused breath test': ('OCGA 40-6-391', 'OCGA 40-5-67.1', 'OCGA 40-6-392'),
    'refused test': ('OCGA 40-6-391', 'OCGA 40-5-67.1', 'OCGA 40-6-392'),
    'domestic violence': ('OCGA 16-5-23', 'OCGA 16-5-23.1', 'OCGA 16-5-20', 'OCGA 16-5-21', 'OCGA 16-5-90', 'OCGA 16-5-95', 'Article 128b', '18 USC 2261'),
    'family violence': ('OCGA 16-5-23', 'OCGA 16-5-23.1', 'OCGA 16-5-20', 'OCGA 16-5-21', 'OCGA 16-5-90', 'OCGA 16-5-95', 'Article 128b', '18 USC 2261'),
    'rape': ('OCGA 16-6-1', 'OCGA 16-6-22', 'Article 120'),
    'sexual assault': ('OCGA 16-6-1', 'OCGA 16-6-22', 'Article 120'),
    'aggravated sexual battery': ('OCGA 16-6-22',),
    'forced sex': ('OCGA 16-6-1', 'OCGA 16-6-22', 'Article 120'),
    'sex in public': ('OCGA 16-6-8',),
    'public indecency': ('OCGA 16-6-8',),
    'indecent exposure': ('OCGA 16-6-8',),
    'streaking': ('OCGA 16-6-8',),
    'public nudity': ('OCGA 16-6-8',),
    'public defecation': ('OCGA 16-11-39', 'OCGA 16-6-8'),
    'defecating in public': ('OCGA 16-11-39', 'OCGA 16-6-8'),
    'pooping in public': ('OCGA 16-11-39', 'OCGA 16-6-8'),
    'pooping in the street': ('OCGA 16-11-39', 'OCGA 16-6-8'),
    'parking in handicap without sticker': ('OCGA 40-6-221',),
    'handicap parking': ('OCGA 40-6-221',),
    'ran stop sign': ('OCGA 40-6-20', 'OCGA 40-6-72'),
    'theft': ('OCGA 16-8-2', 'OCGA 16-8-14', 'OCGA 16-8-40', 'OCGA 16-8-41', 'Article 121'),
    'car stolen': ('OCGA 16-8-2', 'OCGA 16-8-7', 'OCGA 16-8-60'),
    'vehicle stolen': ('OCGA 16-8-2', 'OCGA 16-8-7', 'OCGA 16-8-60'),
    'auto theft': ('OCGA 16-8-2', 'OCGA 16-8-7', 'OCGA 16-8-60'),
    'stolen vehicle': ('OCGA 16-8-2', 'OCGA 16-8-7', 'OCGA 16-8-60'),
    'vehicle taken': ('OCGA 16-8-2', 'OCGA 16-8-60'),
    'car taken': ('OCGA 16-8-2', 'OCGA 16-8-60'),
    'shoplifting': ('OCGA 16-8-14',),
    'stealing from the store': ('OCGA 16-8-14', 'OCGA 16-8-2'),
    'store theft': ('OCGA 16-8-14', 'OCGA 16-8-2'),
    'retail theft': ('OCGA 16-8-14', 'OCGA 16-8-2'),
    'robbery': ('OCGA 16-8-40', 'OCGA 16-8-41'),
    'stole wallet by force': ('OCGA 16-8-40', 'OCGA 16-8-41'),
    'carjacking': ('OCGA 16-8-44', 'OCGA 16-8-41'),
    'burglary': ('OCGA 16-7-22', 'OCGA 16-8-2'),
    'broke into home and stole tv': ('OCGA 16-7-22', 'OCGA 16-8-2'),
    'drug trafficking': ('OCGA 16-13-31',),
    'drug possession': ('OCGA 16-13-30', 'OCGA 16-13-75', 'OCGA 16-13-58'),
    'meth possession': ('OCGA 16-13-30', 'OCGA 16-13-58'),
    'possession of methamphetamine': ('OCGA 16-13-30', 'OCGA 16-13-58'),
    'sold cocaine near a school': ('OCGA 16-13-30', 'OCGA 16-13-30.1'),
    'used a child to run narcotics': ('OCGA 16-13-30.3', 'OCGA 16-13-30'),
    'drug pipe with residue': ('OCGA 16-13-32.2',),
    'fake pills': ('OCGA 16-13-32.4', 'OCGA 16-13-32.5'),
    'counterfeit pills': ('OCGA 16-13-32.4', 'OCGA 16-13-32.5'),
    'forged prescription': ('OCGA 16-13-33', 'OCGA 16-13-33.1'),
    'forged prescription for oxycodone': ('OCGA 16-13-33', 'OCGA 16-13-33.1', 'OCGA 16-13-58'),
    'meth lab precursor chemicals': ('OCGA 16-13-45', 'OCGA 16-13-30'),
    'doctor writing unlawful narcotic scripts': ('OCGA 16-13-39', 'OCGA 16-13-33.1'),
    'marijuana possession': ('OCGA 16-13-75', 'OCGA 16-13-30', 'OCGA 16-13-71'),
    'possession of marijuana': ('OCGA 16-13-75', 'OCGA 16-13-30', 'OCGA 16-13-71'),
    'weed possession': ('OCGA 16-13-75', 'OCGA 16-13-30', 'OCGA 16-13-71'),
    'wrongful use of controlled substance': ('Article 112a',),
    'wrongful possession military': ('Article 112a',),
    'introduced drugs on base': ('Article 112a',),
    'marine used cocaine': ('Article 112a',),
    'service member drug use': ('Article 112a',),
    'high on duty': ('Article 112', 'Article 112a'),
    'felon in possession': ('OCGA 16-11-131',),
    'awol': ('Article 86', 'Article 87'),
    'disrespect': ('Article 89', 'Article 91', 'Article 92'),
    'failure to obey order': ('Article 92',),
    'refused lawful command': ('Article 92', 'Article 91'),
    'disobeyed direct order': ('Article 92',),
    'simple assault no injury': ('OCGA 16-5-20', 'OCGA 16-5-23'),
    'weed found in vehicle': ('OCGA 16-13-75', 'OCGA 16-13-30', 'OCGA 16-13-71'),
    'drove on base while intoxicated': ('OCGA 40-6-391', 'MCLBAO 5560.9G CH3-11', 'MCLBAO 5560.9G CH6'),
    'drunk in barracks and fighting': ('Article 112', 'Article 128', 'Article 134'),
    'harassing messages': ('OCGA 16-5-90', 'OCGA 16-5-91', 'Article 130', '18 USC 2261A'),
    'violated protective order': ('OCGA 16-5-95', 'OCGA 16-5-91', '18 USC 2262'),
    'would not let her leave': ('OCGA 16-5-41', 'OCGA 16-5-40', 'Article 128b'),
    'interstate domestic violence': ('18 USC 2261', '18 USC 2261A', '18 USC 2262'),
    'interstate stalking': ('18 USC 2261A', '18 USC 875(c)'),
    'trespassing after being told to leave': ('OCGA 16-7-21',),
    'damaged government property': ('18 USC 1361', '18 USC 641'),
    'stole government property': ('18 USC 641',),
    'federal felon in possession': ('18 USC 922(g)',),
    'felon with gun': ('18 USC 922(g)',),
    'counterfeit money': ('18 USC 471',),
    'identity theft': ('18 USC 1028', '18 USC 1028A'),
    'bank robbery': ('18 USC 2113',),
    'mail theft': ('18 USC 1708',),
    'wire fraud': ('18 USC 1343',),
    'threat sent across state lines': ('18 USC 875(c)',),
    'unauthorized access to government computer': ('18 USC 1030',),
    'firearm in federal facility': ('18 USC 930',),
    'mclb traffic court': ('MCLBAO 5560.9G CH6',),
}

STOPWORDS = {
    'a', 'an', 'and', 'are', 'at', 'be', 'but', 'by', 'for', 'from', 'how', 'i', 'if', 'in', 'is', 'it',
    'me', 'my', 'of', 'on', 'or', 'so', 'that', 'the', 'their', 'them', 'they', 'this', 'to', 'was', 'we',
    'what', 'when', 'where', 'which', 'who', 'with', 'would', 'you', 'your', 'while', 'during', 'can',
    'he', 'she', 'his', 'her', 'hers', 'him', 'subject', 'suspect', 'victim',
}

AMBIGUOUS_TERMS = {
    'vehicle', 'car', 'person', 'subject', 'suspect', 'victim', 'incident', 'report',
    'officer', 'base', 'property', 'message', 'phone', 'text', 'public', 'store',
}

MISSPELLING_MAP = {
    'hancicap': 'handicap',
    'handicapp': 'handicap',
    'disrepect': 'disrespect',
    'disrespekt': 'disrespect',
    'wepon': 'weapon',
    'wepons': 'weapons',
    'felonn': 'felon',
    'shopliftng': 'shoplifting',
    'reckles': 'reckless',
    'drving': 'driving',
    'lisence': 'license',
    'suspened': 'suspended',
    'obstrution': 'obstruction',
    'posassion': 'possession',
    'posession': 'possession',
    'possion': 'possession',
    'marjauana': 'marijuana',
    'marajuana': 'marijuana',
    'marijuanna': 'marijuana',
    'textingg': 'texting',
    'tresspass': 'trespass',
    'shop lift': 'shoplift',
    'marihuana': 'marijuana',
    'vicitm': 'victim',
}

SHORTHAND_MAP = {
    'subj': 'subject',
    'susp': 'suspect',
    'vic': 'victim',
    'comp': 'complainant',
    'dv': 'domestic violence',
    'tpo': 'protective order',
    'px': 'exchange store',
    'uo': 'under investigation',
    'w/': 'with',
    'w/o': 'without',
    'u/s': 'under suspicion',
    'dwi': 'dui',
    'mva': 'vehicle accident',
}

PHRASE_ALIASES = {
    'following too close': ('tailgating', 'following too closely'),
    '65 in a 25': ('speeding', 'over speed limit'),
    'refused breath test': ('dui refusal', 'implied consent', 'dui'),
    'refused blood test': ('dui refusal', 'implied consent', 'dui'),
    'refused test': ('dui refusal', 'implied consent', 'dui'),
    'smelled of alcohol': ('dui', 'impaired'),
    'weaving': ('failure to maintain lane', 'dui'),
    'ran a red light': ('traffic control device', 'signal violation'),
    'no turn signal': ('failed to signal',),
    'expired registration': ('tag expired', 'no valid registration'),
    'license suspended': ('driving while suspended',),
    'left the scene': ('hit and run',),
    'failure to obey order': ('disobeyed order', 'disobeyed command'),
    'refused command': ('willfully disobeyed',),
    'absent from duty': ('awol', 'failure to go'),
    'beat up': ('battery', 'assault', 'domestic violence', 'family violence'),
    'beat his wife': ('battery', 'domestic violence', 'family violence'),
    'beat her': ('battery', 'assault'),
    'beat up his wife': ('domestic violence', 'family violence', 'battery', 'spouse assault'),
    'man beat up his wife': ('domestic violence', 'family violence', 'battery'),
    'hit his wife': ('domestic violence', 'family violence', 'battery'),
    'boyfriend hit girlfriend': ('domestic violence', 'family violence', 'battery'),
    'husband raped his wife': ('rape', 'sexual assault', 'domestic violence', 'family violence'),
    'raped his wife': ('rape', 'sexual assault'),
    'raped her': ('rape', 'sexual assault'),
    'wife reports husband forced sex': ('forced sex', 'rape', 'sexual assault'),
    'sex in public': ('public indecency', 'indecent exposure'),
    'public sex': ('public indecency', 'indecent exposure'),
    'indecent exposure': ('public indecency',),
    'streaking': ('public indecency', 'indecent exposure', 'public nudity'),
    'public nudity': ('public indecency', 'indecent exposure', 'streaking'),
    'public defecation': ('disorderly conduct', 'public indecency', 'public nuisance'),
    'defecating in public': ('disorderly conduct', 'public indecency', 'public nuisance'),
    'pooping in public': ('disorderly conduct', 'public indecency', 'public nuisance'),
    'pooping in the street': ('disorderly conduct', 'public indecency', 'public nuisance'),
    'parking in handicap without sticker': ('handicap parking', 'disabled parking'),
    'ran stop sign': ('stop sign', 'traffic control device'),
    'mclb traffic': ('base traffic', 'installation traffic'),
    'base traffic': ('mclb traffic', 'installation traffic'),
    'on base speeding': ('mclb speed limit', 'base speed limit'),
    'base speed limit': ('mclb speed limit',),
    'mclb albany traffic': ('base traffic', 'mclb traffic'),
    'car stolen': ('theft', 'auto theft', 'vehicle theft'),
    'vehicle stolen': ('theft', 'auto theft', 'vehicle theft'),
    'stolen vehicle': ('theft', 'auto theft', 'vehicle theft'),
    'home owner had the car stolen': ('theft', 'auto theft', 'vehicle theft'),
    'vehicle was taken': ('theft', 'vehicle theft', 'car taken'),
    'car was taken': ('theft', 'vehicle theft', 'car taken'),
    'homeowner says vehicle was taken overnight': ('theft', 'vehicle theft', 'car taken'),
    'stealing from the store': ('shoplifting', 'retail theft', 'theft'),
    'store theft': ('shoplifting', 'retail theft', 'theft'),
    'retail theft': ('shoplifting', 'store theft', 'theft'),
    'stole wallet by force': ('robbery', 'armed robbery', 'theft from person'),
    'carjacking': ('robbery', 'vehicle theft', 'armed robbery'),
    'broke into home and stole tv': ('burglary', 'theft', 'entered home to steal'),
    'burglary': ('entered home to steal', 'forced entry and theft'),
    'juvenile with weed in school parking lot': ('marijuana possession', 'drug free zone', 'school zone narcotics'),
    'possession of methamphetamine': ('drug possession', 'meth', 'schedule ii drug'),
    'sold cocaine near a school': ('cocaine', 'drug free zone', 'school zone narcotics'),
    'used a child to run narcotics': ('minor in drug', 'drug trafficking', 'controlled substance'),
    'drug pipe with residue': ('drug paraphernalia', 'drug related object'),
    'forged prescription for oxycodone': ('forged prescription', 'prescription fraud', 'schedule ii drug'),
    'meth lab precursor chemicals': ('meth lab', 'precursor', 'drug manufacturing'),
    'doctor writing unlawful narcotic scripts': ('pill mill', 'unlawful prescribing', 'prescription fraud'),
    'possession of controlled substance': ('drug possession', 'controlled substance possession'),
    'controlled substance possession': ('drug possession', 'controlled substance possession'),
    'possessing pills': ('drug possession', 'prescription pill possession'),
    'possess pills': ('drug possession', 'prescription pill possession'),
    'illegal pills': ('drug possession', 'controlled substance possession'),
    'posession of prescription pills': ('drug possession', 'controlled substance possession', 'prescription pill possession'),
    'marijuana possession': ('drug possession', 'marijuana', 'weed', 'cannabis'),
    'possession of marijuana': ('drug possession', 'marijuana', 'weed', 'cannabis'),
    'weed possession': ('drug possession', 'marijuana', 'weed', 'cannabis'),
    'marine used cocaine': ('wrongful use of controlled substance', 'article 112a', 'drug use military'),
    'service member drug use': ('wrongful use of controlled substance', 'article 112a', 'drug use military'),
    'introduced drugs on base': ('article 112a', 'introduced drugs on base'),
    'high on duty': ('drunk on duty', 'incapacitated for duty', 'article 112'),
}


def _normalize(value: str) -> str:
    text = (value or '').lower().replace('-', ' ').replace('/', ' ')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    for short, expanded in SHORTHAND_MAP.items():
        text = re.sub(rf'\b{re.escape(short)}\b', expanded, text)
    return ' '.join(text.split())


def _correct_misspellings(value: str) -> str:
    text = (value or '').strip().lower()
    if not text:
        return text
    for wrong, correct in MISSPELLING_MAP.items():
        text = re.sub(rf'\b{re.escape(wrong)}\b', correct, text)
    return text


def _federal_title_section(citation: str) -> tuple[str, str]:
    raw = (citation or '').upper()
    match = re.search(r'(\d+)\s*U\.?\s*S\.?\s*C\.?\s*(?:§\s*)?([0-9A-Z().\-]+)', raw)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r'^(\d+)\s+USC\s+([0-9A-Z().\-]+)$', raw)
    if match:
        return match.group(1), match.group(2)
    return '', ''


def _source_label(source: str) -> str:
    return {
        'GEORGIA': 'Georgia Code',
        'UCMJ': 'UCMJ / Manual for Courts-Martial',
        'BASE_ORDER': 'MCLB Albany Base Orders',
        'FEDERAL_USC': 'United States Code',
    }.get((source or '').upper(), source or 'Unknown')


def _stem(term: str) -> str:
    token = (term or '').strip().lower()
    if len(token) <= 4:
        return token
    for suffix in ('ing', 'edly', 'ed', 'ly', 'es', 's'):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[:-len(suffix)]
    return token


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = _normalize(value)
    raw_tokens = re.findall(r'[a-z0-9]+', normalized)
    output: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        if token in STOPWORDS:
            continue
        if token.isdigit():
            continue
        stemmed = _stem(token)
        if not stemmed or stemmed in STOPWORDS:
            continue
        if stemmed not in seen:
            output.append(stemmed)
            seen.add(stemmed)
    return tuple(output)


def _query_intents(query: str) -> set[str]:
    q = _normalize(query)
    intents: set[str] = set()
    if any(token in q for token in ('dui', 'drunk', 'impaired', 'alcohol', 'traffic', 'speed', 'lane', 'stop sign', 'red light', 'vehicle')):
        intents.add('traffic')
    if any(token in q for token in ('drug', 'narcotic', 'marijuana', 'weed', 'meth', 'cocaine', 'fentanyl', 'pill', 'prescription')):
        intents.add('drug')
    if any(token in q for token in ('assault', 'battery', 'pushed', 'slapped', 'hit', 'fight', 'struck', 'choked')):
        intents.add('assault')
    if any(token in q for token in ('domestic', 'spouse', 'wife', 'husband', 'boyfriend', 'girlfriend', 'dating partner', 'family violence')):
        intents.add('domestic')
    if any(token in q for token in ('trespass', 'entered', 'broke into', 'burglary', 'unlawful entry')):
        intents.add('entry')
    if any(token in q for token in ('theft', 'stole', 'shoplift', 'robbery', 'wallet', 'property taken')):
        intents.add('theft')
    if any(token in q for token in ('threat', 'harass', 'text message', 'stalking', 'terroristic', 'protective order')):
        intents.add('threat')
    if any(token in q for token in ('order', 'lawful command', 'refused command', 'awol', 'barracks', 'marine', 'service member', 'ucmj')):
        intents.add('military')
    if any(token in q for token in ('federal', 'usc', 'interstate', 'government property', 'federal facility', 'wire fraud', 'identity theft')):
        intents.add('federal')
    return intents


def _entry_intents(entry: LegalEntry) -> set[str]:
    text = _normalize(' '.join((
        entry.code,
        entry.title,
        entry.summary,
        entry.category,
        entry.subcategory,
        ' '.join(entry.keywords),
        ' '.join(entry.aliases),
        ' '.join(entry.narrative_triggers),
        ' '.join(entry.conduct_verbs),
        ' '.join(entry.traffic_context),
        ' '.join(entry.drug_context),
        ' '.join(entry.military_context),
        ' '.join(entry.federal_context),
    )))
    intents: set[str] = set()
    if any(token in text for token in ('dui', 'traffic', 'speed', 'lane', 'stop sign', 'vehicle', 'driving')):
        intents.add('traffic')
    if any(token in text for token in ('drug', 'controlled substance', 'narcotic', 'marijuana', 'meth', 'cocaine', 'prescription')):
        intents.add('drug')
    if any(token in text for token in ('assault', 'battery', 'struck', 'physical harm', 'violent injury')):
        intents.add('assault')
    if any(token in text for token in ('domestic', 'family violence', 'spouse', 'dating partner')):
        intents.add('domestic')
    if any(token in text for token in ('trespass', 'burglary', 'entry', 'entered', 'without authority')):
        intents.add('entry')
    if any(token in text for token in ('theft', 'shoplifting', 'robbery', 'larceny', 'stolen')):
        intents.add('theft')
    if any(token in text for token in ('threat', 'harass', 'stalking', 'terroristic', 'protective order')):
        intents.add('threat')
    if entry.source == 'UCMJ' or any(token in text for token in ('article', 'lawful order', 'command', 'awol', 'barracks', 'service member')):
        intents.add('military')
    if entry.source == 'FEDERAL_USC' or any(token in text for token in ('usc', 'interstate', 'federal', 'government property', 'federal facility')):
        intents.add('federal')
    return intents


def _source_relevance_boost(source: str, intents: set[str]) -> int:
    if not intents:
        return 0
    src = (source or '').upper()
    boost = 0
    if src == 'GEORGIA':
        if intents & {'traffic', 'drug', 'assault', 'domestic', 'theft', 'entry', 'threat'}:
            boost += 5
        if intents & {'federal', 'military'} and 'traffic' not in intents:
            boost -= 6
    elif src == 'UCMJ':
        if intents & {'military', 'assault', 'domestic', 'drug', 'threat'}:
            boost += 6
        if 'traffic' in intents:
            boost -= 2
    elif src == 'FEDERAL_USC':
        if intents & {'federal', 'threat', 'theft', 'drug'}:
            boost += 6
        if intents & {'federal', 'entry'}:
            boost += 10
        if intents & {'military', 'federal'}:
            boost += 8
        if intents & {'traffic'}:
            boost -= 3
    elif src == 'BASE_ORDER':
        if intents & {'military', 'traffic'}:
            boost += 5
        if intents & {'federal', 'entry'} and 'traffic' not in intents:
            boost -= 8
    return boost


def _ensure_legal_data_dir() -> None:
    LEGAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _entry_from_mapping(raw: dict, fallback_source: str) -> LegalEntry | None:
    if not isinstance(raw, dict):
        return None
    code = str(raw.get('code') or '').strip()
    title = str(raw.get('title') or '').strip()
    summary = str(raw.get('summary') or '').strip()
    if not (code and title and summary):
        return None
    source = str(raw.get('source') or fallback_source or 'ALL').strip().upper()
    if code.upper().startswith('MCLBAO'):
        source = 'BASE_ORDER'
    elif code.upper().startswith('ARTICLE '):
        source = 'UCMJ'
    elif re.match(r'^\d+\s*USC\b', code.upper()) or ' USC ' in code.upper():
        source = 'FEDERAL_USC'
    elif code.upper().startswith('OCGA '):
        source = 'GEORGIA'
    if source not in {'GEORGIA', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'}:
        source = fallback_source
    source_type = str(raw.get('source_type') or '').strip().lower()
    if not source_type:
        source_type = {
            'GEORGIA': 'georgia',
            'UCMJ': 'ucmj',
            'BASE_ORDER': 'base_order',
            'FEDERAL_USC': 'federal',
        }.get(source, source.lower())
    citation = str(raw.get('citation') or code).strip()
    title_number, section_number = _federal_title_section(citation if source == 'FEDERAL_USC' else '')
    elements_value = raw.get('elements') or ()
    keywords_value = raw.get('keywords') or ()
    related_codes_value = raw.get('related_codes') or ()
    if isinstance(elements_value, str):
        elements = tuple(item.strip() for item in elements_value.split('|') if item.strip())
    else:
        elements = tuple(str(item).strip() for item in elements_value if str(item).strip())
    if not elements:
        return None
    if isinstance(keywords_value, str):
        keywords = tuple(item.strip() for item in keywords_value.split('|') if item.strip())
    else:
        keywords = tuple(str(item).strip() for item in keywords_value if str(item).strip())
    if isinstance(related_codes_value, str):
        related_codes = tuple(item.strip() for item in related_codes_value.split('|') if item.strip())
    else:
        related_codes = tuple(str(item).strip() for item in related_codes_value if str(item).strip())
    def _to_tuple(value):
        if isinstance(value, str):
            return tuple(item.strip() for item in re.split(r'[|;,]', value) if item.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

    def _to_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    return _with_punishment_defaults(LegalEntry(
        record_id=str(raw.get('record_id') or raw.get('offense_id') or code).strip() or code,
        jurisdiction_type=str(raw.get('jurisdiction_type') or source).strip() or source,
        source=source,
        code=code,
        title=title,
        summary=summary,
        elements=elements,
        source_group=str(raw.get('source_group') or _source_label(source)).strip(),
        short_title=str(raw.get('short_title') or title).strip(),
        plain_language_summary=str(raw.get('plain_language_summary') or summary).strip(),
        required_elements=_to_tuple(raw.get('required_elements')) or elements,
        scenario_triggers=_to_tuple(raw.get('scenario_triggers')) or _to_tuple(raw.get('narrative_triggers')),
        penalties=str(raw.get('penalties') or '').strip(),
        related_statutes=_to_tuple(raw.get('related_statutes')) or related_codes,
        related_orders=_to_tuple(raw.get('related_orders')),
        enforcement_notes=str(raw.get('enforcement_notes') or raw.get('officer_notes') or '').strip(),
        notes=str(raw.get('notes') or '').strip(),
        keywords=keywords,
        related_codes=related_codes,
        minimum_punishment=str(raw.get('minimum_punishment') or '').strip(),
        maximum_punishment=str(raw.get('maximum_punishment') or '').strip(),
        offense_id=str(raw.get('offense_id') or '').strip() or code,
        source_type=source_type,
        source_label=str(raw.get('source_label') or _source_label(source)).strip(),
        citation=citation,
        title_number=str(raw.get('title_number') or title_number).strip(),
        section_number=str(raw.get('section_number') or section_number).strip(),
        chapter_number=str(raw.get('chapter_number') or '').strip(),
        article_number=str(raw.get('article_number') or '').strip(),
        category=str(raw.get('category') or '').strip(),
        subcategory=str(raw.get('subcategory') or '').strip(),
        severity=str(raw.get('severity') or '').strip(),
        aliases=_to_tuple(raw.get('aliases')),
        synonyms=_to_tuple(raw.get('synonyms')),
        narrative_triggers=_to_tuple(raw.get('narrative_triggers')),
        conduct_verbs=_to_tuple(raw.get('conduct_verbs')),
        victim_context=_to_tuple(raw.get('victim_context')),
        property_context=_to_tuple(raw.get('property_context')),
        injury_context=_to_tuple(raw.get('injury_context')),
        relationship_context=_to_tuple(raw.get('relationship_context')),
        location_context=_to_tuple(raw.get('location_context')),
        federal_context=_to_tuple(raw.get('federal_context')),
        military_context=_to_tuple(raw.get('military_context')),
        traffic_context=_to_tuple(raw.get('traffic_context')),
        juvenile_context=_to_tuple(raw.get('juvenile_context')),
        drug_context=_to_tuple(raw.get('drug_context')),
        lesser_included_offenses=_to_tuple(raw.get('lesser_included_offenses')),
        alternative_offenses=_to_tuple(raw.get('alternative_offenses')),
        overlap_notes=_to_tuple(raw.get('overlap_notes')),
        officer_notes=str(raw.get('officer_notes') or '').strip(),
        jurisdiction_conditions=_to_tuple(raw.get('jurisdiction_conditions')),
        examples=_to_tuple(raw.get('examples')),
        active_flag=bool(raw.get('active_flag', True)),
        source_version=str(raw.get('source_version') or '').strip(),
        source_reference_url=str(raw.get('source_reference_url') or '').strip(),
        source_reference=str(raw.get('source_reference') or '').strip(),
        source_file_name=str(raw.get('source_file_name') or '').strip(),
        source_document_path=str(raw.get('source_document_path') or '').strip(),
        source_page_reference=str(raw.get('source_page_reference') or '').strip(),
        official_text=str(raw.get('official_text') or '').strip(),
        official_citation=str(raw.get('official_citation') or citation).strip(),
        official_punishment_text=str(raw.get('official_punishment_text') or '').strip(),
        official_text_available=bool(raw.get('official_text_available', bool(raw.get('official_text')))),
        derived_summary=str(raw.get('derived_summary') or '').strip(),
        derived_aliases=_to_tuple(raw.get('derived_aliases')),
        derived_synonyms=_to_tuple(raw.get('derived_synonyms')),
        derived_examples=_to_tuple(raw.get('derived_examples')),
        derived_triggers=_to_tuple(raw.get('derived_triggers')),
        citation_requires_verification=bool(raw.get('citation_requires_verification', False)),
        parser_confidence=_to_float(raw.get('parser_confidence'), 0.0),
        enrichment_confidence=_to_float(raw.get('enrichment_confidence'), 0.0),
        last_updated=str(raw.get('last_updated') or '').strip(),
        enrichment_derived=bool(raw.get('enrichment_derived', False)),
    ))


def _serialize_entry(entry: LegalEntry) -> dict:
    payload = asdict(entry)
    payload['elements'] = list(entry.elements)
    payload['required_elements'] = list(entry.required_elements)
    payload['scenario_triggers'] = list(entry.scenario_triggers)
    payload['keywords'] = list(entry.keywords)
    payload['related_codes'] = list(entry.related_codes)
    payload['related_statutes'] = list(entry.related_statutes)
    payload['related_orders'] = list(entry.related_orders)
    return payload


def _read_corpus_file(path: Path, fallback_source: str) -> tuple[LegalEntry, ...]:
    if not path.exists():
        return ()
    try:
        raw_payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return ()
    if isinstance(raw_payload, dict):
        entries_raw = raw_payload.get('entries') or raw_payload.get('results') or ()
    elif isinstance(raw_payload, list):
        entries_raw = raw_payload
    else:
        entries_raw = ()
    entries: list[LegalEntry] = []
    seen_codes: set[str] = set()
    for raw_entry in entries_raw:
        entry = _entry_from_mapping(raw_entry, fallback_source)
        if not entry:
            continue
        if entry.code in seen_codes:
            continue
        seen_codes.add(entry.code)
        entries.append(entry)
    return tuple(entries)


def _path_mtime(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _refresh_corpus_cache() -> None:
    _ensure_legal_data_dir()
    georgia_mtime = _path_mtime(GEORGIA_CORPUS_PATH)
    ucmj_mtime = _path_mtime(UCMJ_CORPUS_PATH)
    base_order_mtime = _path_mtime(BASE_ORDER_CORPUS_PATH)
    federal_usc_mtime = _path_mtime(FEDERAL_USC_CORPUS_PATH)
    if georgia_mtime != _CORPUS_CACHE['georgia_mtime']:
        loaded = _read_corpus_file(GEORGIA_CORPUS_PATH, 'GEORGIA')
        _CORPUS_CACHE['georgia_entries'] = loaded or GEORGIA_CODES
        _CORPUS_CACHE['georgia_mtime'] = georgia_mtime
    if ucmj_mtime != _CORPUS_CACHE['ucmj_mtime']:
        loaded = _read_corpus_file(UCMJ_CORPUS_PATH, 'UCMJ')
        _CORPUS_CACHE['ucmj_entries'] = loaded or UCMJ_ARTICLES
        _CORPUS_CACHE['ucmj_mtime'] = ucmj_mtime
    if base_order_mtime != _CORPUS_CACHE['base_order_mtime']:
        loaded = _read_corpus_file(BASE_ORDER_CORPUS_PATH, 'BASE_ORDER')
        _CORPUS_CACHE['base_order_entries'] = loaded or tuple(item for item in GEORGIA_CODES if str(item.code).startswith('MCLBAO'))
        _CORPUS_CACHE['base_order_mtime'] = base_order_mtime
    if federal_usc_mtime != _CORPUS_CACHE['federal_usc_mtime']:
        loaded = _read_corpus_file(FEDERAL_USC_CORPUS_PATH, 'FEDERAL_USC')
        merged: dict[str, LegalEntry] = {}
        for entry in FEDERAL_USC_CODES:
            merged[entry.code] = entry
        for entry in loaded:
            merged[entry.code] = entry
        _CORPUS_CACHE['federal_usc_entries'] = tuple(merged.values())
        _CORPUS_CACHE['federal_usc_mtime'] = federal_usc_mtime


def get_entries(source: str = 'ALL') -> tuple[LegalEntry, ...]:
    _refresh_corpus_cache()
    source = (source or 'ALL').upper()
    if source == 'GEORGIA':
        return tuple(_with_punishment_defaults(item) for item in _CORPUS_CACHE['georgia_entries'])
    if source == 'UCMJ':
        return tuple(_with_punishment_defaults(item) for item in _CORPUS_CACHE['ucmj_entries'])
    if source == 'BASE_ORDER':
        return tuple(_with_punishment_defaults(item) for item in _CORPUS_CACHE['base_order_entries'])
    if source == 'FEDERAL_USC':
        return tuple(_with_punishment_defaults(item) for item in _CORPUS_CACHE['federal_usc_entries'])

    combined = (
        list(_CORPUS_CACHE['georgia_entries'])
        + list(_CORPUS_CACHE['ucmj_entries'])
        + list(_CORPUS_CACHE['base_order_entries'])
        + list(_CORPUS_CACHE['federal_usc_entries'])
    )
    deduped: dict[str, LegalEntry] = {}
    for entry in combined:
        deduped.setdefault(entry.code, entry)
    return tuple(_with_punishment_defaults(item) for item in deduped.values())


def get_entry(source: str, code: str) -> LegalEntry | None:
    source = (source or 'ALL').upper()
    target_code = (code or '').strip().lower()
    if not target_code:
        return None
    for entry in get_entries(source):
        if entry.code.strip().lower() == target_code:
            return entry
    return None


def _source_file_candidates(entry: LegalEntry) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for raw in (entry.source_document_path, entry.source_file_name):
        value = (raw or '').strip()
        if not value:
            continue
        direct = Path(value)
        if direct.is_file():
            candidates.append(direct)
            continue
        for root in (
            LEGAL_DATA_DIR,
            LEGAL_DATA_DIR.parent / 'uploads',
            LEGAL_DATA_DIR.parent / 'uploads' / 'orders',
            LEGAL_DATA_DIR.parent / 'uploads' / 'orders' / 'official',
        ):
            candidate = root / value
            if candidate.is_file():
                candidates.append(candidate)
    deduped: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        resolved = str(item.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(item)
    return tuple(deduped)


def reference_download_info(entry: LegalEntry) -> dict:
    files = _source_file_candidates(entry)
    if files:
        return {
            'available': True,
            'mode': 'file',
            'label': 'Download Reference',
            'file_name': files[0].name,
            'mime': '',
        }
    if (entry.official_text or entry.summary).strip():
        safe_stem = re.sub(r'[^A-Za-z0-9._-]+', '-', (entry.code or entry.title or 'reference')).strip('-') or 'reference'
        return {
            'available': True,
            'mode': 'generated_text',
            'label': 'Download Reference',
            'file_name': f'{safe_stem}.txt',
            'mime': 'text/plain',
        }
    return {
        'available': False,
        'mode': 'none',
        'label': 'Download not available',
        'file_name': '',
        'mime': '',
    }


def _coverage_metrics(entries: tuple[LegalEntry, ...]) -> dict:
    total = len(entries)
    if not total:
        return {
            'total': 0,
            'with_citation': 0,
            'missing_elements': 0,
            'missing_punishment': 0,
            'missing_aliases': 0,
            'missing_examples': 0,
            'missing_official_text': 0,
            'citation_verification_required': 0,
            'low_parser_confidence': 0,
            'low_enrichment_confidence': 0,
            'inactive': 0,
            'not_indexed_estimate': 0,
        }
    return {
        'total': total,
        'with_citation': sum(1 for e in entries if (e.citation or e.code).strip()),
        'missing_elements': sum(1 for e in entries if not e.elements),
        'missing_punishment': sum(1 for e in entries if not ((e.minimum_punishment or '').strip() and (e.maximum_punishment or '').strip())),
        'missing_aliases': sum(1 for e in entries if not (e.aliases or e.derived_aliases or e.synonyms or e.derived_synonyms)),
        'missing_examples': sum(1 for e in entries if not (e.examples or e.derived_examples)),
        'missing_official_text': sum(1 for e in entries if not e.official_text_available),
        'citation_verification_required': sum(1 for e in entries if e.citation_requires_verification),
        'low_parser_confidence': sum(1 for e in entries if 0 < e.parser_confidence < 0.55),
        'low_enrichment_confidence': sum(1 for e in entries if 0 < e.enrichment_confidence < 0.55),
        'inactive': sum(1 for e in entries if not e.active_flag),
        'not_indexed_estimate': sum(1 for e in entries if (not e.active_flag) or e.citation_requires_verification),
    }


def corpus_status() -> dict:
    georgia_entries = get_entries('GEORGIA')
    ucmj_entries = get_entries('UCMJ')
    base_order_entries = get_entries('BASE_ORDER')
    federal_usc_entries = get_entries('FEDERAL_USC')
    georgia_cov = _coverage_metrics(georgia_entries)
    ucmj_cov = _coverage_metrics(ucmj_entries)
    base_cov = _coverage_metrics(base_order_entries)
    federal_cov = _coverage_metrics(federal_usc_entries)
    coverage_warnings: list[str] = []
    if not GEORGIA_CORPUS_PATH.exists() or georgia_cov['total'] < 50:
        coverage_warnings.append('Georgia source coverage incomplete.')
    if not UCMJ_CORPUS_PATH.exists() or ucmj_cov['total'] < 15:
        coverage_warnings.append('UCMJ source coverage incomplete.')
    if not FEDERAL_USC_CORPUS_PATH.exists() or federal_cov['total'] < 20:
        coverage_warnings.append('Federal source coverage incomplete.')
    if not BASE_ORDER_CORPUS_PATH.exists() or base_cov['total'] == 0:
        coverage_warnings.append('MCLB Albany order source not yet loaded.')
    return {
        'directory': str(LEGAL_DATA_DIR),
        'georgia_file': str(GEORGIA_CORPUS_PATH),
        'ucmj_file': str(UCMJ_CORPUS_PATH),
        'base_order_file': str(BASE_ORDER_CORPUS_PATH),
        'federal_usc_file': str(FEDERAL_USC_CORPUS_PATH),
        'georgia_count': len(georgia_entries),
        'ucmj_count': len(ucmj_entries),
        'base_order_count': len(base_order_entries),
        'federal_usc_count': len(federal_usc_entries),
        'has_georgia_file': GEORGIA_CORPUS_PATH.exists(),
        'has_ucmj_file': UCMJ_CORPUS_PATH.exists(),
        'has_base_order_file': BASE_ORDER_CORPUS_PATH.exists(),
        'has_federal_usc_file': FEDERAL_USC_CORPUS_PATH.exists(),
        'using_builtin_georgia': not GEORGIA_CORPUS_PATH.exists(),
        'using_builtin_ucmj': not UCMJ_CORPUS_PATH.exists(),
        'using_builtin_base_order': not BASE_ORDER_CORPUS_PATH.exists(),
        'using_builtin_federal_usc': not FEDERAL_USC_CORPUS_PATH.exists(),
        'coverage': {
            'GEORGIA': georgia_cov,
            'UCMJ': ucmj_cov,
            'BASE_ORDER': base_cov,
            'FEDERAL_USC': federal_cov,
        },
        'coverage_warnings': coverage_warnings,
    }


def export_corpus_payload(source: str = 'ALL') -> dict:
    source = (source or 'ALL').upper()
    if source == 'GEORGIA':
        return {'source': 'GEORGIA', 'entries': [_serialize_entry(item) for item in get_entries('GEORGIA')]}
    if source == 'UCMJ':
        return {'source': 'UCMJ', 'entries': [_serialize_entry(item) for item in get_entries('UCMJ')]}
    if source == 'BASE_ORDER':
        return {'source': 'BASE_ORDER', 'entries': [_serialize_entry(item) for item in get_entries('BASE_ORDER')]}
    if source == 'FEDERAL_USC':
        return {'source': 'FEDERAL_USC', 'entries': [_serialize_entry(item) for item in get_entries('FEDERAL_USC')]}
    return {
        'source': 'ALL',
        'georgia_codes': [_serialize_entry(item) for item in get_entries('GEORGIA')],
        'ucmj_articles': [_serialize_entry(item) for item in get_entries('UCMJ')],
        'base_orders': [_serialize_entry(item) for item in get_entries('BASE_ORDER')],
        'federal_usc_codes': [_serialize_entry(item) for item in get_entries('FEDERAL_USC')],
    }


def import_corpus_payload(payload: dict | list, source: str = 'ALL') -> dict:
    _ensure_legal_data_dir()
    source = (source or 'ALL').upper()
    written: dict[str, int] = {'GEORGIA': 0, 'UCMJ': 0, 'BASE_ORDER': 0, 'FEDERAL_USC': 0}
    if source == 'ALL':
        if isinstance(payload, dict):
            georgia_raw = payload.get('georgia_codes') or payload.get('georgia_entries') or payload.get('georgia') or ()
            ucmj_raw = payload.get('ucmj_articles') or payload.get('ucmj_entries') or payload.get('ucmj') or ()
            base_order_raw = payload.get('base_orders') or payload.get('base_order_entries') or payload.get('base_order') or ()
            federal_usc_raw = payload.get('federal_usc_codes') or payload.get('federal_usc_entries') or payload.get('federal_usc') or ()
        else:
            georgia_raw = ()
            ucmj_raw = ()
            base_order_raw = ()
            federal_usc_raw = ()
    elif source == 'GEORGIA':
        georgia_raw = payload if isinstance(payload, list) else payload.get('entries') or payload.get('results') or ()
        ucmj_raw = ()
        base_order_raw = ()
    elif source == 'BASE_ORDER':
        georgia_raw = ()
        ucmj_raw = ()
        base_order_raw = payload if isinstance(payload, list) else payload.get('entries') or payload.get('results') or ()
        federal_usc_raw = ()
    elif source == 'FEDERAL_USC':
        georgia_raw = ()
        ucmj_raw = ()
        base_order_raw = ()
        federal_usc_raw = payload if isinstance(payload, list) else payload.get('entries') or payload.get('results') or ()
    else:
        georgia_raw = ()
        ucmj_raw = payload if isinstance(payload, list) else payload.get('entries') or payload.get('results') or ()
        base_order_raw = ()
        federal_usc_raw = ()

    if georgia_raw:
        georgia_entries = [_serialize_entry(entry) for entry in (_entry_from_mapping(item, 'GEORGIA') for item in georgia_raw) if entry]
        if georgia_entries:
            GEORGIA_CORPUS_PATH.write_text(json.dumps({'source': 'GEORGIA', 'entries': georgia_entries}, indent=2), encoding='utf-8')
            written['GEORGIA'] = len(georgia_entries)
    if ucmj_raw:
        ucmj_entries = [_serialize_entry(entry) for entry in (_entry_from_mapping(item, 'UCMJ') for item in ucmj_raw) if entry]
        if ucmj_entries:
            UCMJ_CORPUS_PATH.write_text(json.dumps({'source': 'UCMJ', 'entries': ucmj_entries}, indent=2), encoding='utf-8')
            written['UCMJ'] = len(ucmj_entries)
    if base_order_raw:
        base_order_entries = [_serialize_entry(entry) for entry in (_entry_from_mapping(item, 'BASE_ORDER') for item in base_order_raw) if entry]
        if base_order_entries:
            BASE_ORDER_CORPUS_PATH.write_text(json.dumps({'source': 'BASE_ORDER', 'entries': base_order_entries}, indent=2), encoding='utf-8')
            written['BASE_ORDER'] = len(base_order_entries)
    if federal_usc_raw:
        federal_usc_entries = [_serialize_entry(entry) for entry in (_entry_from_mapping(item, 'FEDERAL_USC') for item in federal_usc_raw) if entry]
        if federal_usc_entries:
            FEDERAL_USC_CORPUS_PATH.write_text(json.dumps({'source': 'FEDERAL_USC', 'entries': federal_usc_entries}, indent=2), encoding='utf-8')
            written['FEDERAL_USC'] = len(federal_usc_entries)

    _CORPUS_CACHE['georgia_mtime'] = None
    _CORPUS_CACHE['ucmj_mtime'] = None
    _CORPUS_CACHE['base_order_mtime'] = None
    _CORPUS_CACHE['federal_usc_mtime'] = None
    _refresh_corpus_cache()
    return {
        'georgia_written': written['GEORGIA'],
        'ucmj_written': written['UCMJ'],
        'base_order_written': written['BASE_ORDER'],
        'federal_usc_written': written['FEDERAL_USC'],
        'status': corpus_status(),
    }


def reindex_corpus() -> dict:
    _CORPUS_CACHE['georgia_mtime'] = None
    _CORPUS_CACHE['ucmj_mtime'] = None
    _CORPUS_CACHE['base_order_mtime'] = None
    _CORPUS_CACHE['federal_usc_mtime'] = None
    _refresh_corpus_cache()
    return corpus_status()


SEARCH_FIELD_WEIGHTS = {
    'code': 28,
    'title': 20,
    'summary': 12,
    'elements': 11,
    'keywords': 17,
    'aliases': 16,
    'synonyms': 13,
    'narrative_triggers': 16,
    'examples': 14,
    'context': 10,
    'category': 8,
    'official_text': 8,
}


CONCEPT_TERMS = {
    'traffic': ('traffic', 'vehicle', 'driving', 'speed', 'lane', 'signal', 'dui', 'crash', 'accident', 'roadway'),
    'trespass': ('trespass', 'unlawful entry', 'unauthorized entry', 'without permission', 'without authority', 'refused to leave'),
    'federal_installation': ('federal installation', 'military installation', 'barred from base', 'barred from installation', 'restricted area', 'debarred', 'barment'),
    'restricted_area': ('restricted area', 'secure area', 'installation gate', 'without permission', 'suspicious person in restricted area'),
    'lawful_order': ('lawful order', 'lawful command', 'direct order', 'disobeyed', 'refused command', 'failure to obey'),
    'controlled_substance': ('drug', 'drugs', 'controlled substance', 'narcotic', 'marijuana', 'weed', 'cannabis', 'cocaine', 'meth', 'fentanyl', 'pill', 'prescription'),
    'domestic_violence': ('domestic', 'family violence', 'spouse', 'wife', 'husband', 'boyfriend', 'girlfriend', 'dating partner'),
    'false_identity': ('false name', 'fake id', 'false identification', 'fraudulent identification', 'identity document', 'gave false name'),
    'threats': ('threat', 'threatened', 'threatening', 'harassing', 'stalking', 'terroristic', 'text message', 'by text'),
    'government_property': ('government property', 'federal property', 'military property', 'stole government property', 'damaged government property'),
    'weapons': ('weapon', 'weapons', 'firearm', 'gun', 'knife', 'felon in possession', 'prohibited person'),
    'property_crime': ('theft', 'stole', 'stolen', 'shoplifting', 'burglary', 'robbery', 'larceny', 'property'),
    'violent_contact': ('assault', 'battery', 'pushed', 'slapped', 'grabbed', 'hit', 'struck', 'fight', 'fighting'),
    'military_status': ('marine', 'service member', 'barracks', 'on duty', 'military', 'ucmj'),
}


CONCEPT_EXPANSIONS = {
    'traffic': ('traffic offense', 'vehicle offense', 'roadway violation'),
    'trespass': ('trespass', 'unlawful entry', 'unauthorized entry', 'refused to leave'),
    'federal_installation': ('military installation', 'federal property', 'barred from installation', 'reentry after removal', 'restricted area'),
    'restricted_area': ('restricted area', 'secure area', 'installation gate', 'without permission'),
    'lawful_order': ('lawful order', 'direct order', 'disobeyed order', 'refused lawful order'),
    'controlled_substance': ('drug possession', 'drug distribution', 'controlled substance', 'narcotics'),
    'domestic_violence': ('domestic violence', 'family violence', 'intimate partner violence'),
    'false_identity': ('false identification', 'fraudulent identification', 'identity document offense'),
    'threats': ('threat by text', 'harassing messages', 'terroristic threats'),
    'government_property': ('government property', 'federal property', 'public property offense'),
    'weapons': ('firearm offense', 'weapon possession', 'prohibited person firearm'),
    'property_crime': ('theft offense', 'stolen property', 'shoplifting', 'burglary'),
    'violent_contact': ('assault', 'battery', 'offensive contact', 'physical altercation'),
    'military_status': ('service member misconduct', 'military offense', 'barracks incident'),
}


SOURCE_HINT_TERMS = {
    'GEORGIA': ('ocga', 'georgia', 'state law', 'traffic', 'roadway'),
    'UCMJ': ('article', 'ucmj', 'marine', 'service member', 'lawful order', 'barracks', 'on duty'),
    'BASE_ORDER': ('mclb', 'base order', 'installation', 'gate', 'post order', 'on base'),
    'FEDERAL_USC': ('usc', 'federal', 'interstate', 'government property', 'federal facility', 'military installation'),
}


SOURCE_DISPLAY_LABELS = {
    'GEORGIA': 'Georgia Code',
    'UCMJ': 'UCMJ',
    'BASE_ORDER': 'Base Orders',
    'FEDERAL_USC': 'United States Code',
}


def _ordered_unique(values):
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or '').strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _phrase_windows(tokens: tuple[str, ...], min_size: int = 2, max_size: int = 4) -> tuple[str, ...]:
    phrases: list[str] = []
    for size in range(min_size, min(max_size, len(tokens)) + 1):
        for start in range(0, len(tokens) - size + 1):
            phrase = ' '.join(tokens[start:start + size]).strip()
            if phrase and phrase not in STOPWORDS:
                phrases.append(phrase)
    return _ordered_unique(phrases)


def _context_tokens(text: str) -> tuple[str, ...]:
    return _ordered_unique(
        token
        for token in _tokenize(text)
        if token not in AMBIGUOUS_TERMS and len(token) >= 4
    )


def _detect_concepts(normalized_text: str, tokens: tuple[str, ...]) -> tuple[str, ...]:
    text = normalized_text or ''
    token_set = set(tokens)
    concepts: list[str] = []
    for concept, triggers in CONCEPT_TERMS.items():
        if any(_normalize(trigger) in text for trigger in triggers):
            concepts.append(concept)
            continue
        normalized_triggers = {_stem(part) for trigger in triggers for part in _tokenize(trigger)}
        if normalized_triggers & token_set:
            concepts.append(concept)
    return _ordered_unique(concepts)


def _query_source_hints(normalized_query: str, source: str, concepts: tuple[str, ...]) -> tuple[str, ...]:
    hints: list[str] = []
    if source in {'GEORGIA', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'}:
        hints.append(source)
    hints.extend(_scenario_signals(normalized_query))
    for hint, triggers in SOURCE_HINT_TERMS.items():
        if any(_normalize(trigger) in normalized_query for trigger in triggers):
            hints.append(hint)
    concept_set = set(concepts)
    if 'federal_installation' in concept_set or 'government_property' in concept_set:
        hints.extend(('FEDERAL_USC', 'BASE_ORDER'))
    if 'lawful_order' in concept_set or 'military_status' in concept_set:
        hints.append('UCMJ')
    if 'traffic' in concept_set:
        hints.append('GEORGIA')
    if 'domestic_violence' in concept_set:
        hints.extend(('GEORGIA', 'UCMJ'))
    return _ordered_unique(hints)


def _analyze_query(query: str, source: str = 'ALL', stage: str = 'primary') -> QueryAnalysis:
    corrected_query = _correct_misspellings(query)
    normalized_query = _normalize(corrected_query)
    tokens = _ordered_unique(_tokenize(normalized_query))
    base_phrases = list(_phrase_windows(tokens))
    base_phrases.extend(_expand_phrase_aliases(normalized_query))
    clauses = _split_query_clauses(corrected_query)
    clause_tokens = [_tokenize(_normalize(clause)) for clause in clauses]
    concept_tags = list(_detect_concepts(normalized_query, tokens))
    intents = list(_query_intents(normalized_query))
    expanded_terms = list(_expand_terms(list(tokens) + [token for clause in clause_tokens for token in clause]))
    expanded_phrases = list(base_phrases)
    for concept in concept_tags:
        for item in CONCEPT_EXPANSIONS.get(concept, ()):
            normalized_item = _normalize(item)
            if ' ' in normalized_item:
                expanded_phrases.append(normalized_item)
            else:
                expanded_terms.append(normalized_item)
    if stage != 'primary':
        for clause in clauses:
            normalized_clause = _normalize(clause)
            if normalized_clause:
                expanded_phrases.append(normalized_clause)
        for concept in concept_tags:
            expanded_terms.extend(_tokenize(' '.join(CONCEPT_EXPANSIONS.get(concept, ()))))
    source_hints = _query_source_hints(normalized_query, source, tuple(concept_tags))
    context_terms = _context_tokens(' '.join(expanded_terms) + ' ' + ' '.join(expanded_phrases))
    conduct_terms = _ordered_unique(
        term
        for term in context_terms
        if term in {
            'enter', 'entry', 'trespass', 'refus', 'obey', 'disobey', 'threat', 'stalk',
            'steal', 'theft', 'shoplift', 'push', 'slap', 'grab', 'struck', 'fight',
            'possess', 'distribut', 'carry', 'damag'
        }
    )
    return QueryAnalysis(
        original_query=query,
        corrected_query=corrected_query,
        normalized_query=normalized_query,
        source=source,
        tokens=tokens,
        phrases=_ordered_unique(base_phrases),
        expanded_terms=_ordered_unique(expanded_terms),
        expanded_phrases=_ordered_unique(expanded_phrases),
        concept_tags=_ordered_unique(concept_tags),
        source_hints=source_hints,
        context_terms=_ordered_unique(context_terms),
        conduct_terms=conduct_terms,
        clauses=_ordered_unique(_normalize(clause) for clause in clauses),
        intents=_ordered_unique(intents),
        article_number=_article_number(normalized_query),
        ocga_code=_ocga_code_token(corrected_query),
        ocga_prefix=_ocga_prefix_token(corrected_query),
        stage=stage,
    )


def _profile_source_hints(entry: LegalEntry, normalized_blob: str) -> frozenset[str]:
    hints = [entry.source]
    for hint, triggers in SOURCE_HINT_TERMS.items():
        if hint == entry.source:
            hints.append(hint)
        if any(_normalize(trigger) in normalized_blob for trigger in triggers):
            hints.append(hint)
    if entry.source == 'FEDERAL_USC' and ('installation' in normalized_blob or 'federal property' in normalized_blob):
        hints.append('BASE_ORDER')
    if entry.source == 'BASE_ORDER' and ('traffic' in normalized_blob or 'installation' in normalized_blob):
        hints.append('GEORGIA')
    return frozenset(_ordered_unique(hints))


@lru_cache(maxsize=4096)
def _build_entry_profile(entry: LegalEntry) -> SearchEntryProfile:
    field_texts = {
        'code': _normalize(entry.code),
        'title': _normalize(entry.title),
        'summary': _normalize(' '.join((
            entry.summary,
            entry.plain_language_summary,
            entry.derived_summary,
            entry.notes,
            entry.enforcement_notes,
            entry.officer_notes,
        ))),
        'elements': _normalize(' '.join(entry.required_elements or entry.elements)),
        'keywords': _normalize(' '.join(entry.keywords)),
        'aliases': _normalize(' '.join(entry.aliases + entry.derived_aliases)),
        'synonyms': _normalize(' '.join(entry.synonyms + entry.derived_synonyms)),
        'narrative_triggers': _normalize(' '.join(entry.narrative_triggers + entry.scenario_triggers + entry.derived_triggers)),
        'examples': _normalize(' '.join(entry.examples + entry.derived_examples)),
        'context': _normalize(' '.join(
            entry.conduct_verbs
            + entry.victim_context
            + entry.property_context
            + entry.injury_context
            + entry.relationship_context
            + entry.location_context
            + entry.federal_context
            + entry.military_context
            + entry.traffic_context
            + entry.juvenile_context
            + entry.drug_context
            + entry.jurisdiction_conditions
        )),
        'category': _normalize(' '.join((entry.category, entry.subcategory, entry.source_label, entry.source_group))),
        'official_text': _normalize(' '.join((entry.official_text, entry.official_citation, entry.official_punishment_text))),
    }
    field_tokens = {name: frozenset(_tokenize(text)) for name, text in field_texts.items() if text}
    all_tokens = frozenset(token for values in field_tokens.values() for token in values)
    phrase_inventory = frozenset(
        _ordered_unique(
            list(_phrase_windows(tuple(all_tokens)))
            + [value for value in field_texts.values() if 8 <= len(value.split()) <= 18]
            + list(_phrase_windows(tuple(_tokenize(field_texts.get('title', '')))))
            + list(_phrase_windows(tuple(_tokenize(field_texts.get('keywords', '')))))
            + list(_phrase_windows(tuple(_tokenize(field_texts.get('aliases', '')))))
        )
    )
    normalized_blob = ' '.join(field_texts.values())
    concept_tags = frozenset(_detect_concepts(normalized_blob, tuple(all_tokens)))
    source_quality = 1.0
    if entry.official_text_available:
        source_quality += 0.08
    if entry.source_reference or entry.source_reference_url:
        source_quality += 0.05
    if entry.parser_confidence:
        source_quality += min(0.08, max(0.0, entry.parser_confidence * 0.1))
    if entry.enrichment_confidence:
        source_quality += min(0.04, max(0.0, entry.enrichment_confidence * 0.05))
    if entry.citation_requires_verification:
        source_quality -= 0.06
    return SearchEntryProfile(
        entry=entry,
        field_texts=field_texts,
        field_tokens=field_tokens,
        all_tokens=all_tokens,
        phrase_inventory=phrase_inventory,
        concept_tags=concept_tags,
        source_hints=_profile_source_hints(entry, normalized_blob),
        source_quality=max(0.75, source_quality),
        intent_tags=frozenset(_entry_intents(entry)),
    )


def _fuzzy_overlap_score(query_terms: tuple[str, ...], candidate_terms: frozenset[str]) -> tuple[float, list[str]]:
    score = 0.0
    labels: list[str] = []
    for query_term in query_terms:
        if len(query_term) < 5:
            continue
        best_ratio = 0.0
        best_term = ''
        for candidate in candidate_terms:
            if abs(len(candidate) - len(query_term)) > 3:
                continue
            ratio = SequenceMatcher(None, query_term, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_term = candidate
        if best_ratio >= 0.86:
            score += 5.0
            labels.append(best_term)
    return score, labels


def _candidate_gate(profile: SearchEntryProfile, analysis: QueryAnalysis, strict_gating: bool) -> bool:
    if analysis.source != 'ALL' and profile.entry.source != analysis.source:
        return False
    if not analysis.normalized_query:
        return True
    if analysis.ocga_code and analysis.ocga_code in profile.field_texts.get('code', ''):
        return True
    if analysis.ocga_prefix and analysis.ocga_prefix in profile.field_texts.get('code', ''):
        return True
    if analysis.article_number and f'article {analysis.article_number}' in profile.field_texts.get('code', ''):
        return True
    direct_text = ' '.join(profile.field_texts.values())
    base_term_overlap = set(analysis.tokens) & profile.all_tokens
    expanded_overlap = set(analysis.expanded_terms) & profile.all_tokens
    concept_overlap = set(analysis.concept_tags) & set(profile.concept_tags)
    phrase_match = any(phrase and phrase in direct_text for phrase in analysis.phrases + analysis.expanded_phrases)
    if phrase_match or concept_overlap:
        return True
    if len(base_term_overlap) >= 2:
        return True
    if expanded_overlap and not strict_gating:
        return True
    fuzzy_score, _ = _fuzzy_overlap_score(analysis.tokens, profile.all_tokens)
    return fuzzy_score >= (5.0 if not strict_gating else 10.0)


def _full_document_relevance(profile: SearchEntryProfile, analysis: QueryAnalysis) -> tuple[float, tuple[str, ...], tuple[str, ...], float]:
    """Score the whole entry body, not just curated trigger words.

    Officers often type a full incident description. The lookup needs to read the
    statute/order body, elements, notes, examples, and official text before it
    trusts keyword hits. This keeps short keyword aliases useful without letting
    them overwhelm better full-content matches.
    """

    body_fields = (
        'summary',
        'elements',
        'context',
        'category',
        'official_text',
        'examples',
    )
    body_text = ' '.join(profile.field_texts.get(name, '') for name in body_fields if profile.field_texts.get(name))
    body_tokens = set(_tokenize(body_text))
    if not body_tokens:
        return 0.0, (), (), 0.0

    query_terms = {
        term
        for term in tuple(analysis.tokens) + tuple(analysis.context_terms) + tuple(analysis.expanded_terms)
        if len(term) >= 3 and term not in STOPWORDS and term not in AMBIGUOUS_TERMS
    }
    if not query_terms:
        return 0.0, (), (), 0.0

    overlap = query_terms & body_tokens
    coverage = len(overlap) / max(1, len(query_terms))
    score = min(34.0, coverage * 38.0)
    if overlap:
        score += min(18.0, len(overlap) * 2.5)

    phrase_hits: list[str] = []
    for phrase in analysis.phrases + analysis.expanded_phrases:
        if not phrase or len(phrase) < 6:
            continue
        if phrase in body_text:
            phrase_hits.append(phrase)
    if phrase_hits:
        score += min(24.0, 12.0 + (len(phrase_hits) * 4.0))

    official_tokens = profile.field_tokens.get('official_text', frozenset())
    official_overlap = set(analysis.tokens) & set(official_tokens)
    if official_overlap:
        score += min(14.0, 4.0 + (len(official_overlap) * 2.0))

    reasons: list[str] = []
    if coverage >= 0.34 or phrase_hits or official_overlap:
        reasons.append('reviewed full statute/order text')
    if official_overlap:
        reasons.append('matched official text')
    if phrase_hits:
        reasons.append(f"matched body phrase: {phrase_hits[0]}")

    return score, tuple(reasons), tuple(sorted(overlap | official_overlap))[:10], coverage


def _score_profile(profile: SearchEntryProfile, analysis: QueryAnalysis, strict_gating: bool) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    entry = profile.entry
    score = 0.0
    reasons: list[str] = []
    matched_terms: list[str] = []
    code_text = profile.field_texts.get('code', '')
    title_text = profile.field_texts.get('title', '')
    summary_text = profile.field_texts.get('summary', '')
    all_text = ' '.join(profile.field_texts.values())
    normalized_keywords = tuple(_normalize(item) for item in entry.keywords if item)
    normalized_aliases = tuple(_normalize(item) for item in entry.aliases if item)
    normalized_synonyms = tuple(_normalize(item) for item in entry.synonyms if item)
    normalized_triggers = tuple(_normalize(item) for item in entry.narrative_triggers if item)
    exact_keyword_match = any(analysis.normalized_query == item for item in normalized_keywords)
    exact_alias_match = any(analysis.normalized_query == item for item in normalized_aliases + normalized_synonyms + normalized_triggers)
    title_led_query = bool(
        analysis.normalized_query
        and title_text
        and analysis.normalized_query != title_text
        and title_text in analysis.normalized_query
    )
    controlled_substance_query = (
        'controlled_substance' in analysis.concept_tags
        or bool(re.search(r'\bdrug\b|\bdrugs\b|\bnarcotic\b|\bmarijuana\b|\bweed\b|\bcannabis\b|\bcocaine\b|\bmeth\b|\bfentanyl\b', analysis.normalized_query))
    )
    public_sanitation_query = bool(
        re.search(
            r'public defecation|defecat\w+|poop\w+|feces|urinat\w+|peeing|public indecency|indecent exposure|lewd conduct',
            analysis.normalized_query,
        )
    )
    installation_entry_query = bool(
        re.search(r'trespass|unauthorized entr|unlawful entr|without permission|barred from (?:base|installation)|reenter(?:ed)?|returned to (?:base|installation)|ordered not to return|told not to return|refus\w+ to leave|remain\w+ after|debarred|barment', analysis.normalized_query)
        or ('restricted area' in analysis.normalized_query and not controlled_substance_query)
    )
    property_damage_query = bool(re.search(r'damag|destroy|destruction|vandal|graffiti|break|broke|smash', analysis.normalized_query))
    lawful_order_query = bool(re.search(r'lawful order|lawful command|direct order|disobey|refus\w+ command|article 92|regulation', analysis.normalized_query))

    if analysis.ocga_code and analysis.ocga_code in code_text:
        score += 96
        reasons.append('matched citation')
    elif analysis.ocga_prefix and analysis.ocga_prefix in code_text:
        score += 76
        reasons.append('matched citation prefix')
    if analysis.article_number and f'article {analysis.article_number}' in code_text:
        score += 92
        reasons.append('matched article number')
    if analysis.normalized_query == code_text:
        score += 102
        reasons.append('matched exact citation')
    if analysis.normalized_query and analysis.normalized_query == title_text:
        score += 78
        reasons.append('matched exact title')
    elif analysis.normalized_query and analysis.normalized_query in title_text:
        score += 36
        reasons.append('matched title phrase')
    elif title_led_query:
        score += 46
        reasons.append('matched title-led query')
    if exact_keyword_match:
        score += 84
        reasons.append('matched exact keyword')
    if exact_alias_match:
        score += 52
        reasons.append('matched exact alias')

    full_text_score, full_text_reasons, full_text_terms, full_text_coverage = _full_document_relevance(profile, analysis)
    if full_text_score:
        score += full_text_score
        reasons.extend(full_text_reasons)
        matched_terms.extend(full_text_terms)
    keyword_only_match = bool(
        (exact_keyword_match or any(analysis.normalized_query and analysis.normalized_query in item for item in normalized_keywords))
        and full_text_coverage < 0.18
        and analysis.normalized_query != title_text
        and analysis.normalized_query != code_text
        and not (analysis.ocga_code or analysis.ocga_prefix or analysis.article_number)
    )
    if keyword_only_match:
        score -= 30 if strict_gating else 18
        reasons.append('keyword-only weak match')

    for field_name, field_tokens in profile.field_tokens.items():
        overlap = set(analysis.tokens) & set(field_tokens)
        if overlap:
            field_weight = SEARCH_FIELD_WEIGHTS.get(field_name, 8)
            score += len(overlap) * field_weight
            matched_terms.extend(sorted(overlap))
            if field_name in {'keywords', 'aliases', 'narrative_triggers'}:
                reasons.append('matched scenario triggers')
            elif field_name in {'title', 'summary', 'elements'}:
                reasons.append(f'matched {field_name}')
        expanded_overlap = (set(analysis.expanded_terms) - set(analysis.tokens)) & set(field_tokens)
        if expanded_overlap:
            score += len(expanded_overlap) * max(3, SEARCH_FIELD_WEIGHTS.get(field_name, 8) * 0.45)

    phrase_hits: list[str] = []
    for phrase in analysis.phrases + analysis.expanded_phrases:
        if not phrase or len(phrase) < 5:
            continue
        if phrase in all_text:
            phrase_hits.append(phrase)
    if phrase_hits:
        score += min(42, 16 + (len(phrase_hits) * 5))
        reasons.append(f"matched phrase: {phrase_hits[0]}")

    concept_overlap = list(_ordered_unique(set(analysis.concept_tags) & set(profile.concept_tags)))
    if concept_overlap:
        score += 18 * len(concept_overlap)
        reasons.extend(f"matched concept: {concept.replace('_', ' ')}" for concept in concept_overlap[:2])

    intent_overlap = set(analysis.intents) & set(profile.intent_tags)
    if intent_overlap:
        score += 12 + (len(intent_overlap) * 4)
        reasons.append('matched offense context')
    elif analysis.intents and strict_gating:
        score -= 10

    source_overlap = set(analysis.source_hints) & set(profile.source_hints)
    if source_overlap:
        score += 12 + (4 * len(source_overlap))
        best_source = profile.entry.source if profile.entry.source in source_overlap else next(iter(source_overlap))
        reasons.append(f"matched jurisdiction: {SOURCE_DISPLAY_LABELS.get(best_source, best_source)}")
    elif analysis.source_hints and strict_gating:
        if 'FEDERAL_USC' in analysis.source_hints and entry.source not in {'FEDERAL_USC', 'BASE_ORDER'}:
            score -= 18
        elif 'UCMJ' in analysis.source_hints and entry.source == 'GEORGIA':
            score -= 14
        elif 'GEORGIA' in analysis.source_hints and entry.source == 'FEDERAL_USC':
            score -= 10

    context_overlap = set(analysis.context_terms) & set(profile.field_tokens.get('context', frozenset()))
    if context_overlap:
        score += min(18, 5 + (len(context_overlap) * 3))
        reasons.append('matched context clues')

    conduct_overlap = set(analysis.conduct_terms) & profile.all_tokens
    if conduct_overlap:
        score += min(14, 4 + (len(conduct_overlap) * 3))
        reasons.append('matched conduct')

    token_overlap = set(analysis.tokens) & set(profile.all_tokens)
    if token_overlap:
        coverage = len(token_overlap) / max(1, len(set(analysis.tokens)))
        score += coverage * 18
        if coverage >= 0.55:
            reasons.append('matched broad scenario details')
        elif coverage < 0.2:
            score -= 8

    fuzzy_score, fuzzy_terms = _fuzzy_overlap_score(analysis.tokens, profile.all_tokens)
    if fuzzy_score:
        score += fuzzy_score
        matched_terms.extend(fuzzy_terms)

    best_similarity = max(
        SequenceMatcher(None, analysis.normalized_query, candidate).ratio()
        for candidate in (
            title_text,
            summary_text,
            profile.field_texts.get('examples', ''),
            profile.field_texts.get('narrative_triggers', ''),
        )
        if candidate
    )
    if best_similarity >= 0.72:
        score += 14
        reasons.append('matched similar scenario wording')
    elif best_similarity >= 0.58:
        score += 7

    score *= profile.source_quality
    if 'matched exact title' in reasons:
        score += 44
    if 'matched exact keyword' in reasons:
        score += 38
    if 'matched exact alias' in reasons:
        score += 20
    if 'matched title-led query' in reasons:
        score += 24

    weak_overlap = len(token_overlap) + len(phrase_hits) + len(concept_overlap)
    if weak_overlap <= 1 and best_similarity < 0.58 and not source_overlap:
        score -= 18 if strict_gating else 10
    if analysis.stage == 'primary' and analysis.tokens and len(token_overlap) == 0 and not phrase_hits and not concept_overlap:
        score -= 22
    if controlled_substance_query and entry.code == '18 USC 1382' and not installation_entry_query:
        # Keep base/gate context as background, but do not let it beat the
        # actual described drug conduct unless entry/barment facts are present.
        score -= 40
        reasons.append('location context only; primary conduct is controlled substance')
    if public_sanitation_query:
        if entry.code == '18 USC 1382' and not installation_entry_query:
            score -= 130
            reasons.append('location context only; primary conduct is public sanitation/indecency')
        if entry.code == '18 USC 1361' and not property_damage_query:
            score -= 72
            reasons.append('suppressed property-damage path; no damage facts described')
        if entry.code == 'Article 92' and not lawful_order_query:
            score -= 64
            reasons.append('suppressed order/regulation path; no order facts described')
        if (
            entry.source == 'BASE_ORDER'
            and re.search(r'traffic|speed|seat belt|cell phone|texting|vehicle', title_text)
            and not re.search(r'vehicle|traffic|driv|road|lane|speed|crash|parking|seat belt|cell phone|texting', analysis.normalized_query)
        ):
            score -= 90
            reasons.append('suppressed traffic-order path; no traffic facts described')

    final_reasons = _ordered_unique(reasons)[:6]
    final_terms = _ordered_unique(matched_terms)[:10]
    return score, final_reasons, final_terms


def _run_retrieval_pass(query: str, source: str, strict_gating: bool, stage: str = 'primary') -> tuple[QueryAnalysis, list[LegalMatch]]:
    analysis = _analyze_query(query, source, stage=stage)
    pool = list(get_entries(source))
    if not analysis.normalized_query:
        return analysis, [LegalMatch(entry=entry, score=1, reasons=('Reference list',)) for entry in pool[:12]]
    profiles = [_build_entry_profile(entry) for entry in pool]
    candidates = [profile for profile in profiles if _candidate_gate(profile, analysis, strict_gating)]
    if not candidates and stage == 'fallback':
        candidates = profiles

    scored: list[LegalMatch] = []
    for profile in candidates:
        raw_score, reasons, matched_terms = _score_profile(profile, analysis, strict_gating)
        if raw_score <= (36 if stage == 'fallback' else 28):
            continue
        if not reasons and strict_gating:
            continue
        scored.append(
            LegalMatch(
                entry=profile.entry,
                score=int(round(raw_score)),
                reasons=reasons,
                matched_terms=matched_terms,
            )
        )
    scored.sort(key=_legal_match_sort_key)
    return analysis, scored


def _reason_priority(item: LegalMatch) -> int:
    reasons = set(item.reasons)
    priority = 0
    if 'matched exact citation' in reasons:
        priority += 120
    if 'matched citation' in reasons:
        priority += 80
    if 'matched article number' in reasons:
        priority += 76
    if 'matched exact title' in reasons:
        priority += 56
    if 'matched title-led query' in reasons:
        priority += 28
    if 'matched exact keyword' in reasons:
        priority += 36
    if 'matched exact alias' in reasons:
        priority += 18
    return priority


def _legal_match_sort_key(item: LegalMatch) -> tuple[int, int, str, str]:
    return (-item.score, -_reason_priority(item), item.entry.source, item.entry.code)


def _merge_search_passes(groups: list[list[LegalMatch]]) -> list[LegalMatch]:
    merged: dict[str, LegalMatch] = {}
    for group in groups:
        for rank, item in enumerate(group):
            boost = max(0, 8 - rank)
            existing = merged.get(item.entry.code)
            if existing is None or item.score + boost > existing.score:
                reasons = tuple(_ordered_unique((existing.reasons if existing else ()) + item.reasons))
                matched_terms = tuple(_ordered_unique((existing.matched_terms if existing else ()) + item.matched_terms))
                merged[item.entry.code] = LegalMatch(
                    entry=item.entry,
                    score=item.score + boost if existing is not None else item.score,
                    reasons=reasons,
                    matched_terms=matched_terms,
                )
    return sorted(merged.values(), key=_legal_match_sort_key)


def _needs_fallback(results: list[LegalMatch]) -> bool:
    if not results:
        return True
    if len(results) == 1 and results[0].score < 90:
        return True
    return False


def _required_codes_for_query(analysis: QueryAnalysis, source: str) -> tuple[str, ...]:
    normalized = analysis.normalized_query
    required: list[str] = []
    if analysis.article_number:
        required.append(f'Article {analysis.article_number.upper()}')
    if re.search(r'aggravated sexual battery|sexual battery', normalized):
        required.append('OCGA 16-6-22')
    if re.search(r'rape|forced sex|sexual assault|sexual battery|nonconsensual', normalized):
        required.extend(['OCGA 16-6-1', 'Article 120'])
    if re.search(r'public defecation|defecat\w+ in public|poop\w+ in (?:public|the street|street)|poop\w+.*(?:road|sidewalk|street|public)', normalized):
        required.extend(['OCGA 16-11-39', 'OCGA 16-6-8'])
    if re.search(r'\bdui\b|intoxicat|impaired|drunk|refus\w+.*(?:breath|blood|test)|implied consent|less safe|weav', normalized):
        required.append('OCGA 40-6-391')
        if re.search(r'refus\w+.*(?:breath|blood|test)|implied consent', normalized):
            required.extend(['OCGA 40-5-67.1', 'OCGA 40-6-392'])
        if 'weav' in normalized:
            required.append('OCGA 40-6-48')
        if any(token in normalized for token in ('base', 'mclb', 'installation', 'on base')):
            required.extend(['MCLBAO 5560.9G CH3-11', 'MCLBAO 5560.9G CH6'])
    if re.search(r'\b\d{1,3}\s*(?:in|/)\s*(?:a\s*)?\d{1,3}\b', normalized):
        required.append('OCGA 40-6-181')
    if re.search(r'stop sign|red light|traffic control', normalized):
        required.extend(['OCGA 40-6-20', 'OCGA 40-6-72'])
    if 'prescription' in normalized and 'pill' in normalized and 'forg' not in normalized and 'fake prescription' not in normalized:
        required.extend(['OCGA 16-13-30', 'OCGA 16-13-58'])
    if re.search(r'\bmarijuana\b|\bweed\b|\bcannabis\b', normalized):
        required.extend(['OCGA 16-13-75', 'OCGA 16-13-30'])
    if re.search(r'\bhigh on duty\b|drunk on duty|incapacitated for duty', normalized):
        required.extend(['Article 112', 'Article 112a'])
    if re.search(r'homeowner|home owner|vehicle was taken|car stolen|vehicle stolen|taken overnight', normalized):
        required.append('OCGA 16-8-2')
    if re.search(r'shoplifting|shoplift|retail theft|merchandise from store|from px', normalized):
        required.extend(['OCGA 16-8-14', 'OCGA 16-8-2'])
    if re.search(r'\bpushed\b|\bslapped\b|\bgrabbed\b|\bshoved\b|\bhit\b', normalized):
        required.extend(['OCGA 16-5-23', 'OCGA 16-5-20'])
        if any(term in normalized for term in ('spouse', 'wife', 'husband', 'domestic', 'family violence')):
            required.append('OCGA 16-5-23.1')
    if re.search(r'lawful order|lawful command|direct order|disobeyed order|refused command', normalized):
        required.extend(['Article 92', 'Article 91'])
    if re.search(r'false name|fake id|false identification|identity theft|stolen ids?', normalized):
        if 'identity theft' in normalized or 'stolen id' in normalized or 'fake id' in normalized:
            required.append('18 USC 1028')
    if re.search(r'government property', normalized):
        required.append('18 USC 641')
    controlled_substance_query = bool(re.search(r'\bdrug\b|\bdrugs\b|\bnarcotic\b|\bmarijuana\b|\bweed\b|\bcannabis\b|\bcocaine\b|\bmeth\b|\bfentanyl\b', normalized))
    installation_entry_query = bool(
        re.search(r'trespass|federal installation|military installation|unauthorized entr|unlawful entr|without permission|barred from base|barred from installation|reenter(?:ed)?|returned to (?:base|installation)|ordered not to return|told not to return|refus\w+ to leave|remain\w+ after|debarred|barment', normalized)
        or ('restricted area' in normalized and not controlled_substance_query)
    )
    if installation_entry_query:
        required.append('18 USC 1382')
    allowed_sources = {'GEORGIA', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'}
    if source in allowed_sources:
        entries = {entry.code for entry in get_entries(source)}
        required = [code for code in required if code in entries]
    return _ordered_unique(required)


def _forbidden_codes_for_query(analysis: QueryAnalysis) -> tuple[str, ...]:
    normalized = analysis.normalized_query
    forbidden: list[str] = []
    if 'prescription' in normalized and 'pill' in normalized and 'forg' not in normalized and 'fake prescription' not in normalized:
        forbidden.extend(['OCGA 16-13-37', 'OCGA 16-13-33', 'OCGA 16-13-33.1'])
    if 'control' in normalized and 'substance' in normalized and 'forg' not in normalized:
        forbidden.append('OCGA 16-13-37')
    return _ordered_unique(forbidden)


def _apply_result_overlays(results: list[LegalMatch], analysis: QueryAnalysis, source: str) -> list[LegalMatch]:
    if not results:
        results = []
    forbidden = set(_forbidden_codes_for_query(analysis))
    if forbidden:
        results = [item for item in results if item.entry.code not in forbidden]
    required_codes = _required_codes_for_query(analysis, source)
    if not required_codes:
        return results
    by_code = {item.entry.code: item for item in results}
    pool = {entry.code: entry for entry in get_entries(source)}
    seed = results[0].score if results else 72
    for index, code in enumerate(required_codes):
        if code in by_code:
            existing = by_code[code]
            by_code[code] = LegalMatch(
                entry=existing.entry,
                score=max(existing.score, 56, seed - min(index * 3, 12)),
                reasons=tuple(_ordered_unique(existing.reasons + ('matched likely core reference path',))),
                matched_terms=existing.matched_terms,
            )
            continue
        entry = pool.get(code)
        if not entry:
            continue
        by_code[code] = LegalMatch(
            entry=entry,
            score=max(56, seed - min(index * 4, 16)),
            reasons=('matched likely core reference path',),
        )
    return sorted(by_code.values(), key=_legal_match_sort_key)


def _expand_terms(terms: list[str]) -> list[str]:
    expanded: list[str] = []
    seen = set()
    for term in terms:
        normalized_term = _normalize(term)
        if not normalized_term or normalized_term in STOPWORDS:
            continue
        if normalized_term and normalized_term not in seen:
            expanded.append(normalized_term)
            seen.add(normalized_term)
        for synonym in SYNONYM_MAP.get(normalized_term, ()):
            normalized = _normalize(synonym)
            if normalized and normalized not in seen and normalized not in STOPWORDS:
                expanded.append(normalized)
                seen.add(normalized)
    return expanded


def _expand_phrase_aliases(query: str) -> list[str]:
    normalized = _normalize(query)
    aliases: list[str] = []
    for phrase, values in PHRASE_ALIASES.items():
        if phrase in normalized:
            aliases.extend(_normalize(v) for v in values if _normalize(v))
    return aliases


def _article_number(query: str) -> str:
    match = re.search(r'\barticle\s+(\d+[a-z]?)\b', query)
    if match:
        return match.group(1).lower()
    plain = re.fullmatch(r'(\d+[a-z]?)', query.strip())
    if plain:
        return plain.group(1).lower()
    return ''


def _ocga_code_token(query: str) -> str:
    match = re.search(r'\b(\d{1,2}-\d-\d{1,3}(?:\.\d+)?)\b', query)
    return match.group(1).lower() if match else ''


def _ocga_prefix_token(query: str) -> str:
    raw = (query or '').lower().replace('ocga', ' ').strip()
    match = re.search(r'\b(\d{1,2}(?:-\d{1,2}){1,3}(?:\.\d+)?)\b', raw)
    return match.group(1).lower() if match else ''


def _scenario_signals(query: str) -> tuple[str, ...]:
    normalized = _normalize(query)
    signals: list[str] = []
    if any(token in normalized for token in ('truck', 'driving', 'road', 'traffic', 'speed', 'plate', 'tag', 'lane', 'signal', 'red light', 'stop sign', 'dui', 'reckless')):
        signals.append('GEORGIA')
    if any(token in normalized for token in ('article', 'awol', 'superior', 'nco', 'order', 'duty', 'military', 'commissioned')):
        signals.append('UCMJ')
    if any(token in normalized for token in ('mclb', 'mclb albany', 'base traffic', 'installation traffic', 'base order', 'on base', 'barracks')):
        signals.extend(('GEORGIA', 'BASE_ORDER'))
    if any(token in normalized for token in ('domestic violence', 'family violence', 'wife', 'husband', 'girlfriend', 'boyfriend', 'spouse', 'dating partner')):
        signals.append('GEORGIA')
    if any(token in normalized for token in ('sex in public', 'public sex', 'public indecency', 'indecent exposure', 'lewd conduct')):
        signals.append('GEORGIA')
    if any(token in normalized for token in ('rape', 'sexual assault', 'sexual battery', 'nonconsensual', 'forcible rape', 'forced sex')):
        # Sexual-offense scenarios commonly require both state and UCMJ review.
        signals.extend(('GEORGIA', 'UCMJ'))
    if any(token in normalized for token in ('marine', 'soldier', 'airman', 'sailor', 'service member', 'military', 'on base', 'barracks')):
        signals.append('UCMJ')
    if any(token in normalized for token in ('article 112a', 'wrongful use', 'wrongful possession', 'introduced drugs on base', 'high on duty', 'drunk on duty')):
        signals.append('UCMJ')
    if any(token in normalized for token in ('federal', 'usc', 'u s code', 'government property', 'federal property', 'prohibited person firearm')):
        signals.append('FEDERAL_USC')
    return tuple(dict.fromkeys(signals))


def _scenario_pack_hits(query: str) -> tuple[str, ...]:
    normalized = _normalize(query)
    hits: list[str] = []
    theft_context = any(token in normalized for token in ('stole', 'stolen', 'theft', 'robbery', 'shoplifting', 'auto theft', 'vehicle theft'))
    drug_context = any(token in normalized for token in ('drug', 'drugs', 'marijuana', 'weed', 'cannabis', 'narcotic', 'controlled substance', 'cocaine', 'meth'))
    for pack_name, pack in SCENARIO_PACKS.items():
        if pack_name == 'traffic' and theft_context:
            continue
        if pack_name == 'traffic' and drug_context:
            continue
        if any(_normalize(trigger) in normalized for trigger in pack['triggers']):
            hits.append(pack_name)
    return tuple(dict.fromkeys(hits))


def _intent_phrase_hits(query: str) -> tuple[str, ...]:
    normalized = _normalize(query)
    hits: list[str] = []
    for phrase in INTENT_PHRASE_CODES:
        if _normalize(phrase) in normalized:
            hits.append(phrase)
    return tuple(dict.fromkeys(hits))


def _split_query_clauses(query: str) -> tuple[str, ...]:
    text = (query or '').strip()
    if not text:
        return ()
    lowered = f" {text.lower()} "
    # Only split when there are explicit multi-event connectors.
    if not any(token in lowered for token in (' and ', ' then ', ' while ', ' after ', ';', ',')):
        return ()
    parts = re.split(r'\b(?:and then|then|while|after|and)\b|[;,]', text, flags=re.I)
    clean = []
    seen = set()
    for part in parts:
        clause = ' '.join(part.strip().split())
        if len(clause) < 6:
            continue
        key = clause.lower()
        if key in seen:
            continue
        seen.add(key)
        clean.append(clause)
    return tuple(clean[:5])


def _merge_ranked_results(base: list[LegalMatch], extra_groups: list[list[LegalMatch]]) -> list[LegalMatch]:
    merged: dict[str, LegalMatch] = {item.entry.code: item for item in base}
    for group in extra_groups:
        for idx, item in enumerate(group):
            existing = merged.get(item.entry.code)
            boost = max(4, 12 - min(idx, 8))
            if existing is None:
                merged[item.entry.code] = LegalMatch(
                    entry=item.entry,
                    score=item.score + boost,
                    reasons=tuple(dict.fromkeys(tuple(item.reasons) + ('Clause match',))),
                )
                continue
            if item.score + boost > existing.score:
                merged[item.entry.code] = LegalMatch(
                    entry=item.entry,
                    score=item.score + boost,
                    reasons=tuple(dict.fromkeys(tuple(existing.reasons) + tuple(item.reasons) + ('Clause match',))),
                )
            else:
                merged[item.entry.code] = LegalMatch(
                    entry=existing.entry,
                    score=existing.score,
                    reasons=tuple(dict.fromkeys(tuple(existing.reasons) + ('Clause match',))),
                )
    ordered = sorted(merged.values(), key=lambda item: (-item.score, item.entry.source, item.entry.code))
    return ordered


def _confidence_from_score(score: int, top_score: int) -> int:
    if top_score <= 0:
        return 0
    relative = int((score / top_score) * 100)
    absolute = max(0, min(99, int(score * 0.85)))
    blended = int((relative * 0.65) + (absolute * 0.35))
    return max(0, min(99, blended))


def _certainty_bucket(confidence: int) -> str:
    if confidence >= 85:
        return 'strong'
    if confidence >= 60:
        return 'probable'
    return 'possible'


def _result_warning(entry: LegalEntry, confidence: int) -> str:
    warnings: list[str] = []
    if confidence < 45:
        warnings.append('Possible match - verify final charge selection.')
    if (
        not (entry.minimum_punishment or entry.maximum_punishment)
        or (entry.minimum_punishment or '').lower().startswith('minimum punishment depends on charged federal subsection')
        or (entry.maximum_punishment or '').lower().startswith('maximum punishment is governed by the charged federal statute')
    ):
        warnings.append('Punishment data not loaded.')
    if entry.source == 'BASE_ORDER' and not entry.source_reference:
        warnings.append('MCLB Albany order source not yet loaded.')
    if entry.source == 'FEDERAL_USC' and not entry.official_text_available:
        warnings.append('Federal source data incomplete.')
    if entry.citation_requires_verification:
        warnings.append('Citation requires verification.')
    return ' '.join(warnings)


def _finalize_results(query: str, raw_results: list[LegalMatch]) -> list[LegalMatch]:
    if not raw_results:
        return []
    query_terms = set(_tokenize(_normalize(query)))
    top_score = raw_results[0].score if raw_results else 0
    finalized: list[LegalMatch] = []
    for item in raw_results:
        entry_text = ' '.join((
            item.entry.code,
            item.entry.title,
            item.entry.summary,
            ' '.join(item.entry.elements),
            ' '.join(item.entry.keywords),
            ' '.join(item.entry.aliases),
            ' '.join(item.entry.synonyms),
            ' '.join(item.entry.narrative_triggers),
            ' '.join(item.entry.derived_aliases),
            ' '.join(item.entry.derived_synonyms),
            ' '.join(item.entry.derived_triggers),
        ))
        entry_terms = set(_tokenize(_normalize(entry_text)))
        matched_terms = tuple(sorted(query_terms & entry_terms))[:10]
        confidence = _confidence_from_score(item.score, top_score)
        warning = _result_warning(item.entry, confidence)
        finalized.append(
            LegalMatch(
                entry=item.entry,
                score=item.score,
                reasons=item.reasons,
                confidence=confidence,
                matched_terms=matched_terms,
                warning=warning,
                certainty_bucket=_certainty_bucket(confidence),
            )
        )
    return finalized


def search_entries(query: str, source: str = 'ALL', strict_gating: bool = True) -> list[LegalMatch]:
    corrected_query = _correct_misspellings(query)
    normalized_query = _normalize(corrected_query)
    source = (source or 'ALL').upper()
    pool = list(get_entries(source))
    if not normalized_query:
        return _finalize_results(query, [LegalMatch(entry=entry, score=1, reasons=('Reference list',)) for entry in pool[:12]])

    raw_terms = normalized_query.split()
    terms = _expand_terms(raw_terms + _expand_phrase_aliases(normalized_query))
    query_tokens = set(_tokenize(normalized_query))
    narrative_query = len(query_tokens) >= 6
    article_number = _article_number(normalized_query)
    ocga_code = _ocga_code_token(corrected_query)
    ocga_prefix = _ocga_prefix_token(corrected_query)
    scenario_sources = _scenario_signals(normalized_query)
    scenario_packs = _scenario_pack_hits(normalized_query)
    intent_hits = _intent_phrase_hits(normalized_query)
    intent_codes = {code for phrase in intent_hits for code in INTENT_PHRASE_CODES.get(phrase, ())}
    query_intents = _query_intents(normalized_query)
    speed_phrase = bool(re.search(r'\b\d{1,3}\s*(?:in|/)\s*(?:a\s*)?\d{1,3}\b', normalized_query))
    dui_phrase = bool(re.search(r'\bdui\b|impaired|drunk|alcohol|refus\w+\s+(?:breath|blood|test)|implied consent|less safe|weav\w+', normalized_query))
    sexual_phrase = bool(re.search(r'\brape\w*\b|sexual assault|sexual battery|nonconsensual|forced sex', normalized_query))
    public_indecency_phrase = bool(re.search(r'\bsex in public\b|\bpublic sex\b|public indecency|indecent exposure|lewd conduct|exposed (himself|herself)|public defecation|defecat\w+ in public|poop\w+ in (?:public|the street|street)', normalized_query))
    handicap_phrase = bool(re.search(r'handicap parking|disabled parking|parking in handicap', normalized_query))
    stop_sign_phrase = bool(re.search(r'ran stop sign|stop sign', normalized_query))
    drug_phrase = bool(re.search(r'drug|drugs|narcotic|cocaine|meth|methamphetamine|marijuana|weed|cannabis|paraphernalia|prescription|pill|fentanyl', normalized_query))
    school_zone_drug_phrase = bool(re.search(r'near (?:a )?school|school zone|drug free zone', normalized_query))
    minor_drug_phrase = bool(re.search(r'used a child|minor .*drug|child .*narcotic', normalized_query))
    forged_rx_phrase = bool(re.search(r'forged prescription|fake prescription|rx fraud|prescription fraud|doctor shopping', normalized_query))
    prescription_pill_possession_phrase = bool(
        re.search(r'possession of (?:prescription )?pills?|pressession of (?:prescription )?pills?|possession .*rx|rx possession', normalized_query)
        or (('possession' in normalized_query or 'possess' in normalized_query) and any(token in normalized_query for token in ('prescription', 'pill', 'pills', 'rx')))
    )
    meth_lab_phrase = bool(re.search(r'meth lab|precursor|cook meth|one pot', normalized_query))
    counterfeit_pill_phrase = bool(re.search(r'fake pills|counterfeit pills|pressed pills|imitation drug', normalized_query))
    practitioner_drug_phrase = bool(re.search(r'pill mill|unlawful prescribing|doctor .*narcotic scripts|overprescribing', normalized_query))
    military_drug_phrase = bool(re.search(r'article 112a|wrongful use|wrongful possession|introduced drugs on base|marine|service member|barracks|high on duty|drunk on duty', normalized_query))
    federal_phrase = bool(re.search(r'federal|usc|united states code|interstate|bank|wire fraud|identity theft|government property|federal facility|unauthorized computer access|counterfeit', normalized_query))
    federal_installation_phrase = bool(re.search(r'federal installation|military installation|barred from (?:base|installation)|reenter(?:ed)? (?:base|installation)|returned to (?:base|installation)|unlawful entry onto (?:military|federal).*(?:installation|property)|restricted area|debarred|barment', normalized_query))
    federal_entry_conduct_phrase = bool(
        re.search(r'trespass|unauthorized entr|unlawful entr|without permission|barred from (?:base|installation)|reenter(?:ed)?|returned to (?:base|installation)|ordered not to return|told not to return|refus\w+ to leave|remain\w+ after|debarred|barment', normalized_query)
        or ('restricted area' in normalized_query and not drug_phrase)
    )
    marijuana_possession_phrase = bool(re.search(r'possession of marijuana|marijuana possession|weed possession|cannabis possession', normalized_query))
    marijuana_term_phrase = bool(re.search(r'marijuana|weed|cannabis', normalized_query))
    retail_theft_phrase = bool(re.search(r'shoplift|steal(?:ing)?(?: [a-z]+){0,3} from (?:the )?store|store theft|retail theft|stole(?: [a-z]+){0,3} from (?:the )?store', normalized_query))
    nonviolent_theft_phrase = bool(
        any(token in normalized_query for token in ('theft', 'stole', 'steal', 'stolen', 'shoplift', 'retail theft', 'store theft'))
        and not any(token in normalized_query for token in ('armed', 'weapon', 'gun', 'force', 'threat', 'robbery', 'carjacking', 'kidnap'))
    )
    vehicle_theft_phrase = bool(
        (
            any(token in normalized_query for token in ('car', 'vehicle', 'auto', 'truck'))
            and any(token in normalized_query for token in ('stole', 'stolen', 'theft', 'taken'))
        )
        or any(token in normalized_query for token in ('car stolen', 'vehicle stolen', 'auto theft', 'stolen vehicle'))
    )
    owner_victim_theft_phrase = bool(
        vehicle_theft_phrase and any(token in normalized_query for token in (
            'my ', 'home owner', 'homeowner', 'owner', 'victim', 'from driveway', 'from home', 'was stolen', 'had the'
        ))
    )
    receiving_stolen_phrase = bool(any(token in normalized_query for token in (
        'receiving stolen', 'received stolen', 'in possession of stolen', 'possessing stolen', 'retained stolen'
    )))
    speed_codes = {'OCGA 40-6-181'}
    if any(token in normalized_query for token in ('mclb', 'base traffic', 'installation traffic')):
        speed_codes.add('MCLBAO 5560.9G CH3-11')
    if any(token in normalized_query for token in ('reckless', 'unsafe', 'disregard')):
        speed_codes.add('OCGA 40-6-390')
    if any(token in normalized_query for token in ('aggressive', 'road rage', 'harass', 'intimidate', 'obstruct')):
        speed_codes.add('OCGA 40-6-397')
    dui_codes = {'OCGA 40-6-391', 'OCGA 40-5-67.1', 'OCGA 40-6-392', 'OCGA 40-6-48'}
    sexual_codes = {'OCGA 16-6-1', 'OCGA 16-6-22', 'Article 120'}
    public_indecency_codes = {'OCGA 16-6-8', 'OCGA 16-11-39'}
    vehicle_theft_codes = {'OCGA 16-8-2', 'OCGA 16-8-60'}
    retail_theft_codes = {'OCGA 16-8-14', 'OCGA 16-8-2'}
    nonviolent_person_crime_codes = {'OCGA 16-5-40', 'OCGA 16-5-41', 'OCGA 16-5-21'}
    if receiving_stolen_phrase:
        vehicle_theft_codes.add('OCGA 16-8-7')
    if source in {'GEORGIA', 'ALL'} and (ocga_code or ocga_prefix):
        lookup = (ocga_code or ocga_prefix).lower()
        direct_matches: list[LegalMatch] = []
        georgia_pool = [item for item in pool if item.source == 'GEORGIA']
        for entry in georgia_pool:
            code_match = re.search(r'(\d{1,2}-\d{1,2}(?:-\d{1,3}(?:\.\d+)?)?)', entry.code.lower())
            if not code_match:
                continue
            code_token = code_match.group(1)
            if code_token.startswith(lookup) or lookup in code_token:
                reason = 'Code number match' if code_token == lookup else 'Code prefix match'
                score = 120 if code_token == lookup else 98
                direct_matches.append(LegalMatch(entry=entry, score=score, reasons=(reason,)))
        if direct_matches:
            direct_matches.sort(key=lambda item: (-item.score, item.entry.code))
            return _finalize_results(query, direct_matches[:50])
    gated_codes = set()
    for pack_name in scenario_packs:
        gated_codes.update(SCENARIO_PACKS[pack_name]['codes'])
    if source == 'ALL' and intent_codes:
        gated_codes.update(intent_codes)
    scored: list[LegalMatch] = []
    for entry in pool:
        if dui_phrase and entry.code not in dui_codes and not speed_phrase:
            continue
        if public_indecency_phrase and not sexual_phrase and entry.code not in public_indecency_codes:
            continue
        if vehicle_theft_phrase and entry.code not in vehicle_theft_codes:
            continue
        if retail_theft_phrase and entry.code not in retail_theft_codes:
            continue
        if sexual_phrase and entry.code not in sexual_codes:
            continue
        if speed_phrase and entry.code not in speed_codes:
            continue
        if nonviolent_theft_phrase and entry.code in nonviolent_person_crime_codes:
            continue
        if prescription_pill_possession_phrase and entry.code == 'OCGA 16-13-37':
            # OCGA 16-13-37 is about prescription blanks/forms, not simple possession.
            continue
        if prescription_pill_possession_phrase and not forged_rx_phrase and entry.code in {'OCGA 16-13-33', 'OCGA 16-13-33.1'}:
            # Keep possession-focused returns clean unless the query clearly describes prescription fraud/forgery.
            continue
        if source == 'ALL' and gated_codes and strict_gating and entry.code not in gated_codes:
            # Keep exact-number style lookups available, but gate broad scenario searches.
            if not (
                _normalize(entry.code) == normalized_query
                or (ocga_code and ocga_code in _normalize(entry.code))
                or (entry.source == 'UCMJ' and article_number and f'article {article_number}' in _normalize(entry.code))
            ):
                continue
        code = _normalize(entry.code)
        title = _normalize(entry.title)
        summary = _normalize(entry.summary)
        notes = _normalize(entry.notes)
        elements = tuple(_normalize(item) for item in entry.elements)
        keywords = tuple(_normalize(item) for item in entry.keywords)
        aliases = tuple(_normalize(item) for item in entry.aliases)
        synonyms = tuple(_normalize(item) for item in entry.synonyms)
        narrative_triggers = tuple(_normalize(item) for item in entry.narrative_triggers)
        examples = tuple(_normalize(item) for item in entry.examples)
        derived_aliases = tuple(_normalize(item) for item in entry.derived_aliases)
        derived_synonyms = tuple(_normalize(item) for item in entry.derived_synonyms)
        derived_triggers = tuple(_normalize(item) for item in entry.derived_triggers)
        derived_examples = tuple(_normalize(item) for item in entry.derived_examples)
        conduct_verbs = tuple(_normalize(item) for item in entry.conduct_verbs)
        victim_context = tuple(_normalize(item) for item in entry.victim_context)
        property_context = tuple(_normalize(item) for item in entry.property_context)
        injury_context = tuple(_normalize(item) for item in entry.injury_context)
        relationship_context = tuple(_normalize(item) for item in entry.relationship_context)
        location_context = tuple(_normalize(item) for item in entry.location_context)
        federal_context = tuple(_normalize(item) for item in entry.federal_context)
        military_context = tuple(_normalize(item) for item in entry.military_context)
        traffic_context = tuple(_normalize(item) for item in entry.traffic_context)
        juvenile_context = tuple(_normalize(item) for item in entry.juvenile_context)
        drug_context = tuple(_normalize(item) for item in entry.drug_context)
        category = _normalize(entry.category)
        subcategory = _normalize(entry.subcategory)
        entry_token_source = ' '.join((
            code,
            title,
            summary,
            notes,
            category,
            subcategory,
            ' '.join(elements),
            ' '.join(keywords),
            ' '.join(aliases),
            ' '.join(synonyms),
            ' '.join(narrative_triggers),
            ' '.join(examples),
            ' '.join(derived_aliases),
            ' '.join(derived_synonyms),
            ' '.join(derived_triggers),
            ' '.join(derived_examples),
            ' '.join(conduct_verbs),
            ' '.join(victim_context),
            ' '.join(property_context),
            ' '.join(injury_context),
            ' '.join(relationship_context),
            ' '.join(location_context),
            ' '.join(federal_context),
            ' '.join(military_context),
            ' '.join(traffic_context),
            ' '.join(juvenile_context),
            ' '.join(drug_context),
        ))
        entry_tokens = set(_tokenize(entry_token_source))
        entry_intents = _entry_intents(entry)
        score = 0
        reasons: list[str] = []

        if normalized_query == code:
            score += 80
            reasons.append('Exact code match')
        elif ocga_code and ocga_code in code:
            score += 70
            reasons.append('Code number match')
        elif ocga_prefix and ocga_prefix in code:
            score += 55
            reasons.append('Code prefix match')

        if entry.source == 'UCMJ' and article_number and f'article {article_number}' in code:
            score += 70
            reasons.append('Article number match')

        if normalized_query == title:
            score += 50
            reasons.append('Exact title match')
        elif normalized_query in title:
            score += 25
            reasons.append('Title phrase match')
        else:
            similarity = SequenceMatcher(None, normalized_query, title).ratio()
            if similarity >= 0.72:
                score += 16
                reasons.append('Close title match')

        if normalized_query in summary:
            score += 18
            reasons.append('Summary phrase match')
        if any(normalized_query in alias for alias in aliases):
            score += 28
            reasons.append('Alias phrase match')
        if any(normalized_query in alias for alias in derived_aliases):
            score += 18
            reasons.append('Derived alias match')
        if any(normalized_query in item for item in synonyms):
            score += 20
            reasons.append('Synonym phrase match')
        if any(normalized_query in item for item in derived_synonyms):
            score += 14
            reasons.append('Derived synonym match')
        if any(normalized_query in item for item in narrative_triggers):
            score += 24
            reasons.append('Narrative trigger match')
        if any(normalized_query in item for item in derived_triggers):
            score += 15
            reasons.append('Derived narrative trigger match')
        if category and normalized_query in category:
            score += 12
            reasons.append('Category phrase match')
        if subcategory and normalized_query in subcategory:
            score += 10
            reasons.append('Subcategory phrase match')

        if entry.source in scenario_sources:
            score += 6
            reasons.append('Scenario context match')
        elif scenario_sources:
            score -= 4

        if owner_victim_theft_phrase:
            if entry.code == 'OCGA 16-8-2':
                score += 24
                reasons.append('Owner victim theft context')
            elif entry.code == 'OCGA 16-8-7':
                score -= 24
        if receiving_stolen_phrase and entry.code == 'OCGA 16-8-7':
            score += 20
            reasons.append('Receiving stolen property context')

        for pack_name in scenario_packs:
            if entry.code in SCENARIO_PACKS[pack_name]['codes']:
                score += 32 if pack_name == 'domestic_violence' else 22
                reasons.append(f'{pack_name.replace("_", " ").title()} scenario match')
        if intent_codes and entry.code in intent_codes:
            score += 34
            reasons.append('Intent phrase match')
        if query_intents:
            overlap_intents = query_intents & entry_intents
            if overlap_intents:
                score += min(20, 8 + (len(overlap_intents) * 4))
                reasons.append('Intent alignment match')
            elif entry_intents:
                score -= 10
                reasons.append('Intent mismatch')
        source_boost = _source_relevance_boost(entry.source, query_intents)
        if source_boost:
            score += source_boost
            reasons.append('Source relevance adjustment')
        if (
            drug_phrase
            and entry.code == '18 USC 1382'
            and not federal_entry_conduct_phrase
        ):
            # A gate/base location can be relevant background, but it should not
            # outrank the described drug conduct unless the officer describes
            # barment, trespass, reentry, or another installation-entry offense.
            score -= 32
            reasons.append('Location context only; primary conduct is controlled substance')

        for keyword in keywords:
            if normalized_query and normalized_query == keyword:
                score += 40
                reasons.append('Exact keyword match')
                break
            if normalized_query and normalized_query in keyword:
                score += 18
                reasons.append('Keyword phrase match')
                break

        for phrase in aliases + synonyms + narrative_triggers + conduct_verbs + derived_aliases + derived_synonyms + derived_triggers:
            if not phrase:
                continue
            if phrase == normalized_query:
                score += 24
                reasons.append('Exact narrative alias match')
                break
            if phrase in normalized_query:
                score += 14
                reasons.append('Narrative alias overlap')
                break

        if any(phrase and phrase in normalized_query for phrase in conduct_verbs):
            score += 10
            reasons.append('Matched conduct verb')
        if any(phrase and phrase in normalized_query for phrase in relationship_context):
            score += 8
            reasons.append('Matched relationship context')
        if any(phrase and phrase in normalized_query for phrase in victim_context):
            score += 7
            reasons.append('Matched victim context')
        if any(phrase and phrase in normalized_query for phrase in property_context):
            score += 7
            reasons.append('Matched property context')
        if any(phrase and phrase in normalized_query for phrase in injury_context):
            score += 7
            reasons.append('Matched injury context')
        if any(phrase and phrase in normalized_query for phrase in location_context):
            score += 7
            reasons.append('Matched location context')
        if any(phrase and phrase in normalized_query for phrase in military_context):
            score += 8
            reasons.append('Matched military context')
        if any(phrase and phrase in normalized_query for phrase in federal_context):
            score += 8
            reasons.append('Matched federal context')
        if any(phrase and phrase in normalized_query for phrase in traffic_context):
            score += 7
            reasons.append('Matched traffic context')
        if any(phrase and phrase in normalized_query for phrase in juvenile_context):
            score += 7
            reasons.append('Matched juvenile context')
        if any(phrase and phrase in normalized_query for phrase in drug_context):
            score += 7
            reasons.append('Matched drug context')

        comparison_examples = examples + derived_examples
        if comparison_examples:
            best_example_similarity = max(SequenceMatcher(None, normalized_query, sample).ratio() for sample in comparison_examples)
            if best_example_similarity >= 0.72:
                score += 14
                reasons.append('Example similarity match')
            elif best_example_similarity >= 0.60:
                score += 8
                reasons.append('Example partial similarity')

        for term in terms:
            if not term:
                continue
            if term.isdigit():
                continue
            if term in STOPWORDS:
                continue
            if len(term) < 3:
                continue
            term_weight = 0.5 if term in AMBIGUOUS_TERMS else 1.0
            if term in code:
                score += int(12 * term_weight)
            if term in title:
                score += int(10 * term_weight)
            if term in summary:
                score += int(6 * term_weight)
            if term in notes:
                score += int(4 * term_weight)
            if any(term in element for element in elements):
                score += int(8 * term_weight)
            if any(term in keyword for keyword in keywords):
                score += int(9 * term_weight)
            if any(term in value for value in aliases):
                score += int(8 * term_weight)
            if any(term in value for value in derived_aliases):
                score += int(5 * term_weight)
            if any(term in value for value in synonyms):
                score += int(7 * term_weight)
            if any(term in value for value in derived_synonyms):
                score += int(4 * term_weight)
            if any(term in value for value in narrative_triggers):
                score += int(9 * term_weight)
            if any(term in value for value in derived_triggers):
                score += int(5 * term_weight)
            if any(term in value for value in conduct_verbs):
                score += int(7 * term_weight)
            if any(term in value for value in relationship_context):
                score += int(5 * term_weight)
            if any(term in value for value in victim_context):
                score += int(4 * term_weight)
            if any(term in value for value in property_context):
                score += int(4 * term_weight)
            if any(term in value for value in injury_context):
                score += int(4 * term_weight)
            if any(term in value for value in location_context):
                score += int(4 * term_weight)
            if any(term in value for value in military_context):
                score += int(5 * term_weight)
            if any(term in value for value in federal_context):
                score += int(5 * term_weight)
            if any(term in value for value in traffic_context):
                score += int(4 * term_weight)
            if any(term in value for value in juvenile_context):
                score += int(4 * term_weight)
            if any(term in value for value in drug_context):
                score += int(4 * term_weight)
            if term in category or term in subcategory:
                score += int(5 * term_weight)

        if query_tokens and entry_tokens:
            overlap = len(query_tokens & entry_tokens)
            if overlap:
                score += overlap * 7
                reasons.append('Token overlap match')
            coverage = overlap / max(1, len(query_tokens))
            if coverage >= 0.6:
                score += 10
                reasons.append('High scenario coverage')
            elif coverage < 0.34:
                score -= 18
                reasons.append('Low scenario coverage')
            if len(query_tokens) >= 3 and overlap <= 1:
                if 'Exact code match' not in reasons and 'Article number match' not in reasons and 'Exact keyword match' not in reasons:
                    score -= 15
                    reasons.append('Weak token match')
            if len(query_tokens) >= 4 and overlap <= 1 and not (query_intents & entry_intents):
                score -= 18
                reasons.append('Weak contextual overlap')

        if not reasons and score:
            if any(term in element for term in terms for element in elements):
                reasons.append('Element match')
            elif any(term in summary for term in terms):
                reasons.append('Summary match')
            elif any(term in notes for term in terms):
                reasons.append('Notes match')
            else:
                reasons.append('Keyword match')

        if score:
            weak_reason_set = {'Token overlap match', 'Low scenario coverage', 'Weak token match', 'Weak contextual overlap'}
            useful_reason_set = {
                'Exact code match',
                'Code number match',
                'Article number match',
                'Exact title match',
                'Exact keyword match',
                'Keyword phrase match',
                'Intent phrase match',
                'Intent alignment match',
                'Matched conduct verb',
            }
            reason_set = set(reasons)
            if reason_set and reason_set.issubset(weak_reason_set):
                continue
            if score < 26 and not (reason_set & useful_reason_set):
                continue
            if strict_gating and (scenario_packs or intent_codes):
                has_signal = (
                    any(reason.endswith('scenario match') for reason in reasons)
                    or 'Intent phrase match' in reasons
                    or 'Exact code match' in reasons
                    or 'Article number match' in reasons
                    or 'Exact keyword match' in reasons
                    or 'Keyword phrase match' in reasons
                )
                if not has_signal:
                    continue
            scored.append(LegalMatch(entry=entry, score=score, reasons=tuple(dict.fromkeys(reasons))))

    scored.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if public_indecency_phrase and not sexual_phrase:
        focused = [item for item in scored if item.entry.code in public_indecency_codes]
        if focused:
            scored = focused
    if dui_phrase and not speed_phrase:
        focused = [item for item in scored if item.entry.code in dui_codes]
        if focused:
            scored = focused
        refusal_context = bool(re.search(r'refus\w+\s+(?:breath|blood|test)|implied consent', normalized_query))
        required_codes = {'OCGA 40-6-391'}
        if refusal_context:
            required_codes.update({'OCGA 40-5-67.1', 'OCGA 40-6-392'})
        if 'weav' in normalized_query:
            required_codes.add('OCGA 40-6-48')
        existing_codes = {item.entry.code for item in scored}
        top_seed = scored[0].score if scored else 62
        pool_by_code = {entry.code: entry for entry in pool}
        for code in required_codes:
            if code in existing_codes:
                continue
            entry = pool_by_code.get(code)
            if not entry:
                continue
            scored.append(
                LegalMatch(
                    entry=entry,
                    score=max(54, top_seed - 6),
                    reasons=('DUI required charge-path result',),
                )
            )
        scored.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if vehicle_theft_phrase:
        focused = [item for item in scored if item.entry.code in vehicle_theft_codes]
        if focused:
            scored = focused
    if retail_theft_phrase:
        focused = [item for item in scored if item.entry.code in retail_theft_codes]
        if focused:
            scored = focused
    if sexual_phrase:
        focused = [item for item in scored if item.entry.code in sexual_codes]
        if focused:
            scored = focused
        required_codes = {'OCGA 16-6-1', 'OCGA 16-6-22', 'Article 120'}
        existing = {item.entry.code for item in scored}
        seed = scored[0].score if scored else 62
        pool_by_code = {entry.code: entry for entry in pool}
        for code in required_codes:
            if code in existing:
                continue
            entry = pool_by_code.get(code)
            if not entry:
                continue
            scored.append(
                LegalMatch(
                    entry=entry,
                    score=max(56, seed - 7),
                    reasons=('Sexual-offense required result',),
                )
            )
            existing.add(code)
        scored.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if speed_phrase:
        focused = [item for item in scored if item.entry.code in speed_codes]
        if focused:
            scored = focused
    if source == 'ALL' and len(scenario_sources) == 1:
        preferred_source = scenario_sources[0]
        constrained = [
            item for item in scored
            if item.entry.source == preferred_source
            or item.score >= 90
            or 'Exact code match' in item.reasons
            or 'Article number match' in item.reasons
        ]
        if constrained:
            scored = constrained
    if not scored and source == 'ALL' and gated_codes and strict_gating:
        # Relax scenario gating once when natural-language wording is broad.
        return search_entries(query, source, strict_gating=False)
    if not scored and handicap_phrase:
        entry = next((e for e in pool if e.code == 'OCGA 40-6-221'), None)
        if entry:
            return _finalize_results(query, [LegalMatch(entry=entry, score=58, reasons=('Handicap parking required result',))])
    if not scored:
        return []

    top_score = scored[0].score
    if top_score <= 0:
        return []
    if source == 'GEORGIA':
        min_score = 10 if (ocga_prefix or ocga_code) else 22
    elif narrative_query:
        # Narrative "what I saw" descriptions should return a short, relevant possibility list.
        min_score = max(28, int(top_score * 0.45))
    else:
        min_score = max(45, int(top_score * 0.62))
    narrowed = [
        item for item in scored
        if item.score >= min_score
        or 'Exact code match' in item.reasons
        or 'Article number match' in item.reasons
        or 'Exact keyword match' in item.reasons
        or 'DUI required charge-path result' in item.reasons
    ]
    narrowed = [
        item for item in narrowed
        if 'Low scenario coverage' not in item.reasons
        or 'Exact code match' in item.reasons
        or 'Article number match' in item.reasons
        or 'Exact keyword match' in item.reasons
        or 'DUI required charge-path result' in item.reasons
    ]
    if not narrowed:
        narrowed = scored[:2]
    if handicap_phrase:
        existing = {item.entry.code for item in narrowed}
        if 'OCGA 40-6-221' not in existing:
            entry = next((e for e in pool if e.code == 'OCGA 40-6-221'), None)
            if entry:
                narrowed.append(LegalMatch(entry=entry, score=max(52, narrowed[0].score - 6 if narrowed else 52), reasons=('Handicap parking required result',)))
                existing.add('OCGA 40-6-221')
    if stop_sign_phrase:
        required_codes = ('OCGA 40-6-72', 'OCGA 40-6-20')
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 52
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(50, seed - 6), reasons=('Stop-sign required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if retail_theft_phrase:
        required_codes = ('OCGA 16-8-14', 'OCGA 16-8-2')
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 52
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(50, seed - 6), reasons=('Retail theft required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if owner_victim_theft_phrase:
        required_codes = ('OCGA 16-8-60', 'OCGA 16-8-2')
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 52
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(50, seed - 6), reasons=('Vehicle owner theft required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    domestic_phrase = bool(any(token in normalized_query for token in (
        'domestic', 'family violence', 'spouse', 'wife', 'husband', 'boyfriend', 'girlfriend', 'dating partner',
        'protective order', 'restraining order', 'tpo', 'stalking'
    )))
    if domestic_phrase and not sexual_phrase:
        required_codes = (
            'OCGA 16-5-23',
            'OCGA 16-5-23.1',
            'OCGA 16-5-20',
            'OCGA 16-5-90',
            'OCGA 16-5-95',
            'OCGA 16-5-41',
        )
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 54
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(52, seed - 7), reasons=('Domestic-violence required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    contact_assault_phrase = bool(
        any(token in normalized_query for token in ('slap', 'slapped', 'pushed', 'push', 'hit', 'struck', 'shoved'))
        and any(token in normalized_query for token in ('argument', 'fight', 'altercation', 'assault', 'battery', 'domestic', 'spouse', 'wife', 'husband'))
    )
    if source in {'ALL', 'GEORGIA'} and contact_assault_phrase:
        required_codes = ('OCGA 16-5-23', 'OCGA 16-5-20')
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 54
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(51, seed - 8), reasons=('Contact-assault required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    base_intox_phrase = bool(
        any(token in normalized_query for token in ('on base', 'base', 'mclb', 'installation'))
        and any(token in normalized_query for token in ('drunk', 'intoxicated', 'impaired', 'dui'))
        and any(token in normalized_query for token in ('drive', 'driving', 'vehicle', 'car', 'truck'))
    )
    if base_intox_phrase:
        required_codes = ('OCGA 40-6-391', 'MCLBAO 5560.9G CH3-11', 'MCLBAO 5560.9G CH6')
        existing = {item.entry.code for item in narrowed}
        seed = narrowed[0].score if narrowed else 58
        for code in required_codes:
            if code in existing:
                continue
            entry = next((e for e in pool if e.code == code), None)
            if not entry:
                continue
            narrowed.append(LegalMatch(entry=entry, score=max(54, seed - 6), reasons=('Base intoxicated driving required result',)))
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if dui_phrase and not speed_phrase:
        refusal_context = bool(re.search(r'refus\w+|implied consent', normalized_query))
        required_codes = ['OCGA 40-6-391']
        if refusal_context:
            required_codes.extend(['OCGA 40-5-67.1', 'OCGA 40-6-392'])
        if 'weav' in normalized_query:
            required_codes.append('OCGA 40-6-48')
        existing = {item.entry.code for item in narrowed}
        pool_by_code = {entry.code: entry for entry in pool}
        top_seed = narrowed[0].score if narrowed else 62
        for code in required_codes:
            if code in existing:
                continue
            entry = pool_by_code.get(code)
            if not entry:
                continue
            narrowed.append(
                LegalMatch(
                    entry=entry,
                    score=max(54, top_seed - 6),
                    reasons=('DUI required charge-path result',),
                )
            )
            existing.add(code)
        narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if source in {'ALL', 'GEORGIA'} and drug_phrase:
        required_codes: list[str] = []
        if school_zone_drug_phrase:
            required_codes.extend(['OCGA 16-13-30', 'OCGA 16-13-30.1'])
        if minor_drug_phrase:
            required_codes.extend(['OCGA 16-13-30.3', 'OCGA 16-13-30'])
        if forged_rx_phrase:
            required_codes.extend(['OCGA 16-13-33', 'OCGA 16-13-33.1'])
        if prescription_pill_possession_phrase:
            required_codes.extend(['OCGA 16-13-30', 'OCGA 16-13-58', 'OCGA 16-13-60'])
        if meth_lab_phrase:
            required_codes.extend(['OCGA 16-13-45', 'OCGA 16-13-30'])
        if counterfeit_pill_phrase:
            required_codes.extend(['OCGA 16-13-32.4', 'OCGA 16-13-32.5'])
        if practitioner_drug_phrase:
            required_codes.extend(['OCGA 16-13-39', 'OCGA 16-13-33.1'])
        if marijuana_possession_phrase or marijuana_term_phrase:
            required_codes.extend(['OCGA 16-13-75', 'OCGA 16-13-30', 'OCGA 16-13-71'])

        if required_codes:
            required_codes = list(dict.fromkeys(required_codes))
            existing = {item.entry.code for item in narrowed}
            pool_by_code = {entry.code: entry for entry in pool}
            seed = narrowed[0].score if narrowed else 58
            for code in required_codes:
                if code in existing:
                    continue
                entry = pool_by_code.get(code)
                if not entry:
                    continue
                narrowed.append(
                    LegalMatch(
                        entry=entry,
                        score=max(52, seed - 6),
                        reasons=('Drug required result',),
                    )
                )
                existing.add(code)
            narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if source in {'ALL', 'UCMJ'} and (drug_phrase or military_drug_phrase):
        required_codes: list[str] = []
        if military_drug_phrase or any(token in normalized_query for token in ('drug', 'narcotic', 'controlled substance', 'cocaine', 'meth', 'fentanyl')):
            required_codes.append('Article 112a')
        if any(token in normalized_query for token in ('high on duty', 'drunk on duty', 'incapacitated for duty')):
            required_codes.append('Article 112')
        if required_codes:
            required_codes = list(dict.fromkeys(required_codes))
            existing = {item.entry.code for item in narrowed}
            pool_by_code = {entry.code: entry for entry in pool}
            seed = narrowed[0].score if narrowed else 58
            for code in required_codes:
                if code in existing:
                    continue
                entry = pool_by_code.get(code)
                if not entry:
                    continue
                narrowed.append(
                    LegalMatch(
                        entry=entry,
                        score=max(52, seed - 6),
                        reasons=('UCMJ drug required result',),
                    )
                )
                existing.add(code)
            narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if source in {'ALL', 'FEDERAL_USC'} and federal_phrase:
        required_codes: list[str] = []
        if any(token in normalized_query for token in ('felon', 'prohibited person', 'gun', 'firearm')):
            required_codes.append('18 USC 922(g)')
        if any(token in normalized_query for token in ('government property', 'stole government property', 'federal property')):
            required_codes.extend(['18 USC 641', '18 USC 1361'])
        if any(token in normalized_query for token in ('wire fraud', 'email fraud', 'internet fraud')):
            required_codes.append('18 USC 1343')
        if any(token in normalized_query for token in ('identity theft', 'stolen identity', 'fake identity')):
            required_codes.extend(['18 USC 1028', '18 USC 1028A'])
        if any(token in normalized_query for token in ('bank robbery', 'robbed bank')):
            required_codes.append('18 USC 2113')
        if any(token in normalized_query for token in ('mail theft', 'stole mail', 'mail matter')):
            required_codes.append('18 USC 1708')
        if any(token in normalized_query for token in ('threat across state lines', 'interstate threat')):
            required_codes.append('18 USC 875(c)')
        if any(token in normalized_query for token in (
            'domestic violence',
            'interstate domestic',
            'crossed state lines to assault',
            'intimate partner violence interstate',
        )):
            required_codes.append('18 USC 2261')
        if any(token in normalized_query for token in (
            'interstate stalking',
            'stalking across state lines',
            'harassing messages',
            'repeated threatening messages',
        )):
            required_codes.append('18 USC 2261A')
        if any(token in normalized_query for token in (
            'violated protective order',
            'restraining order violation interstate',
            'interstate protection order',
            'violated tpo across state lines',
        )):
            required_codes.append('18 USC 2262')
        if any(token in normalized_query for token in ('government computer', 'unauthorized computer access', 'hacked government computer')):
            required_codes.append('18 USC 1030')
        if any(token in normalized_query for token in ('federal facility', 'federal building', 'weapon in federal facility')):
            required_codes.append('18 USC 930')
        if any(token in normalized_query for token in ('counterfeit money', 'fake currency')):
            required_codes.append('18 USC 471')
        if required_codes:
            required_codes = list(dict.fromkeys(required_codes))
            existing = {item.entry.code for item in narrowed}
            pool_by_code = {entry.code: entry for entry in pool}
            seed = narrowed[0].score if narrowed else 56
            for code in required_codes:
                if code in existing:
                    continue
                entry = pool_by_code.get(code)
                if not entry:
                    continue
                narrowed.append(
                    LegalMatch(
                        entry=entry,
                        score=max(52, seed - 6),
                        reasons=('Federal USC context-required result',),
                    )
                )
                existing.add(code)
            narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if source in {'ALL', 'UCMJ'}:
        order_phrase = bool(any(token in normalized_query for token in ('lawful command', 'direct order', 'disobeyed order', 'refused command', 'failure to obey')))
        barracks_phrase = bool(any(token in normalized_query for token in ('barracks', 'on base', 'military housing')))
        fight_phrase = bool(any(token in normalized_query for token in ('fight', 'fighting', 'assault', 'battery', 'struck')))
        intox_phrase = bool(any(token in normalized_query for token in ('drunk', 'intoxicated', 'impaired', 'alcohol')))
        military_theft_phrase = bool(
            any(token in normalized_query for token in ('service member', 'marine', 'soldier', 'airman', 'sailor'))
            and any(token in normalized_query for token in ('stole', 'stolen', 'theft', 'wrongful appropriation', 'government property'))
        )
        required_codes: list[str] = []
        if order_phrase:
            required_codes.extend(['Article 92', 'Article 91'])
        if barracks_phrase and intox_phrase:
            required_codes.append('Article 112')
        if barracks_phrase and fight_phrase:
            required_codes.append('Article 128')
        if domestic_phrase:
            required_codes.extend(['Article 128b', 'Article 130'])
        if military_theft_phrase:
            required_codes.append('Article 121')
        if required_codes:
            required_codes = list(dict.fromkeys(required_codes))
            existing = {item.entry.code for item in narrowed}
            pool_by_code = {entry.code: entry for entry in pool}
            seed = narrowed[0].score if narrowed else 56
            for code in required_codes:
                if code in existing:
                    continue
                entry = pool_by_code.get(code)
                if not entry:
                    continue
                narrowed.append(
                    LegalMatch(
                        entry=entry,
                        score=max(53, seed - 7),
                        reasons=('UCMJ context-required result',),
                    )
                )
                existing.add(code)
            narrowed.sort(key=lambda item: (-item.score, item.entry.source, item.entry.code))
    if source == 'GEORGIA':
        primary_results = narrowed[:25]
    else:
        primary_results = narrowed[:6] if narrative_query else narrowed[:8]

    # Multi-event narrative support: merge clause-level results so officers can enter
    # "what happened" in one sentence and still get comprehensive candidate paths.
    clause_queries = _split_query_clauses(corrected_query)
    if clause_queries and strict_gating:
        clause_groups: list[list[LegalMatch]] = []
        for clause in clause_queries:
            clause_hits = search_entries(clause, source, strict_gating=True)
            if clause_hits:
                clause_groups.append(clause_hits[:8])
        if clause_groups:
            merged = _merge_ranked_results(primary_results, clause_groups)
            if source == 'GEORGIA':
                return _finalize_results(query, merged[:30])
            return _finalize_results(query, merged[:12] if narrative_query else merged[:10])
    return _finalize_results(query, primary_results)


def search_entries(query: str, source: str = 'ALL', strict_gating: bool = True) -> list[LegalMatch]:
    source = (source or 'ALL').upper()
    analysis, primary_results = _run_retrieval_pass(query, source, strict_gating=strict_gating, stage='primary')
    result_groups = [primary_results]

    if analysis.clauses:
        clause_groups: list[list[LegalMatch]] = []
        for clause in analysis.clauses[:4]:
            _, clause_results = _run_retrieval_pass(clause, source, strict_gating=False, stage='fallback')
            if clause_results:
                clause_groups.append(clause_results[:4])
        if clause_groups:
            result_groups.extend(clause_groups)

    if _needs_fallback(primary_results):
        _, fallback_results = _run_retrieval_pass(query, source, strict_gating=False, stage='fallback')
        if fallback_results:
            result_groups.append(fallback_results)

    merged = _apply_result_overlays(_merge_search_passes(result_groups), analysis, source)
    if not merged:
        return []

    top_score = merged[0].score
    floor = 22 if analysis.ocga_code or analysis.ocga_prefix or analysis.article_number else max(
        40,
        int(top_score * (0.52 if strict_gating else 0.45)),
    )
    filtered = [
        item for item in merged
        if item.score >= floor
        or 'matched exact citation' in item.reasons
        or 'matched citation' in item.reasons
        or 'matched article number' in item.reasons
    ]
    if not filtered:
        filtered = [item for item in merged[:6] if item.score >= 38]

    finalized = _finalize_results(query, filtered[:18])
    if not finalized:
        return []
    if finalized[0].certainty_bucket == 'possible' and strict_gating:
        relaxed = search_entries(query, source, strict_gating=False)
        if relaxed and relaxed[0].confidence > finalized[0].confidence:
            return relaxed
    return finalized
