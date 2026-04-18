# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（以下の履歴は提供されたコードベースの内容から推測して作成しています。）

なお、参照元コードのバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に基づき、初回公開リリースを 0.1.0 として記録しています。

## [Unreleased]

追加予定 / 進行中（コードから推測）
- research/factor_research.py のモメンタム計算機能の実装完了と追加のファクター（Value, Volatility, Liquidity）統合。
- 追加の単体テスト、CI ワークフロー、及びドキュメント（PortfolioConstruction.md / StrategyModel.md の参照整備）。
- 実行時のエラー監視・アラート機能強化（LINE 通知の運用テスト、監視閾値のチューニング）。
- ロギング設定・ログローテーションの追加オプション（圧縮・外部ログ集約対応など）。

---

## [0.1.0] - 2026-04-18

最初のリリース（提供されたコードベースの主要機能を反映）

### Added
- 基本アプリケーション・モジュールを追加
  - パッケージ基盤: src/kabusys/__init__.py（バージョン 0.1.0）
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と完全分離。  
    - BrokerClientFactory 経由でブローカークライアント（モック/実ブローカー）を生成。  
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの管理、デーモンスレッドで Engine を実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番用 sqlite_path を使用し初期化を保証。
- 設定関連
  - config.py: 環境変数 / .env 自動ロード機能（.env / .env.local をプロジェクトルートから読み込み）。  
    - 高度な .env パーサを実装（export 形式、クォート、エスケープ、インラインコメント対応）。  
    - Settings クラスで環境変数のラップ（duckdb/sqlite パス、紙取引用パス、しきい値、KABUSYS_ENV 判定など）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（secret 入力のマスク、デフォルト表示、保存機能）。
  - validate_config.py: 起動前検証 CLI を追加。  
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml 存在チェック（PyYAML の有無に依存）や本番環境向けガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）。
- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。  
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler、30日保持）。  
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度 & CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応。アクセス権限不足や未対応 OS 時は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で BUY 候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の重み算出（全スコア 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションを考慮し上限超過セクターの新規候補除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株（lot_size）丸め、個別上限・aggregate cap によるスケールダウン処理、cost_buffer を考慮した保守的見積もり。
- Paper Trading 関連ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs を参照し、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計・判定（閾値付き PASS/FAIL 判定）。  
    - コマンドライン引数で期間指定および DB パス指定可能。PAPER_TRADING_SQLITE_PATH 環境変数対応。
- データアクセス・分析
  - research/factor_research.py（骨格実装）: DuckDB 接続を受け取り、モメンタム等のファクターを計算する設計方針と一部定数定義を追加。  
    - モメンタム計算（1M/3M/6M、MA200 乖離）を想定。
- DB 初期化ユーティリティ
  - monitoring/monitoring_db.py（起動スクリプトから呼出し）により監視用テーブルの初期化を保証（init_monitoring_db）。
- その他
  - tools パッケージ初期化ファイル追加（空の __init__）。
  - utils パッケージ初期化ファイル追加（空の __init__）。
  - README / ドキュメント参照（コード内コメントから PortfolioConstruction.md / StrategyModel.md 等の存在を示唆）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合にプロセスが停止しないよう、例外発生時のフォールバックを実装（logging_setup.py）。
- process_priority.set_process_priority で未対応 OS やアクセス拒否時にプロセスが落ちないよう例外を捕捉して警告に留める実装。

### Security
- .env ファイルの取り扱いにおいて、config_setup.py が生成する .env ファイル作成時に「.env を絶対に Git にコミットしないこと」を明記。

---

脚注:
- 上記 CHANGELOG は提供されたソースコードを解析して作成した推測的な履歴です。実際のコミットログ・リリースノートがある場合はそちらを優先してください。