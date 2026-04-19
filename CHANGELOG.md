# CHANGELOG

すべての notable な変更を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。  
この CHANGELOG は、与えられたコードベースから推測できる機能追加・設計上のポイントをまとめたものです。

フォーマット:
- Unreleased: 今後の変更予定 / 小さな改善点の候補
- 各リリース: 追加(Added)、変更(Changed)、修正(Fixed)、削除(Removed) など

## [Unreleased]

- ドキュメント・テスト追加の予定
- DuckDB を利用したファクター計算モジュール（research）や Strategy / Execution の統合テスト強化
- portfolio や execution のパラメータチューニング、単元株 (lot) の銘柄別対応（stocks マスタ導入）の予定
- .env のより厳密な検証・サニタイズ機能追加予定

---

## [0.1.0] - 2026-04-19
初期公開リリース。以下の主要機能を含みます（コードから推測して記載）。

### Added
- アプリケーション全体の基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定管理
  - Settings クラス (kabusys.config) による環境変数ラップとプロパティ提供
  - .env 自動読み込み:
    - プロジェクトルートを .git または pyproject.toml により検出
    - .env と .env.local の読み込み順と上書きルールを実装
    - OS 環境変数を保護する仕組みを提供
  - .env ファイルパーサ:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープを考慮してパース

- 設定操作用 CLI
  - config_setup (kabusys.config_setup): 対話式ウィザードで .env を生成／更新
    - 入力プロンプト、デフォルト値、シークレットマスク、保存確認を実装
  - validate_config (kabusys.validate_config): 起動前検証ツール
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、DB パス存在チェック、config/*.yaml の存在・パースチェック (PyYAML があればパースも実行)
    - --strict オプションで警告も失敗扱いにできる

- 実行系スクリプト
  - run_execution (kabusys/run_execution.py)
    - ExecutionEngine の起動エントリポイント（スレッドで実行）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を利用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
    - BrokerClientFactory によるブローカー／MockBroker の生成分離（環境に応じたクライアント選択）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て
    - 停止用フラグファイル (data/stop_requested.flag) と PID 管理ファイル (data/execution.pid) に対応
    - プロセス優先度を起動時に設定 (high)

  - run_monitoring (kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ実装
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB を参照）
    - 停止フラグファイルでループを終了

- 監視データベース初期化
  - init_monitoring_db 呼び出しにより監視テーブルの冪等初期化を実行

- ロギングユーティリティ
  - setup_logging (kabusys.utils.logging_setup)
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定
    - LOG_LEVEL / LOG_DIR / app_name による設定解決
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック

- プロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity (kabusys.utils.process_priority)
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収する実装
    - 権限不足や未対応プラットフォーム時は安全にスキップして警告出力

- ポートフォリオ構築モジュール
  - portfolio_builder:
    - select_candidates: スコア順で上位 N を選択
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（スコアが全て 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: 同一セクターのエクスポージャ超過を除外するフィルタ
    - calc_regime_multiplier: market レジームに応じた投下資金乗数 (bull/neutral/bear)
  - position_sizing:
    - calc_position_sizes: 複数の allocation_method (risk_based / equal / score) をサポート
    - 単元株 (lot_size) に合わせた丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap によるスケーリング処理
    - スケールダウン時の残余分配ロジック（fractions を用いた安定的な追加配分）

- リサーチ／ファクター計算（骨格）
  - research.factor_research:
    - DuckDB を用いたモメンタム等ファクター計算の設計（momentum, MA200, ATR, volume 等）
    - 関数インターフェースと定数が定義されている（実装の一部が続いている想定）

- ペーパートレード検証ツール
  - tools.paper_verification_report:
    - Paper Trading の SQLite DB を読み、システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ (avg/max/P95) を集計してレポート出力
    - PASS/FAIL 判定基準（デフォルトの閾値）を実装:
      - 稼働率 >= 99.0%
      - 注文成功率（Filled/Created） >= 90.0%
      - 送信率（Sent/Created） >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数で期間 (--from/--to) と DB パス (--db) を指定可能

### Changed
- N/A（初期リリースのため「追加」が主）

### Fixed
- N/A（初期リリースのため「修正」はなし）

### Notes / Operational details
- 環境変数とデフォルト値の主な一覧（Settings に実装）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - KILL_FLAG_CLEAR_ON_START: 0 / 1（production では 0 推奨）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の MockBroker 動作指示）
- 実行スクリプトは stop フラグファイル (data/stop_requested.flag) によって外部から安全に停止可能
- run_execution は paper_trading モードで本番 DB と完全分離して動作する設計

---

今後の改善候補（コードからの推測）
- research.factor_research の完全実装とユニットテスト
- strategy / execution の統合テスト（モックブローカーを使った E2E）
- 個別銘柄の lot_size 管理対応（stocks マスタ導入）
- .env パーサの更なる堅牢化（特殊文字列・マルチライン対応等）
- ログのメトリクス化（Prometheus 等）やより詳細な監視アラート機構の追加

以上。必要であれば、特定モジュールごとの詳細な変更点や想定される CLI の使い方、運用手順（デプロイ手順、サービス化のための systemd/cron サンプル）も追記できます。どのレベルの情報を追記しますか？