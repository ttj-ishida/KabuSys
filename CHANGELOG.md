# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

---

## [Unreleased]

### 注意 / 既知の制限
- portfolio.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討中。
- position_sizing: 将来的な拡張として銘柄別単元（lot_size）をマスタから読み込む設計が想定されている（現在は全銘柄共通の lot_size を使用）。
- research.calc_regime_multiplier: 不明なレジーム値はログ警告の上で 1.0 にフォールバックする実装。想定外の入力に注意。

---

## [0.1.0] - 2026-04-18

初回リリース。

### Added
- 基本パッケージ情報
  - kabusys パッケージの初期バージョンを 0.1.0 として追加。

- 設定管理
  - `kabusys.config`:
    - 環境設定読み込み機能。.env/.env.local を自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env ファイルのパース機能（export プレフィックス、シングル/ダブルクォート、インラインコメントの扱い等に対応）。
    - 各種設定プロパティを提供する `Settings` クラス（J-Quants トークン、kabuステーション設定、DBパス、Paper Trading 関連設定、監視しきい値、環境種別判定など）。
    - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数未設定時に明示的なエラーを出す `_require()`。

- 設定検証・ウィザード
  - `kabusys.validate_config`:
    - .env と config/*.yaml の基本検証用 CLI。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、YAML パース（PyYAML があれば）や本番環境向けガードをチェック。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。
  - `kabusys.config_setup`:
    - 対話式ウィザードによる .env の初期作成・更新サポート。多数の設定項目（KABUSYS_ENV、API キー、DB パス、ログレベル等）を対話的に入力可能。
    - 生成された .env のテンプレート書き出し機能（Git へ絶対コミットしない旨のヘッダ付き）。

- 実行系 / 監視系起動スクリプト
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
    - ブローカークライアントを `BrokerClientFactory` で生成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - 停止・強制停止用フラグファイル（data/stop_requested.flag）および PID 管理（data/execution.pid）に対応。
    - RiskManager 初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を含むデフォルト値を提供。
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境に関わらず監視は本番 sqlite_path を使用（監視は本番 DB を前提に動作する設計）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出す。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 例外発生時もログを残して次回ポーリングに継続する堅牢化。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア重み配分（スコア合計が 0 の場合は等金額にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear のマッピング（未知の値は警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）。
    - リスクベースのポジション算出、1銘柄上限、単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数配分アルゴリズムを提供。
  - `kabusys.portfolio.__init__` にて主要関数をエクスポート。

- ユーティリティ
  - `kabusys.utils.logging_setup`:
    - 統一的なログ設定ユーティリティを追加（setup_logging）。
    - stdout への StreamHandler（stdout を使用）と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢化。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - `kabusys.utils.process_priority`:
    - プロセス優先度設定（set_process_priority）: Windows と POSIX（Linux/Mac/FreeBSD）を抽象化して呼び出し側は OS を意識せず使用可能。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を提供。
    - 権限不足や非対応環境では警告を出してスキップする設計。
  - 各ユーティリティはログ出力で失敗理由を明示。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用検証レポート生成スクリプト。
    - SQLite（Paper Trading DB）を参照し、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を行う。
    - コマンドラインオプションで期間指定（--from/--to）および DB パス指定（--db）に対応。
    - P95 計算、期間フィルタリング、N/A の扱いなどを実装。基準値（稼働率 99%、成立率 90% など）はコード内定数で管理。

- 研究モジュール（骨格）
  - `kabusys.research.factor_research`:
    - モメンタム、ボラティリティ、バリュー、流動性などのファクター計算を想定したモジュールの骨格を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算（1M/3M/6M、MA200 乖離等）を実装する方針と定数を定義（実装途中の箇所あり）。

### Changed
- なし（初回リリースのため新規追加が中心）。

### Fixed
- なし（初回リリースのため修正項目なし）。

### Removed
- なし。

### Security
- なし。

---

開発者向けメモ
- CLI 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数:
  - 自動ロードされた .env/.env.local を使う場合、OS 環境変数が優先され、.env.local は .env を上書きできます。
  - 本番稼働時は KABUSYS_ENV=live の設定や LINE 通知設定等を validate_config で必ず確認してください。

--- 

（注）本 CHANGELOG は提供されたソースコードの内容・コメントから推測して作成しています。実際の実装・仕様変更がある場合は適宜更新してください。