# Changelog

すべての重要な変更履歴をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

注意: 日付はコードベースから推測して付与しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能とモジュールを実装・公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）し、公開 API を __all__ で宣言。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に自動で .env/.env.local を読み込む機能を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、行内コメントの扱いなど）。
  - 必須環境変数取得ヘルパ (`_require`) と各種プロパティを提供:
    - J-Quants / kabu API / Slack トークン関連（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 監視関連設定（PID ファイル・CPU/MEM/DISK 閾値）
    - 実行環境とログレベル検証（KABUSYS_ENV, LOG_LEVEL）と便宜プロパティ（is_live, is_paper, is_dev）
- AI ニュース解析 (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当）とバッチ送信（最大 20 銘柄/チャンク）。
  - API 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンスバリデーション、スコア ±1.0 クリップ。
  - テスト用に _call_openai_api を差し替え可能に設計。
  - DuckDB 互換性考慮（executemany に空リスト不可への対応）。
- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF（1321）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等的に書き込む（score_regime）。
  - マクロ記事抽出と OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンス処理、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）。
  - ルックアヘッドバイアス回避のため、target_date 未満のみを参照する実装方針を採用。
- データプラットフォーム (src/kabusys/data/*)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダー同期ジョブ（calendar_update_job）と market_calendar を基にした営業日判定ユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未整備時の曜日ベースフォールバック、最大探索日数制限、バックフィル／整合性チェックを実装。
  - ETL パイプライン基盤 (pipeline.py, etl.py)
    - ETL 実行結果を表す ETLResult データクラスを実装（取得/保存件数・品質問題・エラー集約・シリアライズ）。
    - 差分取得・バックフィル・品質チェック設計方針（J-Quants クライアントを利用）を反映。
    - jquants_client 経由での idempotent 保存を想定（ON CONFLICT DO UPDATE）。
- 研究（Research）モジュール (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて算出する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足・欠損時の扱い（None を返す）と、営業日スキャンバッファの設定。
  - 特徴量解析 (feature_exploration.py)
    - 将来リターン算出（calc_forward_returns、複数ホライズン対応）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB のみで実装。
- 汎用ユーティリティ
  - AI モジュールと Research モジュールでの詳細なログ出力とフォールバック戦略を実装し、運用時の観測性・堅牢性を確保。
  - OpenAI クライアント利用部分は api_key 引数からの注入を許容し、テスト容易性を高める設計。

### 変更 (Changed)
- （初回リリースのため無し）

### 修正 (Fixed)
- （初回リリースのため無し）

### 破壊的変更 (Removed / Deprecated)
- （初回リリースのため無し）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能／環境変数 OPENAI_API_KEY を参照する設計。キー管理は呼び出し側で行う前提。

---

補足（設計上の重要ポイント、運用ノート）
- ルックアヘッドバイアス防止: AI モジュールと Research モジュールの主要関数は内部で datetime.today()/date.today() を参照せず、必ず caller が target_date を与えることを想定。
- DuckDB 関連: executemany に空リストを渡すと問題となるバージョン互換性への配慮が各所で行われている。
- 冪等性とトランザクション: DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の形で冪等性を確保し、例外時は ROLLBACK を試行する実装。
- テスト容易性: _call_openai_api を patch で差し替え可能にする等、ユニットテストを想定した設計・依存注入が行われている。

もし特定の変更点（例: もっと細かいファンクション単位や日付の正確な修正履歴）を追記したい場合は、どのファイル/機能について詳細を出力するか教えてください。