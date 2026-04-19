KEEP A CHANGELOG
=================

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
--------------------

追加
- 初回リリース: KabuSys 自動売買フレームワークの骨格を実装しました。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 環境では専用の SQLite（data/paper_trading.db）と MockBrokerClient を使用する仕組みを実装。PID ファイル管理、停止フラグ検出、スレッドでのエンジン実行・安全停止処理を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
- 設定管理・ウィザード・検証
  - config.py: 環境変数/ .env の自動読み込み、プロジェクトルート検出、必須取得ユーティリティ、各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV、paper_trading 関連など）を実装。PAPER_FILL_MODE 等のバリデーションを含む。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。主要な設定項目を対話的に入力・保存する機能。
  - validate_config.py: 起動前チェック CLI を追加。.env や config/*.yaml の存在・基本設定の妥当性検証、--strict オプションで警告を FAIL 扱いにする機能。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定を提供。コンソール（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログレベル/ログディレクトリの解決ルールを実装。
  - utils/process_priority.py: プロセス優先度（Windows の優先度クラス、POSIX の nice）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS に対するフォールバック処理を含む。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。全スコア 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中をチェックして候補を除外する機能（売却予定銘柄を除外して既存エクスポージャ計算）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。損切り、リスク割合、単元株（lot_size）、max_position/max_utilization、コストバッファを考慮した aggregate キャップとスケーリングロジックを実装。
- Execution 内の主要コンポーネント（組み立て）
  - Execution 側に BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルト設定含む）、Reconciler、ExecutionEngine の結合ロジックを実装（run_execution から利用）。
  - RiskManager の初期設定では broker.get_available_cash() を initial_portfolio_value として使用する設計。
- 監視データベース初期化
  - monitoring/monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。
- 分析用 DB
  - DuckDB 接続を利用する設計を導入（duckdb_path）。DuckDB は分析処理（research モジュール等）を想定。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算・表示し、閾値に基づく PASS/FAIL を判定。--from/--to/--db オプション対応。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に列挙。

改善・設計上の注記
- 環境自動ロード: プロジェクトルートが見つかる場合に .env / .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- paper_trading の DB 分離: paper_trading 環境では本番の monitoring DB と完全に分離された paper_sqlite_path を使用することでデータ混在を防止。
- ログディレクトリ作成失敗時のフォールバック: ファイルハンドラ作成失敗は警告してコンソール出力のみで継続。
- エラー耐性: 監視ループ・レポート生成等で DB スキーマ欠如や例外が発生しても致命的に停止しないようフォールバック処理（例: sqlite3.OperationalError の捕捉）を用意。
- 未実装・注意点（TODO）
  - position_sizing の価格欠損時のフォールバック（前日終値や取得原価の参照）についてコメントで将来的拡張を示唆。
  - research/factor_research.py はモメンタム等の計算関数を設計中（ファイル末尾が未完の状態から計算ロジックの続きが必要）。

修正
- （初回リリースのため無し）

削除
- （初回リリースのため無し）

備考
- この CHANGELOG は提供されたソースコードから推測して作成しています。実際の変更履歴やコミット単位の詳細はリポジトリの VCS 履歴（git log）を参照してください。