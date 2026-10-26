---
name: arlis-research
description: >
  Research Armenian law, identify the provisions governing a question, interpret
  those provisions and apply them to facts. Use for Armenian legal questions,
  explanations of legislation, comparisons of norms, research memoranda and
  verification of legal propositions or citations.
compatibility: >
  Requires the ARLIS MCP tools search_acts and get_act, network access to arlis.am,
  and a file reader that can open the saved Markdown files.
---

# Armenian legal research

Use ARLIS to answer the user's Armenian legal question. For an explanation of a
provision (`դրույթ`), explain who it covers, its conditions of application
(`կիրառման պայմաններ`), exceptions (`բացառություններ`) and legal consequences
(`իրավական հետևանքներ`). For a factual situation, also determine whether the
facts satisfy those conditions.
For a comparison of provisions, explain whether they supplement, limit or conflict
with each other.

The full text of the Law on Regulatory Legal Acts
(`«Նորմատիվ իրավական ակտերի մասին» օրենք`) is included here in
[Armenian](references/regulatory-legal-acts-hy.md) and
[English](references/regulatory-legal-acts.md). Read the relevant provisions when
the question requires rules on act structure, operation (`գործողություն`),
interpretation (`մեկնաբանում`), legal collisions (`իրավական կոլիզիաներ`) or
analogy (`անալոգիա`). The English file is an unofficial translation
(`ոչ պաշտոնական թարգմանություն`).

## Identify the question to be answered

Determine who is claiming a right (`իրավունք`), who may have a duty
(`պարտականություն`), and what conduct, property or legal relationship
(`իրավահարաբերություն`) the question concerns. Separate the result the
user wants from the legal explanation the user offers for it. A request to
"appeal" a document, for example, does not establish the document's legal nature
(`իրավական բնույթ`) or the available remedy (`իրավական պաշտպանության միջոց`).

Separate facts supplied by the user, facts supported by documents, disputed facts
and assumptions. If the user calls someone an employee (`աշխատող`) or owner
(`սեփականատեր`), check the requirements for that legal status (`իրավական կարգավիճակ`)
when it affects the answer. Ask for a missing fact only if it changes which law
applies or what conclusion follows.

For several questions, identify which must be answered first. Determine whether
the claimed right exists before considering how it can be enforced. If the facts
involve another country, determine the applicable law (`կիրառելի իրավունք`) and
international jurisdiction (`միջազգային ընդդատություն`) before using Armenian
substantive norms (`նյութական նորմեր`) or procedural norms (`դատավարական նորմեր`).

## Know where the regulation can be found

### Hierarchy of acts

The main levels of regulatory legal acts (`նորմատիվ իրավական ակտեր`), from
higher to lower legal force (`իրավաբանական ուժ`), are:

| Legal act (`իրավական ակտ`) | Legal relationship to the other levels |
|---|---|
| Constitution (`Սահմանադրություն`) | Has supreme legal force (`բարձրագույն իրավաբանական ուժ`). |
| Constitutional law (`սահմանադրական օրենք`) | Laws must conform to constitutional laws. Constitutional laws regulate their constitutionally assigned subjects. |
| Law (`օրենք`) | Must conform to the Constitution and constitutional laws. Secondary regulatory legal acts must conform to laws. |
| Secondary regulatory legal act (`ենթաօրենսդրական նորմատիվ իրավական ակտ`) | Is adopted under statutory authorisation (`օրենքով լիազորում`) and must conform to constitutional laws and laws. |

These relationships follow from Constitution Articles 5, 6 and 103(2). A code
(`օրենսգիրք`) is at its statutory level: the Judicial Code (`Դատական օրենսգիրք`)
is a constitutional law, while the Civil Code (`Քաղաքացիական օրենսգիրք`) is a
law. Compare laws of equal legal force by their scope and the applicable collision
rules, not by the word "Code" in a title.

Where the legal norms (`իրավական նորմեր`) of a RATIFIED international treaty
(`վավերացված միջազգային պայմանագիր`) and a law conflict, the treaty norm
applies under Constitution Article 5(3). Before relying on that provision,
check whether the treaty operates for Armenia and covers the disputed relationship.

For secondary regulatory legal acts, determine the statutory authorisation and
subject of each relevant act. The issuing body's name alone does not establish a complete order
among Government decisions (`Կառավարության որոշումներ`), ministerial orders
(`նախարարի հրամաններ`), and acts of regulatory bodies (`կարգավորող մարմիններ`)
or local self-government bodies (`տեղական ինքնակառավարման մարմիններ`).

### Starting sources by subject

Locate the following acts for the relevant subject, then read their scope and
the provisions governing the particular question:

| Question concerns | Start with |
|---|---|
| Property (`գույք`), contracts (`պայմանագրեր`), civil-law obligations (`պարտավորություններ`) or inheritance (`ժառանգություն`) | Civil Code and the special legislation (`հատուկ օրենսդրություն`) governing the property, transaction (`գործարք`) or parties (`կողմեր`) |
| Employment relationships (`աշխատանքային հարաբերություններ`) | Labour Code (`Աշխատանքային օրենսգիրք`); check whether a special public-service (`հանրային ծառայություն`) or other employment regime applies |
| Family relationships (`ընտանեկան հարաբերություններ`) | Family Code (`Ընտանեկան օրենսգիրք`) |
| Tax relationships (`հարկային հարաբերություններ`) | Tax Code (`Հարկային օրենսգիրք`) and any applicable special provisions or treaty |
| Criminal liability (`քրեական պատասխանատվություն`) | Criminal Code (`Քրեական օրենսգիրք`) |
| Administrative action (`վարչական գործողություն`) | Law on Fundamentals of Administration and Administrative Proceedings (`«Վարչարարության հիմունքների և վարչական վարույթի մասին» օրենք`) and the sectoral law (`ոլորտային օրենք`) |
| Administrative offences (`վարչական իրավախախտումներ`) | Code on Administrative Offences (`Վարչական իրավախախտումների վերաբերյալ օրենսգիրք`) and the requirements whose breach is alleged |
| Court proceedings (`դատավարություն`) | The applicable Civil Procedure Code (`Քաղաքացիական դատավարության օրենսգիրք`), Administrative Procedure Code (`Վարչական դատավարության օրենսգիրք`) or Criminal Procedure Code (`Քրեական դատավարության օրենսգիրք`) |
| Licensing (`լիցենզավորում`), permits (`թույլտվություններ`) or other sector regulation | The sectoral law and the acts adopted under its authorising norms |

Use the legal subject as the search input. If the user uses a broad everyday
word, first distinguish the possible legal meanings. A contractual penalty
(`պայմանագրային տուժանք`), administrative penalty (`վարչական տույժ`) and
criminal punishment (`քրեական պատիժ`) lead to different provisions.

### Scope of an act and division of regulation between acts

In each law you retrieve, read the provisions on its subject matter of regulation
(`կարգավորման առարկա`) and scope (`գործողության ոլորտ`), together with
definitions (`սահմանումներ`) and exclusions. Determine which persons and
relationships the law covers. Identify any provision assigning
part of the regulation to another act.

For the user's question, locate the provisions answering each necessary question:

- Who has the right or duty, and what does it concern?
- Which conditions or exceptions determine whether that right or duty exists?
- Which body may decide or act, and what powers (`լիազորություններ`) does the law give it?
- How must the person apply, act or obtain a decision?
- What facts must be proved, by whom and under what standard of proof (`ապացուցման չափանիշ`)?
- What remedy or legal consequence is available, and under which conditions?

These answers may come from several acts. A sectoral law may establish a right,
a Government decision may prescribe the procedure (`կարգ`) for applying, and a
procedural code (`դատավարական օրենսգիրք`) may govern a court challenge. Do not
expect the first act found to contain all three kinds of regulation.

If a provision contains a cross-reference (`հղում`) to another act or article,
read that referenced provision. For example, Civil Procedure Code Article 102(4)
directs the researcher to the
Law on State Duty (`«Պետական տուրքի մասին» օրենք`) for regulation of state-duty
exemptions (`պետական տուրքի վճարումից ազատում`). Follow the reference rather
than trying to derive every exemption condition from the procedural code alone.

### Statutory authorisation

An authorising norm (`լիազորող նորմ`) in a law identifies the body authorised to
adopt a specified regulation. The resulting decision (`որոշում`) or order
(`հրաման`) supplies that regulation within the authority given by the law.
The procedure itself may be in an approved annex (`հավելված`).

When the law says that a body establishes a procedure, rules (`կանոններ`), a form
(`ձև`), a list (`ցանկ`) or criteria (`չափանիշներ`), identify that body and the
exact subject it is authorised to regulate. Locate its decision or order. Read the
approving provision and the
relevant annex, then compare the requirements there with the authorising norm.
From a decision or order already found, read the law cited in its preamble
(`նախաբան`) and check the authority for the regulation being applied.

A concrete chain is the Law on Urban Development (`«Քաղաքաշինության մասին» օրենք`)
and its provisions on design permits (`նախագծման թույլտվություններ`) and
construction permits (`շինարարության թույլտվություններ`), Government Decision
N 596-Ն of 19 March 2015, and the procedure in Annex 1 of that decision. Read the
law for the authority and statutory
requirements, the annex for the prescribed permit stages, and the Administrative
Procedure Code for the form of judicial protection (`դատական պաշտպանություն`).
The Cassation Court (`Վճռաբեկ դատարան`) uses that chain in
[ՎԴ/4473/05/20](https://www.arlis.am/hy/acts/228914/latest).

If a regulation assigns a task to another body, check that body's competence
(`իրավասություն`) to perform it under the law. Consult the included Law on
Regulatory Legal Acts where the legal requirements for authorisation or
implementation affect the answer. If the required implementing act
(`իրականացումն ապահովող իրավական ակտ`) is missing, check whether the particular
statutory provision depends on its adoption or entry into force (`ուժի մեջ մտնելը`).
Examine the conditions and transitional provisions (`անցումային դրույթներ`)
before applying that conclusion to other provisions.

### Structure and priority within the same act

Use the act's actual divisions to locate the provisions: parts (`մասեր`), sections
(`բաժիններ`), chapters (`գլուխներ`), articles (`հոդվածներ`), and the article's
parts, points (`կետեր`) and sub-points (`ենթակետեր`). An article's part is
different from a larger part of the act. Secondary regulatory legal acts use points
and their subdivisions. The nested structure identifies where a provision sits;
priority in applying norms (`նորմերի կիրառման առաջնահերթություն`) follows the
applicable legal rules rather than their position in that structure.

If the code has a General Part (`ԸՆԴՀԱՆՈՒՐ ՄԱՍ`) and Special Part (`ՀԱՏՈՒԿ ՄԱՍ`),
read the relevant norms from both. For a criminal offence (`հանցանք`), for example,
the offence provision in the Special Part must be read with the applicable General
Part norms on criminal liability and sentencing (`պատժի նշանակում`). A chapter
called "General provisions" (`Ընդհանուր դրույթներ`) is not automatically a
formally designated General Part.

Distinguish those structural parts from a general norm (`ընդհանուր նորմ`) and
special norm (`հատուկ նորմ`). Compare the situations covered by the norms to
determine whether one regulates
a narrower case within the other's scope. If the norms conflict, read the
collision rules in the included Law on Regulatory Legal Acts. Check the rule
applicable to general/special norms separately from the rule applicable to
General Part/Special Part norms.

Read transitional provisions for the persons, relationships and periods they
cover. Read the relevant annex together with the provision approving it:
locate the requirements in the approved procedure or other annexed text. Read
the preamble to identify purpose and the cited statutory authorisation. Consult the
included Law on Regulatory Legal Acts for the legal requirements governing these
parts of the document.

## Choose the text and follow references in ARLIS

For current regulation, read the act's current wording (`գործող խմբագրություն`),
with amendments (`փոփոխություններ`) included. Confirm the act's title, issuing
body and applicable wording (`կիրառելի խմբագրություն`). An amendment or a
superseded act can also match the words of a search query.

Amendment notes do not require reading every amending act
(`փոփոխություններ կամ լրացումներ կատարելու մասին իրավական ակտ`). Retrieve one
only when the answer needs a provision absent from the text being read, such as
the amendment's own entry-into-force or transitional provisions. For historical
wording, locate the version applicable to the relevant period.

When a provision or preamble names another act, follow its link in the text.
If no link is supplied, search ARLIS for that act's title or the named regulation.
If the document found is an amending act, its `Acts amended by this act` links
identify the acts it changes. Read the changed act for the regulation governing
the user's question.

The metadata label `General related acts` contains links without specifying what
legal relationship each link represents. Do not assume that a linked document
is the law containing the authorising norm or the implementing act. Select a linked
document because the provision being researched refers to it, or because reading its title and
scope establishes that it supplies a rule needed for the question.

If constitutional review (`սահմանադրականության ստուգում`) affects the provision
being applied, examine the linked decision under `Unconstitutionality-related acts`.
Read the decision's operative part (`եզրափակիչ մաս`) and establish its consequences
for that provision under the Constitution and the Law on the Constitutional Court
(`«Սահմանադրական դատարանի մասին» սահմանադրական օրենք`). The metadata label
does not establish those consequences.

## Find and read the relevant court interpretations

### Cassation decisions (`Վճռաբեկ դատարանի որոշումներ`)

To find how the Cassation Court interprets the provision at issue, search for the
legal concept or a distinctive phrase from that provision in act contents.
For a question about an architectural-planning assignment
(`ճարտարապետահատակագծային առաջադրանք`), for example, search that Armenian phrase.
Among the results, identify Cassation decisions by the document title and issuing
court. If the case identifier is
already known, use it to locate the particular decision.

In the act whose provision you are analysing, the metadata block
`Judicial precedents relating to this act` can also provide links to decisions.
Read each decision used and determine whether the Cassation Court's own reasoning
(`պատճառաբանություններ`) addresses the relevant provision or legal question.
An empty block does not establish that no applicable decision exists.

In the Cassation decision you retrieve, read the stated legal question, relevant
facts, the reasoning part (`պատճառաբանական մաս`), its application to those facts
and the operative part. Separate those passages from summaries
of the lower courts' reasoning, the parties' arguments (`կողմերի փաստարկներ`) and
any separate opinion (`հատուկ կարծիք`).

Before using the decision's legal position (`իրավական դիրքորոշում`), compare its
material factual circumstances (`էական փաստական հանգամանքներ`), procedural stage
(`դատավարական փուլ`) and version of the interpreted provision with the user's
question. Explain why any difference does or does not change the application of
that position.
Look for later Cassation decisions that cite the position and determine whether
they retain, distinguish or develop it. Judicial Code Article 10(3)-(4) addresses
interpretations in cases with similar facts and justification for departure from
a Cassation interpretation (`Վճռաբեկ դատարանի մեկնաբանությունից շեղում`);
that is distinct from the operative effect of a judicial act (`դատական ակտ`)
on its addressees (`հասցեատերեր`).

If the Cassation decision being read relies on an earlier decision, locate the
earlier case in ARLIS when its reasoning is needed. If that source cannot be read,
attribute the proposition to the decision actually examined rather than claiming
that the original has been verified.

### European Court of Human Rights (ECtHR, `Մարդու իրավունքների եվրոպական դատարան`, ՄԻԵԴ)

For a question under the Convention for the Protection of Human Rights and
Fundamental Freedoms (`«Մարդու իրավունքների և հիմնարար ազատությունների պաշտպանության մասին» կոնվենցիա`),
identify the relevant Convention article and the particular issue, such as access
to a court (`դատարանի մատչելիություն`) or an effective investigation (`արդյունավետ քննություն`).
Search the Armenian wording of that issue in act contents. For example, for
access to a court under Article 6, search `դատարանի մատչելիության`.
When an ECtHR case is already identified in a Cassation decision or supplied by the
user, search its case name or application number (`գանգատի համար`) instead.

Confirm that the retrieved document is an ECtHR judgment (`վճիռ`) or decision.
Read the ECtHR's assessment of the relevant article and its numbered paragraphs
(`պարբերություններ`). Identify the conditions or standard the ECtHR applies,
then compare the facts and procedural circumstances with the matter being researched.
Distinguish the ECtHR's conclusions from the allegations of the applicant (`դիմումատու`),
the government's submissions (`Կառավարության դիտարկումներ`) and separate opinions.

Check whether the document is a Grand Chamber (`Մեծ պալատ`), Chamber (`Պալատ`)
or Committee (`Կոմիտե`) judgment or decision, and check finality (`վերջնական լինելը`)
where it matters to the question. Constitution Article 81 and Judicial Code
Article 6(2) address the role of treaty-body practice concerning human rights
(`մարդու իրավունքներ`) in interpreting fundamental rights (`հիմնական իրավունքներ`).
For a question about execution of an ECtHR judgment
(`վճռի կատարում`) against Armenia, examine its operative part and Convention
Article 46 separately from the interpretation of the substantive right (`նյութական իրավունք`).

## Reconstruct and interpret the legal norm

Read the operative provision in full, including the relevant definition, exception
and cross-reference. A legal norm may require several provisions to be read together;
one article may contain several separate norms.

For each norm needed to answer the question, identify the person or body addressed,
the required, prohibited or permitted conduct, the conditions of application and
the legal consequence. Include the applicable procedure or remedy when the user
asks how the right can be exercised or protected.

Use the statute's full Armenian legal terms consistently. If a definition controls
the result, read every condition and exclusion in that definition. Substitute
those requirements into the operative provision before applying it to the facts.
If the definition refers to another act, read that referenced text as well.

Group cumulative conditions (`միաժամանակ պահանջվող պայմաններ`) and alternative
conditions (`այլընտրանքային պայմաններ`) correctly. For `A and (B or C), unless D`,
check A, at least one of B/C, and the effect of D. Explain the grouping from the
Armenian wording and applicable language rules. Identify what each negation or
limiting phrase modifies and whether the text gives an exhaustive list (`սպառիչ ցանկ`)
or an illustrative enumeration (`օրինակային թվարկում`).

For a provision allowing discretion (`հայեցողություն`), determine who decides and
which conditions or standards govern the decision. For contracts, justify any
classification as an imperative norm (`իմպերատիվ նորմ`) or dispositive norm
(`դիսպոզիտիվ նորմ`) and determine the extent to which the law permits a different
agreement. Use the hypothesis (`հիպոթեզ`), disposition (`դիսպոզիցիա`), sanction
(`սանկցիա`) model of a legal norm only where the norm supports those components;
do not invent a component absent from the regulation.

Explain how the relevant provisions work together. Identify which creates the
right or duty, which adds a condition, which creates an exception, and which
prescribes the procedure. A procedural requirement may have different applications
depending on the substantive ground on which the procedure is used.

For an interpretive question, use the wording and grammar to identify possible
readings. Test each reading against the surrounding provisions, definitions,
the act containing the authorising norm where applicable, the regulation's purpose
and principles (`սկզբունքներ`), and the relevant Cassation or
ECtHR interpretation. Read the interpretive provisions of the included Law on
Regulatory Legal Acts and any applicable branch-specific rule.

Show the inference from the provisions to the reconstructed norm. Explain why the
selected reading respects the conditions in the connected provisions and why a
competing reading fails or remains plausible. If purpose is inferred rather than
stated in a source, say so. A short, labelled hypothetical may help show the factual
difference on which competing readings turn.

For a restriction of a fundamental right, identify its legal grounds (`իրավական հիմքեր`)
and extent.
Examine the applicable constitutional requirements, including Articles 78-80,
and the relevant Convention standard. Establish an Armenian legal basis before
using a foreign interpretive doctrine (`մեկնաբանման դոկտրին`) as a rule governing
the answer.

## Resolve overlapping or conflicting provisions

Before treating two provisions as conflicting, compare the persons, relationships,
conditions, periods and consequences each covers. Determine whether they require
incompatible results in the same situation. Requirements applying at different
stages or an exception within a general rule may explain an apparent contradiction.

For a genuine legal collision, establish the legal force of the acts and apply
the governing collision rules. Read those rules in the included Law on Regulatory
Legal Acts rather than assuming a general maxim determines priority. Explain the
applicable criterion and how its conditions are met.

For chronological priority, examine entry-into-force dates and the applicable
transitional rules, including Article 18(6)-(10) of amending law ՀՕ-175-Ն of
19 April 2021 when older acts are involved. Distinguish selection of a norm for
application from repealing (`ուժը կորցրած ճանաչելը`), declaring invalid
(`անվավեր ճանաչելը`) and revocation (`չեղյալ ճանաչելը`); establish the relevant
ground and consequence rather than using these terms interchangeably.

## Determine the applicable version and legal period

Identify the event for which the law must be determined. If that event predates
the version being read, locate the earlier text and examine whether later
regulation applies to that relationship. Check entry into force, transitional
provisions, partial operation (`մասնակի գործողություն`), temporary operation
(`ժամանակավոր գործողություն`), suspension (`գործողության կասեցում`), termination
(`գործողության դադարեցում`) and retroactive effect (`հետադարձ ուժ`) when
they affect the answer. Ask for a missing date only if it changes the result.

When deciding whether a legal change improves or worsens a person's position,
apply the relevant old and new provisions to the same facts and compare the
consequences. Include connected definitions, General Part norms, Special Part
provisions and exceptions. A changed legal label alone does not establish a
different consequence. Identify the authority for applying a later rule or
retaining an earlier one rather than mixing favourable features without a legal basis.

For a time limit (`ժամկետ`), locate the rule prescribing its duration and the rule
governing calculation of time limits (`ժամկետների հաշվարկ`). Identify the event
that starts the time limit and the actual dates. Check calendar days (`օրացուցային օրեր`)
or working days (`աշխատանքային օրեր`), suspension of the time limit's running
(`ժամկետի ընթացքի կասեցում`) or interruption (`ժամկետի ընթացքի ընդհատում`),
the rule for the last day of the time limit (`ժամկետի վերջին օր`) and the
required method of performing the action. Show the calculation and identify any
missing date or assumption that changes it. Determine the consequence of missing
the time limit from the rule governing it.

## Establish a gap before using analogy

Before finding a legislative gap (`օրենսդրական բաց`), search the general and special
regulation, its cross-references and relevant interpretations. Explain why none governs the
situation. Distinguish absence of regulation from an express exclusion, an unmet
condition or a source not yet located.

For analogy of statute (`օրենքի անալոգիա`), identify the norm regulating a similar
relationship and explain the similarity that supports applying it. For analogy of
law (`իրավունքի անալոգիա`), identify the principle of the branch of law
(`իրավունքի ճյուղ`) or general principle of law (`իրավունքի ընդհանուր սկզբունք`)
relied upon and why analogy of statute is unavailable. Read the analogy provisions
in the included Law on Regulatory Legal Acts and the particular law to determine
whether analogy is permitted.
Test the proposed application against the conditions and prohibitions in those texts.

## Apply the legal norm to the facts

For each condition in the norm established above, identify the fact that satisfies
or defeats it and explain the legal qualification (`իրավական որակում`). If that
fact is unknown or disputed, state what must be established and how the alternatives
change the answer. Where one legal category presupposes another, establish the
prerequisite (`նախապայման`) separately.

Check the relevant exception against the facts with the same care as the general
norm. Determine a remedy or measure of liability (`պատասխանատվության միջոց`)
under its own conditions rather than assuming that every breach produces the same
consequence.

Where proof (`ապացուցում`) matters, identify who bears the burden of proof
(`ապացուցման պարտականություն`), what fact must be proved and the standard for
the particular procedural stage. Distinguish rules for deciding the merits
(`գործի ըստ էության լուծում`) from rules for a procedural request
(`դատավարական դիմում կամ միջնորդություն`) or interim measure (`ժամանակավոր միջոց`).
Check applicable presumptions (`կանխավարկածներ`) and whether they can be rebutted.
Assess the supplied evidence (`ապացույցներ`) for the fact it can establish,
including relevance (`վերաբերելիություն`), admissibility (`թույլատրելիություն`),
reliability (`արժանահավատություն`) and sufficiency (`բավարարություն`) where the
procedural norms require those inquiries.

Separate an unknown fact from an assertion not supported by the supplied evidence.
Do not treat a fact as absent merely because the user has not supplied evidence
of it. State the consequence justified by the facts established under the applicable
norm, or give the conditional outcomes when a missing fact determines the result.

## Check and present the answer

Identify the exception, competing interpretation, contrary decision or unresolved
fact that could change the conclusion. Examine that material before finalising
the answer. Check each legal proposition (`իրավունքի վերաբերյալ պնդում`) against
the exact passage supporting it, including the stated conditions and exceptions.
Split a sentence into separate
claims when one citation does not support all of them.

Check the reasoning independently of the result. In a Cassation decision, read
whether the Court accepted the lower court's reasoning or retained its outcome
for different reasons. An unchanged operative result does not endorse every
proposition in the lower decision. Verify quotations and pinpoints separately
from proposition support and applicability.

Continue research to answer a specific unresolved question. If a source could not
be located in ARLIS, state that search limitation rather than treating the source
as disproved or fabricated. Once the necessary provisions and relevant competing
material have been examined, additional citations
are useful only if they contribute a further requirement, exception or legal ground.

Choose a writing structure that fits the requested answer:

| Structure | Use |
|---|---|
| Legal syllogism (`իրավաբանական սիլոգիզմ`): norm, legally qualified facts, conclusion (`եզրակացություն`) | Apply a norm; use a preceding conclusion as a premise where issues depend on each other |
| IRAC: Issue (`հարցադրում`), Rule (`կիրառելի նորմ`), Application (`կիրառում`), Conclusion | Explain an open legal question issue by issue |
| CRAC: Conclusion, Rule, Application, Conclusion | Give the conclusion first, followed by its legal basis and application |
| CREAC: Conclusion, Rule, Explanation (`բացատրություն`), Application, Conclusion | Explain the norm's interpretation before applying it |
| TREAC: Topic sentence, Rule, Explanation, Application, Conclusion | Organise an argument around a stated proposition |
| ILAC: Issue, Law, Application, Conclusion | Present governing law separately from application |
| RAC: Rule, Application, Conclusion | Answer a narrow question whose issue is already identified |

Use these structures to organise the reasoning without imposing identical headings
on every response. Give the answer and the provisions supporting it. Explain
disputed points fully and abbreviate straightforward ones. For a text explanation
without a factual scenario, explain the legal conditions and consequences without
inventing facts for an application section.

### Legal writing and citations

Integrate the authority into the sentence explaining the rule or its application.
Identify what the provision requires, permits or excludes and explain its relevance
to the question. Do not state a conclusion and then append a standalone link such
as "Article 79 of the Civil Code" in place of that explanation. Link the act and
pinpoint reference where they occur naturally in the sentence, using the ARLIS URL.
Give the act's full title on first reference and use an unambiguous short title
thereafter. Identify the actual article, part, point or sub-point; do not replace
the source's structural terms with those of another jurisdiction.

Use the language of the answer. In English, integrate references in forms such as
the following (N and M stand for verified article numbers):

- "Under Article N(1) of the Civil Code, ..."
- "Article N(3) of the Civil Code sets out an exhaustive list of ..."
- "Read together, Articles N and M require ..."
- "Although Article N permits ..., Article M limits that right where ..."

Use an exhaustive-list formulation only when the provision supports it. A reference
such as "Article 79(1)" identifies a subdivision, not the whole article; retain
further subdivisions when needed. In Armenian, integrate the reference similarly:
"Քաղաքացիական օրենսգրքի 79-րդ հոդվածի 1-ին մասի համաձայն՝ ...".
These are citation forms, not statements about what Article 79 provides.

Explain how the provisions support the conclusion. Distinguish what the
legislature expressly provides, what a court has held and
the conclusion drawn by applying those rules to the facts. Legal phrasing must
express that reasoning rather than substitute for it; do not repeat the same
introductory formula mechanically.

For a court decision, identify the court, case identifier, date and relevant
passage; use ECtHR paragraph numbers where available. Integrate the holding and
its citation into the explanation of why it applies or can be distinguished.
Distinguish quotation, paraphrase, interpretation and factual application. Preserve
the source's conditions and exceptions. Identify a missing fact, unavailable source
or unresolved interpretation where it limits the answer, and explain its effect on
the conclusion.
