# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。  

なお、以下はソースコードから推測して作成した変更履歴／リリースノートです。

## [Unreleased]

### Added
- run_monitoring.py: システム監視ループ起動スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き対応（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）検知による安全な終了処理。
  - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - Monitoring 用 DB 初期化（monitoring テーブル群の冪等な初期化）。

- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成（本番 / モックの分岐想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動。
  - エンジンはスレッドで実行、停止フラグ検知で安全停止。
  - PID ファイルパス管理。

- config.py: 設定管理と自動 .env 読み込みロジックを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で .env を読み込む。
  - .env/.env.local の読み込み順をサポート（OS 環境変数を保護する protected 機能）。
  - .env 文字列の強力なパーサを実装（シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなど）。
  - 各種設定プロパティを提供（DB パス、LINE トークン、KABU API、監視閾値、環境判定フラグ等）。
  - `PAPER_FILL_MODE` 等の列挙値検証を実施。

- portfolio モジュール（portfolio_builder / position_sizing / risk_adjustment）を追加。
  - 銘柄選定（select_candidates）、等配分・スコア加重（calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - ポジションサイズ計算（calc_position_sizes）：risk_based / equal / score の複数配分方式、lot_size 単位丸め、aggregate cap によるスケールダウンと端数処理。
  - すべて純粋関数で DB 参照なし、ドキュメントへの参照あり。

- research モジュール（factor_research / feature_exploration）を追加。
  - DuckDB 経由でのファクター計算（モメンタム・ボラティリティ・バリュー等）。
  - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリー。
  - SQL＋Python の組み合わせで高性能に実装。入力データは prices_daily / raw_financials のみ。

- ai.news_nlp: ニュース記事の OpenAI（gpt-4o-mini）によるスコアリング機能を追加。
  - ニュース収集ウィンドウ（JST→UTC 変換）計算ロジック。
  - 記事集約、バッチ（最大 20 銘柄）での API 呼び出し、JSON Mode 期待の厳密なレスポンス検証。
  - 429/ネットワーク/5xx 等に対する指数バックオフリトライ、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護のための部分置換（DELETE→INSERT）戦略。
  - API キーが未設定の場合は明示的なエラーを返す。

- tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と閾値による PASS/FAIL 判定。
  - 日付フィルタ (--from / --to) と DB パスオプション（--db / 環境変数）をサポート。
  - DB テーブルの欠如を考慮した例外ハンドリング（OperationalError を捕捉して N/A でレポート）。

- utils.process_priority: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加。
  - Windows / POSIX(Linux, Darwin, FreeBSD) の差分を吸収して nice/HIGH_PRIORITY_CLASS を操作。
  - 権限不足等の例外は警告ログに落としてスキップ。

### Changed
- Settings の挙動を明確化：
  - `Settings.is_paper` / `is_live` / `is_dev` のプロパティを追加して環境判定を容易に。
  - duckdb/sqlite のデフォルトパスをプロパティ化（環境変数で上書き可）。

- 実行/監視スクリプトのプロセス優先度設定を起動直後に行うように変更（安定稼働のため）。

- Paper Trading 周りの分離を明確化：
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで記録を本番 DB から分離。

### Fixed
- calc_score_weights: 全銘柄のスコアが 0 の場合に等金額配分でフォールバックするようにし、警告ログを追加（分母ゼロ回避）。

- factor_research / feature_exploration: SQL 組み立てやパラメータ制御で入力検証を強化（horizons の検証、NULL 傳播の扱い等）し、データ不足時に None を返す挙動を統一。

- paper_verification_report:
  - P95 計算ロジックの安定化（空リスト→None の扱い）。
  - テーブル未存在時にレポートを欠損データとして継続するハンドリングを追加。

### Security
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて無効化可能（テストや CI の安全性向上）。
- .env ロード時に OS 環境変数を保護（protected set）して意図しない上書きを防止。

---

## [0.1.0] - 2026-04-17

初回リリース。上記 Unreleased に記載の主要機能群を含む初版リリースとしてタグ付け。

### Added
- コア:
  - 基本パッケージ初期化（kabusys.__version__ = 0.1.0）。
  - 設定管理 (kabusys.config.Settings)。
  - プロジェクトルート検出と .env/.env.local 自動読み込み機構。

- 実行系:
  - 実行エンジン起動スクリプト (run_execution.py)。
  - ExecutionEngine 周辺のコンポーネント組立（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）。

- 監視:
  - システム監視ループ (run_monitoring.py)、監視 DB 初期化。

- ポートフォリオ構築:
  - 候補選定 / 重み計算 / ポジションサイズ計算 / セクター制限 / レジーム乗数。

- 研究ツール:
  - ファクター計算（momentum, volatility, value）、将来リターン、IC、統計サマリー。

- AI / NLP:
  - OpenAI を用いたニュースセンチメントスコアリング（news_nlp）。

- 開発ツール:
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）。

- ユーティリティ:
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils.process_priority）。

### Changed
- 初期設計に基づく多数の API/関数を公開（portfolio/ research/ ai/ utils）。  
- DuckDB を分析用 DB として標準利用。

### Fixed
- 初期実装段階での一般的なエラーハンドリングと入力検証を追加（NULL/ゼロ除算/データ欠損ケースへの耐性）。

### Notes / Breaking changes
- run_monitoring は KABUSYS_ENV にかかわらず「本番用の sqlite_path」を使用する実装になっています。監視データをテスト環境と分離したい場合は設定を明示的に行ってください。
- process_priority/set_cpu_affinity は権限やプラットフォームによって動作が制限されることがあります（権限不足時は警告ログでスキップ）。

---

履歴は今後の変更に応じて更新してください。必要であれば各リリースの詳細（例: コードファイル名・関数名・引数の変更差分）をさらに掘り下げて記載できます。どの粒度で記録したいか指示をください。