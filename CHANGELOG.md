CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/),
and follows SemVer.

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初回公開リリース。以下の主要コンポーネントを実装・公開。
  - パッケージ初期化
    - kabusys.__version__ = "0.1.0"
    - エクスポート: data, strategy, execution, monitoring（パッケージAPIの公開）
  - 設定 / 環境変数管理 (kabusys.config)
    - .env / .env.local ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサの実装: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント規則に対応。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
      - 必須値のバリデーション (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など)。
      - デフォルト値の提供（KABUS_API_BASE_URL, DB パスなど）、環境（development/paper_trading/live）とログレベル検証。
  - AI（自然言語処理）モジュール (kabusys.ai)
    - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
      - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
      - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC に変換）を実装。
      - バッチング（最大 20 銘柄／リクエスト）、記事数／文字数トリム、JSON モードのレスポンス検証を実装。
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ／リトライ（上限あり）。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト・code/score の検証・スコアクリップ）。
      - テスト用に _call_openai_api をモック差し替え可能。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
      - prices_daily / raw_news からのデータ取得、ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出しとスコア合成、market_regime テーブルへの冪等書き込みを実装。
      - API エラーやレスポンスパース失敗時はフォールバック（macro_sentiment=0.0）して処理継続（フェイルセーフ）。
      - リトライロジック、モデル指定、最大記事数などを設定可能。
  - Data（データプラットフォーム）モジュール (kabusys.data)
    - ETL パイプライン (kabusys.data.pipeline)
      - 差分取得・保存・品質チェックフローの下地を実装。
      - ETLResult データクラスを定義して取得数・保存数・品質問題・エラーの集約を提供。
      - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
    - ETL の再エクスポート (kabusys.data.etl)
      - ETLResult を公開インターフェースとして再エクスポート。
    - 市場カレンダー管理 (kabusys.data.calendar_management)
      - market_calendar の夜間バッチ更新ジョブ（J-Quants API から差分取得 → 保存）を実装。
      - 営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
      - DB データが部分的にしかない場合の曜日ベースフォールバック、最大探索日数制限、バックフィルの仕組みを実装。
  - Research（リサーチ）モジュール (kabusys.research)
    - ファクター計算 (kabusys.research.factor_research)
      - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。
      - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - Value: PER（price / EPS）、ROE（raw_financials から最新レコードを参照）。
      - DuckDB を用いた SQL ベース実装、データ不足時の None ハンドリング。
    - 特徴量探索 (kabusys.research.feature_exploration)
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
      - IC（Information Coefficient）計算（スピアマンの順位相関）、rank / factor_summary の実装。
      - pandas 等に依存しない純 Python 実装。
  - テスト・運用面の配慮
    - Look-ahead バイアス防止設計: 各スコアリング関数は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る。
    - OpenAI 呼び出し部分はモック差し替え可能で単体テスト容易性を確保。
    - DuckDB（ローカル分析 DB）を前提にした設計で、本番の発注 API などへのアクセスはファクター算出等では行わない旨を明記。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Required environment
- OpenAI API を用いる機能は OPENAI_API_KEY が必要（関数引数で注入可能）。
- J-Quants / kabu API / Slack に接続するための環境変数が Settings で必須とされている（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- DuckDB を前提とするため、ローカルに DuckDB があることを想定。

ライセンス / その他
- この CHANGELOG はソースから推測して作成しています。実際のリリース日やリリースノートはリポジトリ管理方針に従って更新してください。