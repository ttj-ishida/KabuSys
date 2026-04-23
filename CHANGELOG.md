# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの現在の状態から推測して作成しています（実装上の注意点・TODO も含む）。

## [0.1.0] - 2026-04-23

### Added
- 初回リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（data/paper_trading.db を既定）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory を使用したブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド実行と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定関連
  - config.py: 環境変数/.env のロードと Settings クラスを実装。  
    - プロジェクトルートを .git / pyproject.toml で検出し、自動で .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
    - .env のパースは引用符・エスケープ・コメントなどを考慮する堅牢な実装。  
    - 各種設定プロパティ（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値など）を提供。
  - config_setup.py: 対話式の .env 作成ウィザード。既存値の読み取り・マスク表示・保存処理を実装。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がない場合は警告）。--strict モードで警告を失敗扱いに。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティ。  
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるログファイル出力をルートロガーに設定。ログディレクトリ生成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティ。  
    - Windows / POSIX の差分を吸収し、権限不足等は警告ログでフォールバック。
- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジームはフォールバックと警告。
  - portfolio/position_sizing.py: 株数決定ロジック。  
    - risk_based / equal / score の各配分方式をサポート。  
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング処理を実装。cost_buffer による保守的コスト見積りを考慮。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト。  
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判断。CLI 引数 --from / --to / --db をサポート。
- monitoring DB 初期化ユーティリティ参照（init_monitoring_db を呼び出す箇所を導入）。
- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed / Design decisions
- 監視（run_monitoring）は環境（KABUSYS_ENV）に関係なく本番の sqlite_path を使用する設計（監視データは本番 DB に集約する意図）。
- run_execution は paper_trading 環境で paper 用 SQLite を使用することで、本番 DB と完全に分離される設計を採用。
- .env 自動読み込みの優先順:
  - OS 環境変数 > .env.local (> override) > .env（未設定時に .env を補完）を実現。OS 環境変数は保護される。

### Fixed / Robustness improvements
- .env のパース処理を堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いの改善。
  - _load_env_file による既存環境変数の保護（protected 引数）を実装。
- run_monitoring の MONITOR_POLL_INTERVAL は無効な値（非整数・0 以下）を検出してデフォルト（60 秒）へフォールバックし、警告ログを出力。
- process_priority / set_cpu_affinity は権限不足や非対応 OS をキャッチして警告ログにより安全にフォールバック。
- setup_logging はログディレクトリ作成失敗やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続。

### Known issues / TODOs
- research/factor_research.py はファイル末尾が途中で切れており（実装未完または抜粋）、モメンタム等ファクター計算の完全実装が未完の可能性あり。
- portfolio/risk_adjustment.apply_sector_cap の価格欠損 (price == 0.0) によってエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する TODO がある。
- position_sizing における lot_size の将来的拡張（銘柄別単元対応）は TODO としてコメントあり。
- validate_config の YAML 内容検証は PyYAML に依存。インストールされていない場合は内容チェックをスキップして警告する。
- SystemMonitor、ExecutionEngine 等の詳細実装は本差分で参照されているが（import されている）、この差分中にはそれらクラスのソースが含まれていない（別ファイルで実装されている想定）。

### Upgrade / Migration notes
- 初回セットアップ手順（推奨）
  1. python -m kabusys.config_setup で .env を作成。
  2. python -m kabusys.validate_config で設定検証（必要に応じて --strict を利用）。
  3. 実行:
     - 監視: python -m kabusys.run_monitoring
     - エンジン: python -m kabusys.run_execution
  4. ペーパートレードレポート: python -m kabusys.tools.paper_verification_report を使用（--db で DB 指定可）。
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。
  - KABUSYS_ENV: development / paper_trading / live のいずれか。
  - PAPER_FILL_MODE（paper_trading 用）: instant / partial / never / reject。
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB を上書きしたい場合に指定。
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。不正値は 60 秒へフォールバック。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するには 1 を設定。

### Security
- 現状、機密情報（API トークン等）は .env に保存する想定。.env は絶対に Git 等へコミットしないことをドキュメントで明記（config_setup が警告記述を出力）。

---

（注）本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のリリースノート作成時は、差分履歴（git log 等）やリリースポリシーに基づき調整してください。