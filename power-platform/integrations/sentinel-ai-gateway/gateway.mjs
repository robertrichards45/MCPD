import taskContract from './tasks.json' with { type: 'json' };

const MAX_INPUT_LENGTH = 30000;
const TASKS = Object.freeze(taskContract.tasks);

/**
 * Portable reference implementation for the Sentinel AI request boundary.
 * A tenant adapter supplies the approved `SentinelAI` connection. No credentials,
 * endpoint, model, or provider-specific operation name is held by a module.
 */
export function createSentinelAiGateway(SentinelAI) {
  if (typeof SentinelAI?.ChatCompletion !== 'function') {
    throw new TypeError('The SentinelAI adapter must provide ChatCompletion(request).');
  }

  return Object.freeze({
    async dispatch({ task, input, context = {} }) {
      const profile = TASKS[task];
      if (!profile) throw new RangeError(`Unsupported Sentinel AI task: ${task}`);
      if (typeof input !== 'string' || !input.trim() || input.length > MAX_INPUT_LENGTH) {
        throw new TypeError('AI input must be nonempty text within the configured limit.');
      }
      if (context === null || typeof context !== 'object' || Array.isArray(context)) {
        throw new TypeError('AI context must be a record.');
      }
      if (profile.grounding === 'authoritative-legal-source' && !context.approvedSource) {
        throw new TypeError('LawExplain requires an authoritative source in context.');
      }
      if (profile.grounding === 'approved-sources' && !context.approvedSources) {
        throw new TypeError('ReportInspect requires approved source context.');
      }
      if (profile.grounding === 'supplied-facts' && !context.suppliedFacts) {
        throw new TypeError(`${task} requires supplied facts in context.`);
      }
      if (profile.grounding === 'approved-training-rules' && !context.approvedTrainingRules) {
        throw new TypeError('ScenarioGenerate requires approved training rules in context.');
      }
      if (profile.grounding === 'approved-training-sources' && !context.approvedTrainingSources) {
        throw new TypeError('TrainingAssist requires approved training sources in context.');
      }

      const request = {
        task,
        input: input.trim(),
        context,
        profile: { humanReview: profile.humanReview, grounding: profile.grounding }
      };
      // The only provider invocation in the shared gateway.
      const raw = await SentinelAI.ChatCompletion(request);
      const text = typeof raw === 'string' ? raw : raw?.text ?? raw?.choices?.[0]?.message?.content;
      if (typeof text !== 'string' || !text.trim()) {
        throw new Error('SentinelAI returned no usable text.');
      }
      return { task, text: text.trim(), humanReview: profile.humanReview };
    }
  });
}

export const supportedSentinelAiTasks = Object.freeze(Object.keys(TASKS));
