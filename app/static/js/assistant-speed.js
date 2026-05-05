(function(){
  const origFetch = window.fetch;
  window.fetch = function(input, init){
    try {
      const url = (typeof input === 'string') ? input : input.url;
      if(url && url.includes('/api/assistant/ask')){
        if(window.speechSynthesis){
          const utt = new SpeechSynthesisUtterance('I heard you. Working on it.');
          utt.rate = 1.2;
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(utt);
        }
      }
    } catch(e){}
    return origFetch.apply(this, arguments);
  };
})();