# CHANGELOG

すべての重要な変更点を「Keep a Changelog」準拠の形式で記載します。日付・バージョンはコード上の初期バージョン（__version__ = "0.1.0"）に基づいて作成しています。コード内容から推測できる主要な機能、CLI、ユーティリティ、既知の制限点などを含めています。

フォーマットの解説: ここでは主要なリリースとして v0.1.0 を記載しています（初期リリース相当）。将来的な変更は Unreleased セクションに追加してください。

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

---

## [Unreleased]

- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成
  - パッケージ初期化情報（src/kabusys/__init__.py、バージョン 0.1.0）。
- 環境・設定管理
  - Settings クラスによる環境変数ラップ（src/kabusys/config.py）。
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 設定値の検証（必須変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認）を行う CLI: validate_config（--strict オプション対応）。
  - 対話式設定ウィザード: config_setup による .env の初期作成・更新（J-Quants や kabu API、DB パス、ログレベル等を対話的にセット）。
- 実行用スクリプト / デーモン化的挙動
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フロー（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler の組み立て）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB（data/paper_trading.db など）を使用して本番 DB と分離。
    - エンジンはデーモンスレッドで実行され、停止フラグ（data/stop_requested.flag）を検知するとエンジン停止処理を行う。
    - 実行時に PID ファイルを指定してプロセス管理可能。
  - 監視プロセス起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用（監視は実 DB を参照する設計）。
    - 停止フラグを検知してループ終了。check_once 実行中の例外はログに記録して次回ポーリングに回す。
- データベース / 分析
  - DuckDB と SQLite の両方を使用する設計（各起動スクリプトで接続初期化）。DuckDB は分析用（duckdb_path）、SQLite は監視・注文履歴用（sqlite_path / paper_sqlite_path）。
- ロギング・プロセスユーティリティ
  - 統一ロギング初期化ユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみで継続）。
    - 標準出力は stdout を使用（cron 等のリダイレクトに配慮）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX (Linux / Darwin / FreeBSD) を吸収して nice 値や Windows 優先度へ変換。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足や未対応プラットフォームは警告ログを出してスキップ。
- ポートフォリオ構築（純粋関数群、メモリ内計算）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークに signal_rank を使用）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合等金額配分にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター別エクスポージャを計算して上限超過セクターの候補を除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 でフォールバックし警告）。
    - セクターエクスポージャ計算時の価格欠損に関する TODO コメントを記載（将来的にフォールバック価格を検討）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method として "risk_based" / "equal" / "score" に対応。
    - risk_based: 損切り率・リスク許容量に基づくポジション算出。
    - 等分配／スコア加重: 割合に応じた配分、lot_size（単元株）で丸め、max_position_pct／max_utilization／cost_buffer を考慮した aggregate cap のスケーリングと端数補正ロジックを実装。
- 研究用 / ファクター計算（開発中のモジュール）
  - factor_research（src/kabusys/research/factor_research.py）
    - DuckDB を使ったファクター計算設計（Momentum / Value / Volatility / Liquidity）。関数 calc_momentum などの実装が進行中（コード末尾で未完の箇所あり）。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ指標を集計してレポート（PASS/FAIL 判定）を出力。
    - P95 計算、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して判定を行う。
- その他
  - モジュール公開エントリ（portfolio パッケージの __all__）を整備。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 機密情報（API トークンやパスワード）は .env に保存する前提。config_setup は .env に平文で書き出すため、.env を絶対に Git にコミットしないよう注意喚起を出力。

### Known issues / Notes（既知の制限・将来対応メモ）
- risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャが過小評価され、ブロック判定が甘くなる可能性あり。前日終値や取得原価を用いるフォールバックの追加を検討中（TODO コメントあり）。
- research/factor_research モジュールは未完の箇所が存在（calc_momentum の途中で切れている）。
- run_monitoring は監視用 DB として常に本番 sqlite_path を使用する設計のため、テスト環境での分離を行いたい場合は手動で sqlite_path を切り替える必要がある。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム制約で失敗する可能性があり、その場合はログ警告でスキップする設計。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラを無効にして stdout のみで継続する。

---

開発・運用上の補足:
- 各 CLI（config_setup, validate_config, tools.paper_verification_report）は python -m <module> で実行可能。
- 環境変数の優先順: OS 環境 > .env.local > .env（自動ロード時）。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading（ペーパートレード）は本番 DB から分離される設計（settings.is_paper により paper_sqlite_path を使用）。

---

（注）上記はリポジトリ内のソースコードと docstring から推測してまとめた変更履歴です。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。