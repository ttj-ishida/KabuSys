# Changelog

すべての変更は Keep a Changelog の形式に従います。  
各リリースはセマンティックバージョニングに基づき記載しています。

最新の変更
==========

Unreleased
----------

（現在のワークツリーに未リリースの変更はありません）

リリース
=======

[0.1.0] - 2026-04-19
--------------------

Added
- 全体
  - 初回公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を実装。
- 環境/設定管理
  - Settings クラス（kabusys.config）を実装し、環境変数経由で各種設定を取得する仕組みを提供。
  - 自動 .env ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env ファイルパーサを実装（export KEY=val、クォート文字列、インラインコメント処理などに対応）。
  - paper_trading 用の専用 SQLite パス設定（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE のバリデーションを実装。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV により paper_trading 用の MockBroker を使用して本番 DB と分離（data/paper_trading.db）。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可、監視は本番 sqlite_path を使用。
- ロギング／プロセス制御
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を実装。コンソール(stdout) と日次ローテートファイル出力（TimedRotatingFileHandler）を設定。既存ハンドラのクリアやログディレクトリ作成のフォールバック処理あり。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。Windows/Linux/macOS に対応し、設定に失敗した場合は警告を出して安全にスキップ。
- ポートフォリオ構築
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）を実装：
    - select_candidates（スコア順で上位 N 抽出）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコア0の際は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）を実装：
    - apply_sector_cap（既存保有セクター比率が閾値を超える場合に候補除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（bull/neutral/bear の乗数、未知レジーム時は 1.0 でフォールバック）
  - 発注株数算出（kabusys.portfolio.position_sizing）を実装：
    - allocation_method に応じた株数計算（risk_based / equal / score）
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り
    - スケールダウン後の残余分配を小数端数の大きい順に lot 単位で再配分するアルゴリズムを実装
- 検証・設定ウィザード
  - validate_config: .env と config/*.yaml の静的検証ツールを実装。--strict オプションで警告も失敗扱いに。
  - config_setup: 対話型ウィザードで .env を生成/更新する CLI を実装。
- 監視／実行連携
  - 監視用 DB 初期化ユーティリティ（監視テーブル保証）を起動経路で呼び出す（起動スクリプトで冪等に初期化）。
  - run_execution: 起動時に停止フラグ検出で起動を中止、実行中も停止フラグでエンジンを停止する制御を実装。PID ファイル管理あり。
  - run_monitoring: 停止フラグファイルによるループ終了、例外時のログ出力およびポーリング継続処理を実装。
- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL を判定。CLI から期間指定および DB パス指定可。
- リサーチ（途上）
  - research/factor_research にファクター計算の骨組み（モメンタム等）を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。一部関数は実装継続中。

Changed
- logging_setup: 出力先を stderr ではなく stdout に統一（cron/task 環境でのリダイレクト対策）。
- .env 自動読み込みの優先度を OS 環境変数 > .env.local > .env の順に明確化。既存 OS 環境変数を保護するため protected を導入。
- process_priority: プラットフォーム毎の定数参照を安全化（getattr フォールバック）し、未対応 OS ではスキップするように変更。
- run_monitoring: ポーリング間隔の環境変数名を MONITOR_POLL_INTERVAL に統一し、0 以下の値や不正値はデフォルト 60 秒にフォールバックして警告を出すようにした。

Fixed
- .env パーサの実装で以下を改善:
  - export プレフィックスのサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなし値のインラインコメント判定（直前が空白/タブの場合のみコメントとみなす）
  - 無効行のスキップ処理
- logging_setup: ログディレクトリ作成失敗時にもプロセスが継続するようにし、ファイルハンドラ作成失敗はコンソール出力にフォールバック。
- position_sizing: aggregate cap 適用時のスケーリングと lot 単位の丸めで残余配分を行う際の安定性・再現性を向上（降順ソートの安定キー追加など）。

Notes
- 本リリースは初期実装フェーズです。Strategy/Execution の細部（Engine 内部、Broker 実装、DuckDB スキーマ等）は別モジュールに分かれており、将来的なリファクタ・拡張を想定しています。
- research/factor_research や一部ドキュメント（PortfolioConstruction.md 等）に言及がありますが、モジュール内で TODO コメントに示した改善点は今後の課題です。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0