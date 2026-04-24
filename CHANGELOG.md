# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-24
初回公開リリース。以下の主要機能・実装を含みます。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - エンジンはスレッドで実行し、data/stop_requested.flag による停止フラグ、PID ファイル管理（data/execution.pid）に対応。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知・例外捕捉・リソースクローズ処理を実装。

- 設定管理とウィザード
  - 環境変数/設定読み込みモジュールを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出 + .env / .env.local の読み込み順、OS 環境変数保護）。
    - .env 行パーサは export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading 設定、監視閾値など）を提供。
  - .env 作成/更新を支援する対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - 各設定項目の説明・デフォルト値・シークレットマスク表示・ファイル書き込みをサポート。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の妥当性を検証するツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML の存在確認と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス優先度ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をフォールバックしてコンソールのみで継続。
  - プロセス優先度/CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS などの差分を吸収。psutil を用いた優先度変更・CPU 固定をサポート。失敗時は警告を出してスキップ。

- Execution 関連コンポーネント（呼び出し側の構成）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の起動時組立てロジックを run_execution 側に実装（実際の各モジュールは既存の実装と連携する想定）。
  - RiskManager の初期設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）および初期ポートフォリオ値を broker.get_available_cash() で取得して設定。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコア合計が 0 の場合は等分にフォールバック、警告出力）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有比率に基づき新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す。未知レジームは 1.0 にフォールバックし警告。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method="risk_based" / "equal" / "score" に対応。
    - lot_size（単元）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料/スリッページ見積り）を考慮。
    - スケーリング後の端数配分ロジック（fractional remainder に基づき lot 単位で追加配分）を実装。

- 研究/ツール
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨格（モメンタム / MA / ATR / 他）を追加（DuckDB 接続を受ける設計）。
  - ペーパートレード検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）等。
    - デフォルト基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）を定義し PASS/FAIL 判定を出力。
    - --from / --to / --db オプション、P95 計算ロジックを実装。

- DB 初期化サポート
  - 監視用 DB の初期化を idempotent に保証するため init_monitoring_db 呼び出しを追加（run_execution, run_monitoring）。

### Changed
- ログ/プロセス設定の統一
  - 全起動スクリプトで setup_logging と set_process_priority を早期に呼び出すことでログとプロセス優先度設定を統一。

- 環境変数読み込みポリシー
  - .env 自動ロードはプロジェクトルートが検出できない場合はスキップする（配布後の環境でも安全）。
  - OS 環境変数は保護（.env.local による上書き時にも OS 環境変数は保持）。

### Fixed
- リソースクリーンアップ
  - 起動スクリプトで DB 接続（sqlite3 / duckdb）を finally ブロックで必ずクローズするように修正。

- 例外・障害耐性
  - 監視ループ内で monitor.check_once() が例外を投げてもループ継続（例外時ログ出力）するようにし、単発エラーでプロセスが停止しないように改善。
  - ログディレクトリ作成やファイルハンドラ作成の失敗をハンドリングし、ファイル出力が利用できない場合はコンソール出力のみで継続するように改善。

### Notes
- 一部モジュール（ExecutionEngine 本体や Broker 実装、データベーススキーマ等）はこのリリースでは外部実装・既存実装と連携する想定です。実運用前に .env 設定、config/*.yaml の内容、Paper Trading のデータ分離設定を十分に検証してください。
- validate_config により本番環境（KABUSYS_ENV=live）用の追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を行います。live 環境での自動クリア設定は推奨されません。

---

（以後のリリースでは Unreleased セクションに変更を追記してください）