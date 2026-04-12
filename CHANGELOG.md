CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースから推測した機能追加・変更点・既知の挙動を日本語で記載しています。

Unreleased
----------

### Added
- 監視・実行プロセス起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用の DB に記録する（本番 DB と分離）。

- 設定管理モジュールを追加/改善
  - kabusys.config.Settings: 環境変数/ .env ファイルから各種設定を取得するユーティリティを提供。
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を順に読み込み。OS 環境変数を保護するため protected ロジックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 高度な .env パーサ: export 形式・クォート・バックスラッシュエスケープ・インラインコメントを考慮した堅牢なパーサを実装。
  - 各種設定のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。

- データベース / 分離設計
  - duckdb と sqlite3 の接続サポートを追加（duckdb は分析用、sqlite は監視/発注ログなど）。
  - Paper trading 向けに paper_sqlite_path を分離（デフォルト data/paper_trading.db）。

- ポートフォリオ構築関連の純粋関数群（DB 参照なし）
  - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等金額/スコア加重の重み計算 (calc_equal_weights, calc_score_weights)。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、レジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り。

- 研究用モジュール（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（MA200、ATR20、リターン等）。
  - research.feature_exploration: 将来リターン計算、IC（スピアマンランク）算出、ファクター統計サマリー、ランク関数。
  - DuckDB 接続を受け取り SQL と Python の組合せで高速に処理する設計。

- AI ニューススコアリング
  - ai.news_nlp: raw_news / news_symbols をバッチ化して OpenAI (gpt-4o-mini) に送信し、銘柄別 ai_score を ai_scores テーブルへ書き込む処理を追加。
  - バッチ処理サイズ、トークン肥大化対策（記事数・文字数のトリム）、429/ネットワーク/5xx への指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリッピングを実装。
  - ニュースの集計ウィンドウ（JST 基準 → UTC 変換）ロジックを提供（前日 15:00 JST ～ 当日 08:30 JST を対象）。

- ユーティリティ
  - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD） を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティ。psutil を利用し権限不足や未対応環境では警告ログを出してフォールバック。

- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・送信率・レイテンシ等を集計し検証レポートを標準出力に出す CLI。期間指定（--from / --to）と DB パス指定（--db）をサポート。P95 の算出、閾値を元に PASS/FAIL 判定を出力。

### Changed
- ロガー初期化をエントリポイント側で行うように統一（basicConfig(level=INFO)）。

### Fixed
- 環境変数の妥当性チェックやフォールバック（MONITOR_POLL_INTERVAL の不正値はデフォルトへフォールバック等）を追加して堅牢性を向上。

### Known issues / Notes
- ai.news_nlp モジュールは OpenAI API キーが必須（api_key 引数または OPENAI_API_KEY 環境変数）。API 失敗時はスキップして続行する設計だが、部分的な失敗の取り扱いは慎重に運用すること。
- .env の自動ロードはプロジェクトルート探索に依存するため、配布後や非標準レイアウトでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードすることを想定。
- DuckDB に対する executemany の制約（空パラメータでの実行不可）に注意した実装がコメントとして残されている（ai モジュール内）。
- 一部関数はデータ欠損時に None を返す（ファクター計算・レイテンシ算出など）。呼び出し側で None を適切に扱うこと。

0.1.0 - 2026-04-12
------------------

初期リリース（推定）。以下を含む最小限の機能セットを提供。

### Added
- プロジェクトのメタ情報
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 実行系 / 監視
  - run_execution.py: ExecutionEngine の起動フロー（ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと実行）。
    - RiskConfig のデフォルト値群を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() から初期化。
    - paper_trading 環境では paper 用 sqlite を使用して本番 DB と完全分離。
  - run_monitoring.py: SystemMonitor の単純なポーリングループ。check_once() の例外は捕捉してログ出力後ループ継続。KeyboardInterrupt ハンドリングで正常終了。

- 設定 / 環境変数処理
  - Settings クラスに DB パス、PID/kill flag パス、閾値（CPU/MEM/DISK）、環境判定（is_live/is_paper/is_dev）などのプロパティを実装。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。

- ポートフォリオ構築
  - 候補選定 (select_candidates)、重み計算（等額/スコア）、セクター制限、レジーム乗数、ポジションサイズ計算（risk_based/equal/score）など、PortfolioConstruction の主要ロジックを実装。

- 研究ツール
  - ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、ファクター統計サマリーを提供。

- AI ニュース処理
  - ニュース収集ウィンドウ計算、OpenAI バッチ送信ロジック、入力トリム、レスポンス検証、DB 書き込み方針（部分置換による安全な更新）などを実装。

- ユーティリティ
  - process_priority と CPU affinity 設定ユーティリティを実装（psutil ベース、権限エラーは警告で処理）。

- ツール
  - paper_verification_report: Paper Trading の検証指標を出力する CLI ツール（稼働率・成功率・送信率・レイテンシ・リスク却下数・閾値判定）。

### Fixed
- .env の読み込み時にファイル読み込み失敗で warnings.warn を発行して処理を中断せず継続するようにした。

### Security
- OpenAI API キーや重要なシークレットは Settings 経由で必須チェックを行う（未設定時は ValueError を送出）。

謝辞 / 補足
----------
- 本 CHANGELOG は与えられたソースコードの内容から「推測」して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。特に運用上の注意点（DB のバックアップ、OpenAI API の利用料、環境変数の管理等）は実運用前に確認してください。