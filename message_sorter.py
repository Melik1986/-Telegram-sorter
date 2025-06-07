"""Module for sorting and classifying messages."""

from classifier import ContentClassifier

class MessageSorter:
    """Class for sorting and classifying messages."""
    
    def __init__(self, classifier=None):
        """Initialize the MessageSorter with a classifier.
        
        Args:
            classifier: An instance of ContentClassifier. If None, a new instance will be created.
        """
        self.classifier = classifier or ContentClassifier()
    
    async def sort_message(self, message):
        """Sort and classify a message.
        
        Args:
            message: A dictionary containing message data with at least a 'text' field.
            
        Returns:
            A dictionary with classification results.
        """
        if not message or 'text' not in message:
            return {
                'category': 'other',
                'confidence': 0.0,
                'description': 'Empty or invalid message'
            }
        
        # Extract message text
        text = message['text']
        
        # Classify the content
        classification = await self.classifier.classify_content(text)
        
        # Return the classification results
        return classification