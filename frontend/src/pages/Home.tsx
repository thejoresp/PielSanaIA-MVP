import React from 'react';
import HeroSection from '../components/HeroSection';
import ImageUploader from '../components/upload/ImageUploader';
import ConditionsOverview from '../components/ConditionsOverview';

const Home: React.FC = () => {
  return (
    <div className="space-y-12 pb-12">
      <HeroSection />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <ImageUploader />
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ConditionsOverview />
      </div>
    </div>
  );
};

export default Home;