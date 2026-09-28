import assert from 'node:assert/strict';
import test from 'node:test';
import { createSentinelAiGateway, supportedSentinelAiTasks } from './gateway.mjs';

test('all task profiles use one logical provider call', async () => {
  const requests = [];
  const gateway = createSentinelAiGateway({
    async ChatCompletion(request) {
      requests.push(request);
      return { text: `Draft for ${request.task}` };
    }
  });
  for (const task of supportedSentinelAiTasks) {
    const context = task === 'LawExplain' ? { approvedSource: { citation: 'Synthetic source' } }
      : task === 'ReportInspect' ? { approvedSources: [{ title: 'Synthetic policy' }] }
      : task.startsWith('Narrative') ? { suppliedFacts: ['Synthetic fact'] }
      : task === 'ScenarioGenerate' ? { approvedTrainingRules: ['Synthetic rule'] }
      : task === 'TrainingAssist' ? { approvedTrainingSources: ['Synthetic curriculum'] }
      : {};
    const result = await gateway.dispatch({ task, input: 'Synthetic test input', context });
    assert.equal(result.task, task);
    assert.equal(result.text, `Draft for ${task}`);
    assert.equal(result.humanReview, task !== 'GeneralChat');
  }
  assert.equal(requests.length, supportedSentinelAiTasks.length);
  assert.ok(requests.every(request => !Object.hasOwn(request, 'credentials')));
});

test('invalid and ungrounded requests never reach the provider', async () => {
  let calls = 0;
  const gateway = createSentinelAiGateway({ ChatCompletion() { calls++; return 'unused'; } });
  for (const request of [
    { task: 'Other', input: 'text' },
    { task: 'GeneralChat', input: ' ' },
    { task: 'ReportInspect', input: 'text' },
    { task: 'LawExplain', input: 'text' },
    { task: 'NarrativeCreate', input: 'text' },
    { task: 'ScenarioGenerate', input: 'text' },
    { task: 'TrainingAssist', input: 'text' },
    { task: 'GeneralChat', input: 'text', context: [] }
  ]) await assert.rejects(gateway.dispatch(request));
  assert.equal(calls, 0);
});

test('one provider failure remains an error for the module to show', async () => {
  const gateway = createSentinelAiGateway({ ChatCompletion() { throw new Error('Unavailable'); } });
  await assert.rejects(gateway.dispatch({ task: 'GeneralChat', input: 'Synthetic prompt' }), /Unavailable/);
});
