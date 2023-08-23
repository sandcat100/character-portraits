import {useState, useEffect} from 'react'

export default function Description(props) {
  const [promptInput, setPromptInput] = useState(props.llmOutput)
  const [imgSrcs, setImgSrcs] = useState([])
  const [sdSpinner, setSdSpinner] = useState(false)

  // Set the prompt input box equal to the LLM output when the LLM returns the response
  useEffect(function() {
    setPromptInput(props.llmOutput)
  }, [props.llmOutput])

  function handlePromptInputChange(event) {
    const {value} = event.target
    setPromptInput(value)
  }

  function generatedImgJSX() {
    return imgSrcs.map(imgSrc => 
      <div className="sdImg"><img className="sdImg" src={`data:image/png;base64,${imgSrc}`}/></div>
    )
  }

  function handleSDSubmit(event) {
    event.preventDefault()
    setSdSpinner(true)
    if (promptInput) {
      const fullPrompt = `Portrait of ${promptInput}, by Greg Rutkowski, digital painting`
      const url = 'https://sandcat100--stable-diffusion-cli-stable-diffusion-en-3ef78b-dev.modal.run'
      const data = {"prompt": fullPrompt, "samples":1, "steps": 50,"batch_size":3}
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
          return response.json()
        }
        throw new Error("Bad response from Modal endpoint")
      })
      .then(data => {
        setImgSrcs(data)
        setSdSpinner(false)
      })
      .catch(error => console.log(error))    
    }
  }

  return (
    <div>
      <form className="promptInput" onSubmit={handleSDSubmit}>
        <textarea
          name="promptInput"
          onChange={handlePromptInputChange}
          value={promptInput}
        />
        <br/>
        <button className="button-85">Generate portraits</button>
      </form>
      {sdSpinner && <img className="spinnerImg" src="spinner3.gif" />}
      <div className="imgsDiv">
        {generatedImgJSX()}
      </div>
    </div>
  )
}