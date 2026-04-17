# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
この CHANGELOG は提供されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

なお、バージョン番号は src/kabusys/__init__.py の __version__ を採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
最初の公開リリース。本リリースでは、システム監視、実行エンジン、設定管理、ポートフォリオ構築ロジック、研究用ファクター計算、ユーティリティ、及び各種 CLI/ツールを含む基本機能を実装しています。

### Added
- アプリケーションパッケージの初期化とバージョン定義
  - kabusys パッケージ（__version__ = 0.1.0）

- 設定・環境変数管理
  - 自動 .env 読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）
  - 柔軟な .env パース実装（export プレフィックス、シングル/ダブルクォート、インラインコメント処理をサポート）
  - Settings クラスにより環境変数をプロパティとして提供（J-Quants / kabu / DB パス /監視閾値など）
  - PAPER_FILL_MODE 検証（有効値チェック）および paper_trading 用 sqlite パスの分離

- 設定関連 CLI
  - config_setup: 対話式 .env 作成・更新ウィザード（シークレット項目マスク、デフォルト提示、保存）
  - validate_config: 起動前設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス/親ディレクトリチェック、config/*.yaml 存在・パースチェック、--strict モード）

- 実行エンジン関連
  - run_execution: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は Mock を想定）
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動制御・停止処理
    - ユーザ定義の RiskConfig（デフォルト値を含む）を RiskManager に注入し、初期ポートフォリオ値は broker.get_available_cash() から取得

- 監視関連
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（不正値は警告を出してデフォルト 60 秒にフォールバック）
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する（monitoring 用 DB 初期化を実行）
    - stop フラグ検知による安全なループ終了、例外ハンドリングで次ポーリングに継続

- 監視 DB 初期化（monitoring_db 初期化呼び出し）
  - run_execution/run_monitoring 起動時に監視テーブルの存在を保証する初期化処理を実行（冪等）

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出（タイブレークに signal_rank ）
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合のフォールバック処理）
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有を考慮し、上限超過セクターの新規候補を除外）
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバックと警告）
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出
    - lot_size 単位丸め、max_position_pct / max_utilization 制約、cost_buffer を考慮した aggregate スケーリング処理（端数の公平配分アルゴリズム）

- 研究・ファクター計算
  - research/factor_research:
    - calc_momentum: モメンタム指標（1M/3M/6M リターン、MA200 乖離）の算出（DuckDB を用いた SQL 実装）
    - calc_volatility: ATR, 20日平均売買代金などのボラティリティ・流動性指標（部分窓対応）
    - （設計では prices_daily / raw_financials テーブルのみ参照し、外部 API にはアクセスしない）

- ツール
  - tools/paper_verification_report:
    - Paper Trading 検証レポート生成 CLI（期間指定可、PAPER_TRADING_SQLITE_PATH で DB 指定可）
    - 稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定ロジックを実装
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）

- ユーティリティ
  - utils/process_priority:
    - set_process_priority: Windows / POSIX を吸収したプロセス優先度設定（psutil ベース、権限不足や未対応 OS は安全にスキップ）
    - set_cpu_affinity: 指定コア数への CPU affinity 固定（存在しない機能や権限不足は警告でスキップ）
    - run_monitoring / run_execution で起動時に優先度を "high" に設定する呼び出しを追加

### Changed
- N/A（初回リリースのため、変更履歴はなし）

### Fixed
- N/A（初回リリースのため、修正履歴はなし）

### Security
- 環境変数・シークレットの取り扱いについて注意書きを .env テンプレートに明記（config_setup にて .env を生成する際に Git へコミットしないよう指示）

---

注記:
- 本 CHANGELOG はコードの実装内容から推測してまとめたものであり、実際の変更履歴やリリースノートは開発履歴（VCS のコミットログ等）を基に作成することを推奨します。