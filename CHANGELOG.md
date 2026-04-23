# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
日付はコードベースから推測できる情報に基づいて付与しています。

## [Unreleased]

### Added
- 基本アプリケーション構成
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = 0.1.0）。
- 起動用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り替え（paper_trading 時は専用 DB を使用）。  
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine を別スレッドで起動し停止フラグで制御。  
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定・検証ツール
  - config_setup.py: 対話式 .env ウィザードを追加。.env の生成 / 更新を支援。  
  - validate_config.py: 起動前設定検証 CLI を追加（--strict オプションで警告をエラー扱いにできる）。  
  - config.py: 自動 .env 読み込み、環境変数ラッパー Settings クラスを追加。  
    - .env/.env.local の読み込みルール（OS 環境変数を保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - 必須/オプション設定のプロパティを提供（J-Quants / kabu API / DB / 監視閾値 等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等のペーパートレード向け設定を追加。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: スコアで候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア合計 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有・当日売却予定を考慮）。"unknown" セクターは制限対象外。  
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り。
- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。StreamHandler（stdout） + TimedRotatingFileHandler（日次、30日保持）。LOG_DIR/LOG_LEVEL を尊重。
  - utils.process_priority: クロスプラットフォームのプロセス優先度および CPU affinity 設定ユーティリティ（Windows / POSIX を吸収。失敗時は警告でスキップ）。
- 監視関連
  - monitoring.monitoring_db の初期化呼び出しを各スクリプトで実行し、監視テーブル存在を保証（冪等処理）。
  - run_monitoring/run_execution で停止フラグ（data/stop_requested.flag）と pid/kill フラグパスを利用。
- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成する CLI を追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - 閾値（稼働率 99% など）をソース内に明記。--from/--to/--db オプションをサポート。
- リサーチ
  - research.factor_research の骨格を追加。モメンタム等のファクター計算ロジック設計（DuckDB を利用、prices_daily/raw_financials を参照）を開始。

### Changed
- ログ出力方針
  - stdout に出す StreamHandler を標準にし、ファイル出力は日次ローテートに変更。ファイルハンドラ作成失敗時はコンソールのみで継続する挙動。

### Fixed
- 環境変数パーサの堅牢性向上
  - config._parse_env_line においてクォート/エスケープ/インラインコメント等のパースロジックを実装し、.env の多様な記法に対応。

### Notes / Known issues
- risk_adjustment.apply_sector_cap の価格欠損時の挙動に TODO コメントあり（価格が 0.0 の場合にエクスポージャーが過少見積りされる問題）。将来的に前日終値や取得原価でフォールバックする予定。
- portfolio.position_sizing は現状 lot_size を銘柄共通で扱う。将来的に銘柄別 lot_map に拡張する余地あり（TODO コメント）。
- research.factor_research はファイル末尾で途中（start_da…）で切れており、一部実装が未完。完全実装は今後のリリース予定。
- run_monitoring は「監視は常に本番 sqlite_path を使う」設計だが、運用上の想定に注意（意図的な仕様）。

---

## [0.1.0] - 2026-04-23

初回リリース相当のまとめ（上記の機能群を含むリリース）。主に以下を含む：
- 起動スクリプト: run_execution, run_monitoring
- 環境設定: config.py, config_setup.py, validate_config.py
- ポートフォリオ構築: portfolio/（選定・重み付け・リスク調整・株数算出）
- 実行系周辺: BrokerClientFactory 経由のブローカ抽象、ExecutionEngine 起動ロジック（スレッド管理）、OrderManager / Reconciler / RiskManager の組立て（設定値はコード内にデフォルトあり）
- 監視・ロギング: monitoring_db 初期化、logging_setup、process_priority
- ツール: paper_verification_report（ペーパートレード検証レポート）
- 研究: research.factor_research（モメンタム等ファクターの設計骨格）

リリースノートはコードコメント・ドキュメント（PortfolioConstruction.md 等参照）に基づいて作成しています。実運用時は必ず validate_config.py で環境設定を検証し、.env の内容を確認してください。

---

セキュリティや互換性に関する重大な注意点:
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- KABUSYS_ENV=live 設定時は LINE 通知設定や Kill Switch 設定を特に確認すること（validate_config が注意喚起を出します）。