import React, { useState, useEffect } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import io from 'socket.io-client';
import 'react-toastify/dist/ReactToastify.css';
import './App.css'

const socket = io("ws://localhost:8080", {
  withCredentials: true,
});

function App() {
  const [name, setName] = useState(null);
  const [room, setRoom] = useState(null);
  const [info, setInfo] = useState(false);
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState([]);
  const [answered, setAnswered] = useState(false);

  const [seconds, setSeconds] = useState();
  const [scores, setScores] = useState([]);
  const [winner, setWinner] = useState();
  const [selectedAnswerIndex, setSelectedAnswerIndex] = useState(null);


  const handleSubmit = (e) => {
    e.preventDefault();

    if (name && room) {
      setInfo(true);
    }
  };

  useEffect(() => {
    if (seconds === 0) return;

    const timerInterval = setInterval(() => {
      setSeconds(prevTime => prevTime - 1);
    }, 1000);

    return () => {
      clearInterval(timerInterval);
    };
  }, [seconds]);

  useEffect(() => {
    if (name) {
      socket.emit('join_room', room, name);
    }
  }, [info]);


  useEffect(() => {
    socket.on('message', (message) => {

      toast(`${message} joined`, {
        position: "top-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
        progress: undefined,
        theme: "dark",
      });


    });
    return () => {
      socket.off('message')
    }
  }, []);

  useEffect(() => {
    socket.on('newQuestion', (data) => {
      setQuestion(data.question);
      setOptions(data.answers);
      setAnswered(false);
      setSeconds(data.timer)
      setSelectedAnswerIndex();
    });

    socket.on('answerResult', (data) => {
      if (data.isCorrect) {

        toast(`Correct! ${data.playerName} got it right.`, {
          position: "bottom-center",
          autoClose: 2000,
          hideProgressBar: false,
          closeOnClick: true,
          pauseOnHover: true,
          draggable: true,
          progress: undefined,
          theme: "dark",
        });
      }
      setScores(data.scores);
    });

    socket.on('gameOver', (data) => {
      setWinner(data.winner);
    })

    return () => {
      socket.off('newQuestion');
      socket.off('answerResult');
      socket.off('gameOver');
    };
  }, []);

  const handleAnswer = (answerIndex) => {
    if (!answered) {
      setSelectedAnswerIndex(answerIndex);
      socket.emit('submit_answer', room, answerIndex);
      setAnswered(true);
    }
  };

  if (winner) {
    return (
      <h1>winner is {winner}</h1>
    )
  }

  return (
    <div className="App">
      {!info ? (
        <div className='join-div'>
          <h1>Vocabulary Quiz</h1>
          <form onSubmit={handleSubmit}>
            <input required placeholder='Enter your name' value={name} onChange={(e) => setName(e.target.value)} />
            <input required placeholder='Enter quiz id' value={room} onChange={(e) => setRoom(e.target.value)} />
            <button type='submit' className='join-btn'>JOIN</button>
          </form>
        </div>
      ) : (
        <div>
          <h1>Vocabulary Quiz</h1>
          <p className='quiz-id'>Quiz Id: {room}</p>
          <ToastContainer />

          {question ? (

            <div className='quiz-div'>
              Remaining Time: {seconds}

              <div className='question'>
                <p className='question-text'>{question}</p>
              </div>
              <ul>
                {options.map((answer, index) => (
                  <li key={index}>
                    <button className={`options ${selectedAnswerIndex === index ? 'selected' : ''}`}
                      onClick={() => handleAnswer(index)} disabled={answered}>
                      {answer}
                    </button>
                  </li>
                ))}
              </ul>
              {scores.map((player, index) => (
                <p key={index}>{player.name}: {player.score}</p>
              ))}


            </div>
          ) : (
            <p>Loading question...</p>
          )}
        </div>
      )}
    </div>

  );
}

export default App;


