const path = require('path');

module.exports = {
  mode: 'production',
  entry: {
    blockRangeSlider: './src/components/BlockRangeSlider.jsx'
  },
  output: {
    path: path.resolve(__dirname, 'ordinalsarchive/static/dist'),
    filename: '[name].js',
    library: '[name]',
    libraryTarget: 'umd',
    globalObject: 'this'
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react']
          }
        }
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  }
};
