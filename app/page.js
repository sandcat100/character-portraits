'use client'

import Image from 'next/image'
import styles from './page.module.css'
import {useState} from 'react'
import Description from '../components/Description'

export default function Home() {
  const [formData, setFormData] = useState(
    {
      book: "",
      character: ""         
    }
  )

  const [llmSpinner, setLlmSpinner] = useState(false)
  const [llmOutput, setLlmOutput] = useState("")

  function handleSubmit(event) {
    event.preventDefault()
    if (formData.book && formData.character) {
      setLlmSpinner(true)
      const url = `https://sandcat100--stable-diffusion-cli-llm-entrypoint-dev.modal.run?book=${encodeURIComponent(formData.book)}&character=${encodeURIComponent(formData.character)}`
      fetch(url)
      .then(response => {
        if (response.ok) {
          return response.json()
        }
        throw new Error("Bad response from Modal endpoint")
      })
      .then(data => {
        setLlmOutput(data)
        setLlmSpinner(false)
      })
      .catch(error => console.log(error))
    // setLlmOutput("slender, middle-aged man with a refined and dignified appearance, thinning silver hair, piercing blue eyes, sharp nose, elegant dress shirt, tailored suit, polished shoes")
    }
  }

  function handleFormChange(event) {
    const {name, value} = event.target
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }))
  }

  return (
    <main className={styles.main}>
      <h1>🍒 AI-generated Character Portraits 🎰</h1>
      <h2><i>~dusting off my CS degree for a hot sec~</i></h2>
      <form className="llmPromptForm" onSubmit={handleSubmit}>
        <input 
          type="text"
          name="book"
          onChange={handleFormChange}
          value={formData.book}
          placeholder="book title"
        />
        <br/>        
        <input
          type="text"
          name="character"
          onChange={handleFormChange}
          value={formData.character}
          placeholder="character name"
        />
        <br/>
        <button className="button-85">Generate prompt</button>
      </form>
      {llmSpinner && <img className="spinnerImg" src="spinner4.gif" />}
      {!llmSpinner && llmOutput && <Description llmOutput={llmOutput} />}
    </main>
  )
}
