# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

（特になし）

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム KabuSys の基礎機能群を実装しました。以下は主要な追加内容と実装方針の要約です。

### Added
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の MockBrokerClient を透過的に使用し、ペーパートレード用 DB（data/paper_trading.db 等）に記録する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する仕様。
  - 両スクリプトでプロセス優先度を最初に `High` に設定する処理を実装（utils.process_priority）。

- 設定管理・検証・ウィザード
  - config.py: 環境変数読み込みと Settings クラスを実装。自動でプロジェクトルートの `.env` / `.env.local` を読み込む機能、`.env` のロード順と OS 環境変数保護、PAPER_FILL_MODE 等のバリデーションを含む。
  - config_setup.py: 対話式ウィザードで `.env` を生成/更新する CLI を実装。シークレット入力のマスク表示、既存値の読み込み、確認プロンプトを提供。
  - validate_config.py: 起動前設定検証ツールを実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック、`--strict` モードをサポート。

- 監視・モニタリング
  - monitoring DB 初期化ユーティリティ（init_monitoring_db の利用）を導入し、起動時に監視テーブルの存在を保証（冪等処理）。

- 実行コンポーネント群（Execution）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てを行う実行フローを実装。RiskManager 初期設定（max_position_pct 等）を定義し、初期ポートフォリオ値を broker.get_available_cash() で取得して注入する。
  - エンジンは別スレッドで動作し、project-level の stop flag（data/stop_requested.flag）検知で安全に停止する仕組みを実装。起動時の PID ファイル管理に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナルの候補選定（スコア順、タイブレークルール）および等金額／スコア加重配分アルゴリズムを実装。スコアが全て 0 の場合のフォールバックを明記。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のセクター／レジームに対するフォールバックやログを提供。
  - portfolio.position_sizing: 単元株丸め、リスクベースおよびウェイトベースの発注株数算出（lot_size、cost_buffer、aggregate cap、スケーリングと余剰分の配分ロジック）を実装。

- リサーチ（DuckDB ベース）
  - research.factor_research: DuckDB 接続を受けモメンタム／ボラティリティ等のファクターを計算するモジュール骨格を追加（prices_daily / raw_financials テーブル参照設計）。（実装はさらに拡張予定の部分あり）

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB パス指定可能。

- ユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定する共通ユーティリティを実装。ログディレクトリ作成失敗時のフォールバックを実装。
  - utils.process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定 (high/normal/low) と CPU affinity 設定を実装。アクセス権限不足や未対応 OS を安全にスキップする設計。

### Changed
- （初回リリースに伴い既存の単一状態としての実装。今後のバージョンで分割・調整予定）

### Fixed
- 環境変数パーサの強化（config._parse_env_line）
  - export プレフィックスのサポート、シングル／ダブルクォートの中でのバックスラッシュエスケープ処理、行内コメントの扱いなどに対応し `.env` の柔軟な読み込みを実現。
- ロギング設定時のディレクトリ作成失敗をハンドルし、ファイルハンドラ作成に失敗した場合でもコンソール出力にフォールバックするよう改良。
- monitoring / execution 起動時の DB 初期化を冪等にし、存在しないスキーマでのエラーを軽減。

### Security
- config_setup の対話入力ではシークレット項目をマスクして表示。`.env` ファイルに関する注意書きを出力（Git 管理しないよう明記）。

### Notes / Known limitations
- research.factor_research の詳細算出ロジックは拡張を予定（コード内に未完の箇所あり）。
- position_sizing の lot_size は現状全銘柄共通想定。将来的に銘柄別単位（lot_map）への拡張を想定している旨を TODO コメントで明記。
- apply_sector_cap では price_map に欠損（0.0）があると過少見積りになる可能性があるため、将来的にフォールバック価格の導入を検討。

---

（以上）