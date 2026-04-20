# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買フレームワーク KabuSys の基礎機能を実装しました。主な追加・実装点は以下のとおりです。

### Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による終了制御を実装。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine のセッションをスレッドで実行。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検出・例外ハンドリングを含む安定化ループ。
- 設定関連
  - config.py: Settings クラスによる環境変数中心の設定管理を実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の詳細なパース実装（export KEY= 形式、クォート値のエスケープ、インラインコメントの扱い等）。
    - 各種設定プロパティ（DB パス、PID/kill flag パス、しきい値、paper_trading 用設定等）を提供。
  - config_setup.py: 対話式ウィザードにより .env の初期作成・更新を支援。
    - 質問/既存値の再利用、シークレット項目のマスク表示、保存前の確認等を実装。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパースチェック（PyYAML が存在する場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（当日売却予定銘柄はエクスポージャー計算から除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金）でのスケーリング、コストバッファの考慮、残差処理による追加配分ロジック。
- 集計・レポート
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ指標等を集計し PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ（--from / --to）、DB パス指定 (--db / 環境変数) をサポート。
- ユーティリティ
  - utils.logging_setup: 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL による設定、既存ハンドラのクリア処理、ファイル作成失敗時のフォールバック。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows (HIGH_PRIORITY_CLASS 等) と POSIX (nice) に対応。エラー時は警告を出してスキップ。
    - set_cpu_affinity によるコア固定（利用可）も提供。
- DB/分析基盤
  - DuckDB を分析用 DB として統合（duckdb 接続を利用する箇所を実装）。
  - 監視 DB 初期化用 init_monitoring_db 呼び出しを追加し、監視テーブルの存在を保証（冪等）。
- リサーチ（部分実装）
  - research.factor_research: モメンタム等のファクター計算基盤を追加（duckdb を利用）。
    - モメンタム計算に必要な定数・方針を実装。実装途中でファイル末尾が未完（作業継続中）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定しようとするため、権限不足時は警告となり動作継続する設計です。
- .env 自動読み込みは OS 環境変数を尊重し、.env.local の内容は .env をオーバーライドしますが、OS 環境変数は上書きされません。
- Paper Trading モードは発注処理を本番 API と分離することを意図しており、MockBrokerClient を経由して専用 SQLite に記録するため本番 DB への影響を回避します。
- position_sizing の集約スケーリングは lot_size 単位での丸めと残差処理を組み合わせ、利用可能現金に収まるよう配分します。
- tools.paper_verification_report はデータ欠損（テーブル未作成など）を考慮して try/except で守られており、適切に N/A を表示します。
- research.factor_research はファクター計算の骨組みを実装済みですが、いくつかのクエリ実装が未完です（今後実装予定）。

---

開発・デプロイに関する補足:
- 本リリースでは config/*.yaml のテンプレートや一部マスタデータは含まれません。validate_config で警告が出る場合は scripts/generate_config.py 等でファイル生成を行ってください（validate_config の警告メッセージ参照）。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注記あり）。

（以上）