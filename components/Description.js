import {useState, useEffect} from 'react'

export default function Description(props) {
  const [promptInput, setPromptInput] = useState(props.llmOutput)
  const [imgSrc, setImgSrc] = useState("")

  // Set the prompt input box equal to the LLM output when the LLM spits out smth
  useEffect(function() {
    setPromptInput(props.llmOutput)
  }, [props.llmOutput])

  function handlePromptInputChange(event) {
    const {value} = event.target
    setPromptInput(value)
  }

  function handleSDSubmit(event) {
    event.preventDefault()
    if (promptInput) {
      const fullPrompt = `Portrait of ${promptInput}, by Greg Rutkowski, digital painting`
      const url = 'https://sandcat100--stable-diffusion-cli-stable-diffusion-en-3ef78b-dev.modal.run'
      const data = {"prompt": fullPrompt, "samples":1, "steps": 50,"batch_size":1}
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data),
        cache: 'default'
      })
      .then(response => {
        if (response.ok) {
          return response.text()
        }
        throw new Error("Bad response from Modal endpoint")
      })
      .then(data => {
        setImgSrc(data)
      })
      .catch(error => console.log(error))    
    }
  }

  return (
    <div>
      <h2>Character description prompt for stable diffusion</h2>
      <form className="promptInput" onSubmit={handleSDSubmit}>
        <input
          type="text"
          name="promptInput"
          onChange={handlePromptInputChange}
          value={promptInput}
        />
        <button>Generate image</button>
      </form>
      <img src={`data:image/png;base64,${imgSrc}`}/>
    </div>
  )
}