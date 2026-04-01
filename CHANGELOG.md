CHANGELOG
=========

すべての変更は https://keepachangelog.com/ja/ の慣例に従い、Semantic Versioning に基づいて管理します。

[Unreleased]
------------

なし

0.1.0 - 2026-04-01
------------------

初期リリース。以下の主要機能と実装上のポイントを含みます。

Added
- パッケージ基盤
  - pakage エントリポイント src/kabusys/__init__.py を追加。バージョンを "0.1.0" として公開し、主要サブパッケージを __all__ で列挙（data, strategy, execution, monitoring）。
- 設定管理
  - src/kabusys/config.py: 環境変数／.env ファイルからの設定読み込み機能を実装。
    - プロジェクトルート自動検出 (.git または pyproject.toml) による .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープやインラインコメント処理に対応した .env のパーサを実装。
    - OS 環境変数の保護（protected set）を考慮した上書きロジック。
    - Settings クラスを提供し、J-Quants / kabu / Slack / データベース / 監視閾値 / システム設定等のプロパティを環境変数から取得。ENV 値・LOG_LEVEL のバリデーションや Path 型戻り値などを備える。
- データプラットフォーム
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py:
    - ETLResult データクラスによる ETL 実行結果の表現（品質チェック結果やエラー集約を含む）。
    - 差分フェッチ、バックフィル、品質チェック方針に基づく ETL の設計を実装（DuckDB 前提）。
    - パイプラインユーティリティの再エクスポート (etl.ETLResult)。
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを提供。
    - DB 値優先だが未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存を実装。
- AI / NLP
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ反映する score_news を実装。
    - 記事ウィンドウ計算（JST 基準）や記事トリム（件数・文字数）、バッチ処理（最大 20 銘柄/コール）、レスポンスの厳密なバリデーションを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、部分失敗時に他銘柄のスコアを保護する DELETE→INSERT の置換戦略などフォールトトレラント設計。
    - テスト容易性のため API 呼び出し箇所を差し替え可能に実装（モジュールローカルの _call_openai_api）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news / market_regime を用いた計算、LLM 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）や ROLLBACK のフォローアップログを実装。
- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照し、モメンタム（1M/3M/6M、MA200乖離）、ATR・流動性指標、PER/ROE を算出。
    - データ不足時の None 戻しや DuckDB のウィンドウ関数を活用した実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンでの将来リターン）、calc_ic（スピアマンランク相関 = IC）、rank（平均順位のランク化）、factor_summary（基本統計量）を提供。
    - pandas 等に依存しない純 Python + DuckDB 実装を採用。
  - src/kabusys/research/__init__.py: 主要関数の再エクスポートを追加。
- 汎用実装・堅牢性
  - 各所で「ルックアヘッドバイアス防止」の方針を徹底（datetime.today()/date.today() を直接参照しない設計、target_date を明示的に受け取る）。
  - OpenAI 呼び出しでの JSON Mode レスポンスの頑健なパース、不要テキストの除去、数値クリップ処理等を実装。
  - DuckDB に対するトランザクション（BEGIN/COMMIT/ROLLBACK）や executemany 空リスト回避（互換性対策）を実装。
  - ロギングによる情報・警告出力を多用し、異常検知とフォールバック挙動を明示。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 開発者向け補足
- OpenAI API キーの注入は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを使用。テスト用途での差し替えを想定しているため、ローカル関数のモックが可能。
- .env パーサは複雑な引用・エスケープ・インラインコメントに対応しているが、特殊ケースの互換性は .env.example を参照すること。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, market_regime など）が前提。実運用前にスキーマ整合性を確認してください。

--- 

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装（実運用・バックテスト・発注ロジック）。
- 追加の品質チェックルール、データ欠損自動修復・アラート機能の強化。
- OpenAI 呼び出しのコスト最適化やローカルML代替の導入検討。