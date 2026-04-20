# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__（現在: 0.1.0）に基づいています。以下は、コードベースから推測して作成した変更履歴です。

## [Unreleased]

### Added
- run_monitoring スクリプトを追加
  - SystemMonitor のポーリングループ起動用スクリプトを提供。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル (data/stop_requested.flag) による安全なシャットダウン検出。
  - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用する旨の明示。

- run_execution スクリプトを追加
  - ExecutionEngine を起動するエントリポイントを提供。
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離。
  - エンジンはデーモンスレッドで実行され、停止フラグ検知で安全に停止可能。
  - 実行中 PID を記録する pid ファイルのサポート。

- 設定管理機能の追加・拡張
  - Settings クラスを追加し、環境変数（.env の自動読み込みを含む）を一元管理。
  - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 環境変数パーサを強化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のエスケープ対応
    - 行内コメントの取り扱いを改善
  - Paper Trading 固有設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。
  - 各種しきい値（CPU/MEM/DISK）、PID/kill flag パス、ログレベル判定を実装。

- 設定ユーティリティ（CLI）を追加
  - config_setup.py: 対話式ウィザードで .env を作成・更新可能。
  - validate_config.py: 起動前に必須環境変数・パス・YAML ファイル等の検証を実行。--strict オプションで警告を失敗扱いにできる。

- ロギングとプロセス制御ユーティリティを追加
  - utils.logging_setup.setup_logging:
    - コンソール (stdout) と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority:
    - Windows / POSIX（Linux/macOS/FreeBSD）向けにプロセス優先度設定を横断的に提供。
    - CPU affinity 設定ヘルパー set_cpu_affinity を実装。
    - 権限不足等の失敗時は警告を出し安全にスキップ。

- Portfolio 構築関連の純関数群を追加
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順、タイブレークルール）
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター集中上限チェック、売却予定銘柄の除外対応）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
  - portfolio.position_sizing:
    - calc_position_sizes（risk_based / equal / score モード対応）
    - 単元株丸め、1銘柄上限、aggregate cap（資金オーバー時のスケーリング）を実装
    - cost_buffer による手数料/スリッページ考慮、残余キャッシュでの端数割当アルゴリズムを実装

- Paper Trading 検証ツールを追加
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH で指定）から各種指標を集計してレポート出力（稼働率、注文成功率、送信率、レイテンシ等）。
    - P95 計算、判定閾値（稼働率/成功率/送信率/P95 レイテンシ）を定義し PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

- research モジュール（factor_research）の基礎を追加
  - DuckDB 接続を受けてモメンタム等のファクターを計算する設計の下地を実装（関数定義、定数設定）。※実装は継続中（ファイル末尾で途切れあり）。

### Changed
- ロギングのデフォルトを stdout に統一（StreamHandler を stdout に設定）。cron/task 実行時の取り扱いを考慮。
- .env 読み込みの振る舞いを明確化（OS 環境変数を保護しつつ .env.local を上書き可能にするロード順）。
- run_monitoring/run_execution 起動時にプロセス優先度を最初に設定するよう統一。

### Fixed
- 環境変数のパースにおけるクォート / エスケープ処理の改善により、.env 内の複雑な値の読み込み不具合を回避。
- ログディレクトリ作成失敗時に例外で停止せず、コンソール出力のみで継続するように変更（耐障害性向上）。
- process_priority の OS 判定および例外ハンドリングを改善し、未対応 OS や権限不足時に安全にフォールバック。

### Security
- .env ファイルの生成ウィザードで生成されたファイルについて、README に相当する警告（.env を Git にコミットしないこと）を .env ヘッダに明示。

---

## [0.1.0] - 2026-04-20

このリリースはプロジェクトの初期公開リリース（コードベースの主要機能群をまとめたもの）として想定しています。

### Added
- コア機能
  - 実行エンジン（ExecutionEngine）起動ロジック（run_execution）。
  - 監視システムのポーリング（SystemMonitor と run_monitoring）。
  - 設定の集中管理 Settings クラス（環境変数取得、デフォルト値、バリデーション）。
  - 対話式 .env 作成ウィザード（config_setup）。
  - 設定検証 CLI（validate_config）。

- データベース / 分析連携
  - DuckDB と SQLite の接続管理（設定からパスを取得）。
  - 監視用 SQLite DB 初期化ユーティリティ（init_monitoring_db を参照する想定の呼び出し箇所）。

- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数などの純関数群を実装。

- ユーティリティ
  - ロギング設定ユーティリティ（ログローテート、stdout 出力、ログレベル解決）。
  - プロセス優先度・CPU affinity 設定ユーティリティ（クロスプラットフォーム考慮）。

- ツール
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）。

### Changed
- ログ出力の標準化（StreamHandler と 日次ローテーションファイルハンドラの組合せをデフォルト提供）。
- 環境ごとの DB 分離（paper_trading 環境用に paper_sqlite_path を明確化）。

### Fixed
- -（初期リリースのため主要な修正履歴はなし／以降のバグフィックスは Unreleased に記載）

---

注記:
- 上記はソースコードの実装内容・コメント・命名規則から推測した変更履歴です。実際のコミット履歴やリリースノートに基づくものではないため、必要に応じて日付や詳細を調整してください。