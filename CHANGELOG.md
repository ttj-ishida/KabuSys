# Keep a Changelog — CHANGELOG.md

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

全般的な注記:
- 本リリースはパッケージの初期公開（v0.1.0）相当の内容をまとめたものです。
- 多くの機能は環境変数で動作が切り替え可能です（.env 自動読み込み機構と対話式ウィザードを提供）。

## [Unreleased]
- 今後のリリースに向けた未確定の変更点はここに記載します。

## [0.1.0] - 2026-04-25
初回リリース。以下の主要機能・ツール・ユーティリティを実装／提供します。

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。停止フラグ検知で安全に停止処理を呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視データを保存（監視用 DB を共通で参照）。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。
- 設定関連
  - config.py
    - Settings クラスを提供し、環境変数から各種設定（DB パス、API トークン、監視閾値、環境種別など）を取得可能。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
    - .env ファイル（.env/.env.local）の自動ロード機構を実装（OS 環境変数は保護して上書き防止）。
    - .env のパースは引用符・エスケープ・inline コメント等に対応。
  - config_setup.py
    - .env 初期作成・更新を支援する対話式ウィザード。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル、Kill Switch 設定などを対話的に設定して .env を作成可能。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数や DB パス、config/*.yaml の存在（および PyYAML があればパース検証）、本番環境の追加ガード等を検証。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順選抜（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター上限チェック（既存保有のセクター比率が閾値を超えている場合に新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数計算。単元株丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ想定）に対応。スケーリング時の端数配分アルゴリズムを実装。
- 監視・検証ツール
  - monitoring.monitoring_db (初期化機能)
    - init_monitoring_db をエントリポイントから呼び出して監視テーブルの存在を保証（冪等）。
  - tools.paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（SQLite の paper_trading DB を読み取り）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定。
    - デフォルト閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）を定義。
    - --from/--to/--db オプションで期間／DB を指定可能。
- ユーティリティ
  - utils.logging_setup
    - 統一ロギング設定ユーティリティを提供。コンソール（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラはクリアして二重登録を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - デフォルト保有ログは 30 日分（backupCount=30）。
  - utils.process_priority
    - プロセス優先度（high/normal/low）設定と CPU affinity 設定のユーティリティ（Windows / POSIX 差分を吸収）。権限不足時は警告を出してスキップ。
- research.factor_research (部分実装)
  - DuckDB を利用したファクター計算基盤（モメンタム、MA200 乖離、ATR、出来高指標等）を着手。calc_momentum などの関数雛形を含む（将来的な拡張対象）。

### Changed
- なし（初回リリースのため、既存からの変更履歴はありません）。

### Fixed
- なし（初回リリース）。

### Security
- 環境変数の取り扱いに関する注意:
  - .env ファイルは絶対にリポジトリにコミットしない旨を config_setup のヘッダに明記。
  - 必須トークン（J-Quants / KABU API パスワード）は Settings.require により未設定時に明示的エラー（ValueError）を出す設計。

### Notes / Implementation details（重要な挙動とデフォルト）
- 環境自動ロード
  - .env はプロジェクトルート（.git または pyproject.toml を探す）を基準に自動ロード。OS 環境変数が優先され、.env.local は .env を上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- Paper Trading の分離
  - 実行エンジンは paper_trading 環境時に paper_trading 用 SQLite を使用して本番 DB と完全分離する（デフォルト: data/paper_trading.db）。
  - PAPER_FILL_MODE（instant/partial/never/reject）により MockBroker の約定挙動を制御。
- 監視のデフォルト挙動
  - run_monitoring は MONITOR_POLL_INTERVAL により間隔を制御。無効値や 0 以下はデフォルト 60 秒にフォールバックして警告を出す。
  - 監視は停止フラグ（data/stop_requested.flag）で安全に終了可能。
- ロギング
  - stdout を用いた StreamHandler を採用（stderr ではない）。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続する。
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びパフォーマンス確保を試みる。権限不足時は警告で続行。

---

今後の予定（非網羅）
- research モジュールの完全実装（Momentum/Value/Volatility/Liquidity の完全実装と正規化）
- テストカバレッジ拡充（ユニットテスト／統合テスト）
- 監視・通知（LINE 連携）の強化と本番向けガードの追加

以上。問題点や補足があればお知らせください。