CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

最新更新日: 2026-04-18

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
------------------

Added
- 基本的な自動売買フレームワークを実装しました（初期リリース）。
  - パッケージ情報: kabusys v0.1.0（src/kabusys/__init__.py）。
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper 用の SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離して動作します。
    - BrokerClientFactory を経由してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行します。
    - 停止制御は data/stop_requested.flag を監視し、検知時に安全に停止します。
    - 実行時に PID ファイルを書き込む仕組みを想定（pid ファイルパスを設定可能）。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - Monitoring は環境に関係なく production の sqlite_path を使用する設計。
- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を起点）。
    - .env の行パースはクォート、エスケープ、コメント等に対応する堅牢な実装。
    - Settings クラスでアプリ設定をプロパティとして提供（DB パス、API トークン、paper_trading 用設定、監視閾値など）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証を実装。
- 設定操作用ツール
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env の読み込み・更新、秘匿値マスク表示、保存前確認を提供。
  - validate_config.py: 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML があれば実施）、本番(=live)時の追加警告等を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリは引数・環境変数で制御可能。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度および CPU affinity 設定を追加（psutil を使用）。
    - Windows / POSIX（Linux, macOS 等）に対応。失敗時は警告を出して安全にスキップ。
- ポートフォリオ構築・サイズ計算モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank をタイブレークとして上位 N 件を選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供。スコア全体が 0 の場合は等配分へフォールバック（WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジックを実装。既存保有を除いたセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear) に応じた投下資金乗数を提供。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を提供。
      - risk_based: 許容リスク率、stop_loss_pct に基づく株数算出。
      - equal/score: weight に基づく配分、max_position_pct/ max_utilization に基づく上限反映。
      - lot_size による単元丸め、cost_buffer を考慮した保守的見積もり、available_cash による aggregate cap とスケーリング、端数配分ロジックを実装。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等を集計。
    - 閾値を定義して PASS/FAIL 判定を実施（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - 日付フィルタ (--from/--to) と DB パス指定オプション (--db) をサポート。
- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を実行して監視用テーブルの存在を保証（run_monitoring / run_execution 起動時に呼び出し）。

Changed
- N/A（初期リリースのため過去変更なし）

Fixed
- N/A（初期リリースのため過去修正なし）

Notes / Design decisions
- .env 自動ロードはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ出力は stdout を優先する設計（cron/スケジューラでの利用を想定）。ファイル出力は logs/ ディレクトリへ日次ローテートで保存（作成不可時は自動的にフォールバック）。
- process_priority と CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告のみを出して続行します。
- 多くのコンポーネントは外部依存（psutil, duckdb, PyYAML など）を想定しており、環境にない場合は一部機能のフォールバックや警告を行います。

Security
- 環境設定ファイル (.env) は Git 等にコミットしないことを README 等で明記してください（config_setup の出力ヘッダにも注意書きがあります）。

Acknowledgements / Future
- 今後のリリースでは ExecutionEngine / Monitoring の振る舞い詳細、ユニットテスト、エラーハンドリング強化、個別銘柄単位の lot_size 対応や外部 API のリトライ戦略などを追加予定です。