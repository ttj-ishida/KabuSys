# CHANGELOG

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" のスタイルに準拠します。

- リリース方針: 重要な機能追加、変更、バグ修正などを記載します。
- 日付はリポジトリ内のコードから推測した初回リリース日（本ファイル作成日）を使用しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-13

初回リリース。自動売買システム KabuSys のコア機能をまとめて導入します。以下はこのリリースで追加された主な機能・改善点・注意点です。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン管理を導入（kabusys.__version__ = "0.1.0"）。
  - 環境変数 / .env 読み込みユーティリティを実装（kabusys.config）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を優先）。
    - export 形式、クォート文字列、インラインコメント等を考慮したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - Settings クラスを導入し、各種設定（DB パス、API トークン、閾値、環境種別等）を中央管理。

- 実行 / 監視
  - 実行エントリポイント:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory を使ったブローカークライアント生成と、OrderManager / RiskManager / Reconciler の組み立て。
      - ExecutionEngine.run_session() によるセッション実行。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視モジュールは環境にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を監視する設計）。
  - 監視データベース初期化ユーティリティ（init_monitoring_db）を起動前に呼ぶことで監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群、DB 参照なし）。
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア順にソートして上位を選択。
      - calc_equal_weights, calc_score_weights: 等配分 / スコア加重配分を実装（全スコアが 0 の場合は等配分にフォールバックし警告を出力）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中度上限を計算して候補を除外するロジック。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知はフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash を越える場合のスケーリング）、cost_buffer による保守的見積りを実装。
      - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）を引数化。

- リサーチ（Research）
  - research パッケージを追加（DuckDB を使用し prices_daily / raw_financials を参照）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算。
      - calc_value: 財務データ（raw_financials）と価格から PER / ROE を計算。
    - feature_exploration:
      - calc_forward_returns: 各ホライズンの将来リターンをまとめて取得（デフォルト horizons=[1,5,21]）。
      - calc_ic / rank / factor_summary: IC（Spearman）の計算、ランク変換、基本統計量サマリーを実装。
    - duckdb 接続を外部から受け取り SQL＋純 Python で計算する設計。

- AI / ニュース NLP
  - ai.news_nlp モジュールを追加（raw_news → ai_scores）。
    - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア付与ロジックを実装。
    - 処理フロー:
      - タイムウィンドウ（JST 前日15:00〜当日08:30）を UTC に変換して記事を抽出。
      - 1 銘柄あたりの記事数 / 文字数上限（トリム）を設定（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄ずつのバッチで API 呼び出し（JSON Mode）を実行。
      - 429 / ネットワーク / 5xx に対する指数バックオフリトライ実装（上限あり）。
      - レスポンス検証、スコアを ±1.0 にクリップして ai_scores テーブルへ部分更新（対象コードのみ DELETE → INSERT）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError を送出）。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に接続して各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計・出力。
    - 判定基準（閾値）を定義し PASS/FAIL を判定。
    - コマンドライン引数で期間（--from / --to）および --db を受け取る。

- ユーティリティ
  - process_priority ユーティリティを追加（Windows / POSIX の差分吸収）。
    - set_process_priority(level): Windows は HIGH_PRIORITY_CLASS 等、POSIX は nice 値で "high"/"normal"/"low" を設定。権限等で失敗した場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスを制限。引数検証と例外ハンドリングあり。

### 変更 (Changed)
- 設計 / 安全性
  - DB 接続は起動スクリプトで確実に close() するように finally ブロックでクローズを行うように実装。
  - Monitoring 用テーブルの初期化は冪等に行う（init_monitoring_db を呼び出し）。
  - research/ai モジュールは外部 API や本番ブローカーへ直接アクセスしない設計（安全な分離）。

### 修正 (Fixed)
- 入力検証・堅牢性の改善
  - MONITOR_POLL_INTERVAL のパースにおいて不正値や非正の整数を検出し、警告を出してデフォルトにフォールバックする実装を追加（run_monitoring）。
  - Settings.paper_fill_mode の値検証を追加（有効値: instant/partial/never/reject）。不正値は ValueError を投げる。
  - calc_forward_returns の horizons 引数に対する検証（1〜252 の正整数のみ許容）を追加。
  - .env パーサでのクォート処理やエスケープ処理、インラインコメント処理を実装してより堅牢に。

### 注意事項 (Notes)
- 監視モジュール（run_monitoring）は「環境にかかわらず」本番 sqlite_path を使用する設計です。監視対象 DB を切り替えたい場合は環境変数 SQLITE_PATH を明示的に変更してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用に完全に分離された SQLite（デフォルト data/paper_trading.db）を使用します。本番データと混在しないよう配慮されています。
- ai.news_nlp.score_news は OpenAI API の呼び出しに依存します。OPENAI_API_KEY が未設定の場合は明示的にエラーとなるため、運用時はキー設定に注意してください。
- DuckDB を多用する設計のため、prices_daily / raw_financials / ai_scores 等のスキーマ整備とデータ整合性が前提になります。
- 一部の機能（例: position_sizing の lot_size 将来的拡張、apply_sector_cap の価格欠損処理の改善）は TODO コメントとして残しています。

### セキュリティ (Security)
- 特にこのリリースで明示的なセキュリティ修正はありません。API キーや機密情報は環境変数で扱い、.env 読み込み時にも OS 環境変数を保護する仕組み（protected set）を実装しています。

---

今後の改善案（予定）
- 単体テスト・統合テストの整備（特に DuckDB クエリ・AI 呼び出し周り）。
- ai.news_nlp の部分失敗時のより粒度の細かいロールバック戦略。
- position_sizing に銘柄別 lot_size のサポートと価格フォールバックロジックの追加。
- モニタリングのメトリクス可視化（ダッシュボード連携）やアラート通知の実装。