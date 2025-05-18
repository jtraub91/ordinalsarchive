import React, { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';

const BlockRangeSlider = () => {
  // Position states (as percentages 0-100)
  const [startPct, setStartPct] = useState(0);
  const [endPct, setEndPct] = useState(100);
  
  // Block values
  const [startValue, setStartValue] = useState(0);
  const [endValue, setEndValue] = useState('∞');
  
  // Block datetime information
  const [startDateTime, setStartDateTime] = useState('');
  const [endDateTime, setEndDateTime] = useState('');
  
  // Interaction states
  const [isDragging, setIsDragging] = useState(false);
  const [currentHandle, setCurrentHandle] = useState(null);
  
  // Blockchain data
  const [blockchainHeight, setBlockchainHeight] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Refs for DOM elements
  const containerRef = useRef(null);
  const startHandleRef = useRef(null);
  const endHandleRef = useRef(null);
  const activeTrackRef = useRef(null);
  const startInputRef = useRef(null);
  const endInputRef = useRef(null);

  // Fetch blockchain height from API
  useEffect(() => {
    setIsLoading(true);
    fetch('/block_info')
      .then(response => response.json())
      .then(data => {
        setBlockchainHeight(data.block_height);
        initializeSliderFromURL(data.block_height);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching blockchain height:', error);
        // Fallback to a reasonable default if API fails
        setBlockchainHeight(894546);
        initializeSliderFromURL(894546);
        setIsLoading(false);
      });
  }, []);

  // Function to fetch block timestamp
  const fetchBlockTimestamp = (blockHeight, isLatest = false) => {
    // For infinity or when explicitly requesting latest, don't include blockheight param
    const url = isLatest ? '/block_info' : `/block_info?blockheight=${blockHeight}`;
    
    fetch(url)
      .then(response => response.json())
      .then(data => {
        // Use the block_timestamp field from the response
        const dateString = data.block_timestamp;
        
        if (isLatest || (blockHeight === endValue && endValue === '∞')) {
          setEndDateTime(dateString);
        } else if (blockHeight === startValue || blockHeight === 0) {
          setStartDateTime(dateString);
        } else if (blockHeight === endValue) {
          setEndDateTime(dateString);
        }
      })
      .catch(error => {
        // Silent error handling
      });
  };

  // Initialize slider based on URL params
  const initializeSliderFromURL = (maxHeight) => {
    const urlParams = new URLSearchParams(window.location.search);
    const startParam = urlParams.get('start') || 0;
    const endParam = urlParams.get('end');

    // Set start position and value based on URL param
    const startBlock = parseInt(startParam) || 0;
    const startPercentage = (startBlock / maxHeight) * 100;
    setStartPct(startPercentage);
    setStartValue(startBlock);
    
    // Fetch timestamp for start block (specifically handle block 0)
    // fetchBlockTimestamp(startBlock);

    // Set end position and value based on URL param or default to infinity
    if (endParam !== null && endParam !== '') {
      const endBlock = parseInt(endParam);
      const endPercentage = (endBlock / maxHeight) * 100;
      setEndPct(endPercentage);
      setEndValue(endBlock);
      // fetchBlockTimestamp(endBlock);
    } else {
      setEndPct(100);
      setEndValue('∞');
      // Fetch latest block timestamp for infinity
      // fetchBlockTimestamp(null, true);
    }
  };

  // Update form inputs and trigger htmx when values change
  useEffect(() => {
    if (startInputRef.current && endInputRef.current) {
      // Update form inputs
      startInputRef.current.value = startValue;
      
      if (endValue === '∞') {
        endInputRef.current.value = '';
      } else {
        endInputRef.current.value = endValue;
      }

      // Trigger form change event for htmx
      const event = new Event('change', { bubbles: true });
      startInputRef.current.dispatchEvent(event);
    }
  }, [startValue, endValue]);

  // Fetch timestamps when block values change
  // useEffect(() => {
  //   fetchBlockTimestamp(startValue);
  // }, [startValue]);

  // useEffect(() => {
  //   if (endValue === '∞') {
  //     // Fetch latest block timestamp for infinity
  //     // fetchBlockTimestamp(null, true);
  //   } else {
  //     fetchBlockTimestamp(endValue);
  //   }
  // }, [endValue]);

  const handleMouseDown = (e, handle) => {
    setIsDragging(true);
    setCurrentHandle(handle);
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !containerRef.current || !blockchainHeight) return;

    const rect = containerRef.current.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const containerWidth = rect.width;
    
    // Calculate percentage (0-100) of slider width
    const newPct = Math.max(0, Math.min(100, (offsetX / containerWidth) * 100));

    if (currentHandle === 'start') {
      if (newPct < endPct - 5) { // Prevent handles from crossing (5% buffer)
        setStartPct(newPct);
        const blockValue = Math.round((newPct / 100) * blockchainHeight);
        setStartValue(blockValue);
      }
    } else if (currentHandle === 'end') {
      if (newPct > startPct + 5) { // Prevent handles from crossing (5% buffer)
        setEndPct(newPct);
        if (newPct >= 98) { // If very close to the end, set to infinity
          setEndValue('∞');
          // Will trigger the useEffect to fetch latest block timestamp
        } else {
          const blockValue = Math.round((newPct / 100) * blockchainHeight);
          setEndValue(blockValue);
        }
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setCurrentHandle(null);
  };

  // Add and remove event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, startPct, endPct, blockchainHeight]);


  return (
    <div className="w-full py-2">
      {/* Block height display */}
      <div className="flex justify-between items-center mb-1">
        <div className="text-xs font-mono">{startValue}</div>
        <div className="text-xs font-mono">{endValue}</div>
      </div>
      
      {/* Slider */}
      <div className="relative h-6 my-2" ref={containerRef}>
        {/* Background track */}
        <div 
          className="absolute w-full h-1 top-1/2 -translate-y-1/2 bg-gray-300 dark:bg-lime-500 rounded-sm" 
          id="background-track"
        ></div>
        
        {/* Active track */}
        <div 
          className="absolute h-1 top-1/2 -translate-y-1/2 bg-black dark:bg-pink-500 rounded-sm z-[5]" 
          ref={activeTrackRef}
          style={{ 
            left: `${startPct}%`, 
            width: `${endPct - startPct}%` 
          }}
        ></div>
        
        {/* Start handle */}
        <div 
          className="absolute w-4 h-4 top-1/2 -translate-y-1/2 bg-white border-2 border-black dark:border-pink-500 dark:bg-black cursor-pointer z-10" 
          ref={startHandleRef}
          style={{ 
            left: `calc(${startPct}% - 8px)` 
          }}
          onMouseDown={(e) => handleMouseDown(e, 'start')}
          onTouchStart={(e) => {
            e.preventDefault();
            handleMouseDown(e, 'start');
          }}
        ></div>
        
        {/* End handle */}
        <div 
          className="absolute w-4 h-4 top-1/2 -translate-y-1/2 bg-white border-2 border-black dark:border-pink-500 dark:bg-black cursor-pointer z-10" 
          ref={endHandleRef}
          style={{ 
            left: `calc(${endPct}% - 8px)` 
          }}
          onMouseDown={(e) => handleMouseDown(e, 'end')}
          onTouchStart={(e) => {
            e.preventDefault();
            handleMouseDown(e, 'end');
          }}
        ></div>
      </div>
      
      <div className="hidden">
        <input 
          type="hidden" 
          name="start" 
          ref={startInputRef}
          defaultValue={startValue} 
        />
        <input 
          type="hidden" 
          name="end" 
          ref={endInputRef}
          defaultValue={endValue === '∞' ? '' : endValue} 
        />
      </div>
    </div>
  );
};

// Mount the component to a DOM element with id 'block-range-slider'
const mountBlockRangeSlider = () => {
  const container = document.getElementById('block-range-slider');
  if (container) {
    const root = createRoot(container);
    root.render(<BlockRangeSlider />);
  }
};

// Export the mount function
export default mountBlockRangeSlider;

// Mount when the filters container becomes visible
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Try to mount immediately if the element exists
    const container = document.getElementById('block-range-slider');
    if (container) {
      mountBlockRangeSlider();
    }
    
    // Also set up a MutationObserver to detect when the filters container becomes visible
    const filtersContainer = document.getElementById('filters');
    if (filtersContainer) {
      // Create a MutationObserver to watch for changes to the style/class
      const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
          if (mutation.type === 'attributes' && 
              (mutation.attributeName === 'style' || mutation.attributeName === 'class')) {
            // Check if the filters container is now visible
            const isHidden = filtersContainer.classList.contains('hidden');
            const displayStyle = window.getComputedStyle(filtersContainer).display;
            
            if (!isHidden && displayStyle !== 'none') {
              // Filters are visible, mount the component
              mountBlockRangeSlider();
              // Disconnect the observer since we don't need it anymore
              observer.disconnect();
            }
          }
        }
      });
      
      // Start observing the filters container
      observer.observe(filtersContainer, { attributes: true });
      
      // Also listen for click on the filters toggle as a fallback
      const filtersToggle = document.getElementById('filters_toggle');
      if (filtersToggle) {
        filtersToggle.addEventListener('click', () => {
          setTimeout(mountBlockRangeSlider, 50);
        }, { once: true });
      }
    }
  });
}
