CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本リリース: KabuSys v0.1.0 を初回公開。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。監視は常に本番用 sqlite_path を使用する挙動を明記。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。停止フラグ / PID ファイル管理とデーモンスレッドでの実行を実装。
- 設定・環境管理
  - config.py: .env 自動ロード機能（プロジェクトルート探索）、堅牢な .env パーサ（クォートやエスケープ、inline コメント対応）、Settings クラス（環境変数アクセス用プロパティ群）を追加。環境チェック用のプロパティ（is_live/is_paper/is_dev）や paper_trading 用の PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等を実装。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。既存値の読み込み、シークレットマスキング、出力テンプレート生成をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、DB パス、config/*.yaml の存在・YAML パース（PyYAML があれば）や本番環境向けの警告等を行う。--strict モードで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等金額配分、スコア重み配分を実装（同点のタイブレーク等含む）。
  - portfolio/position_sizing.py: position size 計算（risk_based / equal / score）、単元丸め（lot_size）、aggregate cap によるスケールダウン、cost_buffer を考慮した安全な資金配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。未知レジームや price 欠損時のフォールバック挙動も明示。
  - portfolio/__init__.py: 上記 API をパッケージエクスポート。
- 実行・注文関連（骨組み）
  - execution モジュールの構成要素（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager と RiskConfig）を統合して ExecutionEngine 起動フローを構築。RiskConfig のデフォルト値や初期ポートフォリオ値に broker.get_available_cash() を使用する仕様を採用。
- 監視・運用ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール（stdout）と TimedRotatingFileHandler（日次、30 日バックアップ）をルートロガーへ設定。LOG_DIR/LOG_LEVEL 解決ロジック、ログディレクトリ作成失敗時はファイル出力をスキップして継続する挙動を実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）のプロセス優先度設定および CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合は警告でスキップする安全設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95 など）を算出、閾値判定（デフォルト閾値をコード内定義）して PASS/FAIL を出力。--from/--to/--db オプションをサポート。テーブルが存在しない場合は例外に依らず適切に N/A 扱いする防御的実装。
- 研究用モジュール（部分実装）
  - research/factor_research.py: Momentum などのファクター計算モジュールを追加（DuckDB 接続を受け prices_daily/raw_financials を参照）。設計方針や定数、計算関数のインターフェースを定義（実装は継続中の箇所あり）。

Changed
- 初期公開版として各コンポーネントの公開 API と CLI（設定ウィザード、検証ツール、起動スクリプト、レポート）を整備。
- logging_setup のデフォルト動作を stdout に統一（cron/Task Scheduler からの運用を考慮）。

Fixed / Defensive behavior
- .env パーサの堅牢化: export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、無効行スキップなどを実装して誤設定を減らす。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理を追加（0 や負の値、非整数文字列でもデフォルト 60 秒を使用し警告ログを出す）。
- process_priority / set_cpu_affinity: 権限不足や未対応機能に対して警告でスキップするようにして、起動失敗につながらない堅牢化を実施。
- logging_setup: ログディレクトリ作成失敗時はファイルハンドラを作らず StreamHandler のみで継続するように変更。
- init_monitoring_db の呼び出しを起動時に行い、監視テーブルの存在を保証（冪等処理）。
- position_sizing / risk_adjustment 等での価格欠損時の挙動を明確化し、スキップやフォールバックで安全に動くように実装。

Security
- .env 作成テンプレートとウィザードでシークレット項目はマスク表示。README・ドキュメントに .env を Git にコミットしない旨を強調（.env テンプレートヘッダに注意書き含む）。

Notes / Known issues
- research/factor_research.py の一部実装が継続中（ファイル末尾に未完の箇所あり）。ファクター計算の最終検証・最適化は別途リリース予定。
- position_sizing の lot_size は現在全銘柄共通で固定（将来的に銘柄別単元対応を検討）。
- monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様は意図的。必要であれば将来のリリースで挙動を変更して環境ごとの DB を使用するオプションを追加予定。

---

今後の予定
- factor_research の完成と単体テスト追加。
- ExecutionEngine / ブローカー実装の追加テストと paper/live の統合テスト強化。
- ドキュメント（運用手順・デプロイ手順）の整備。