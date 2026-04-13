CHANGELOG
=========

すべての重要な変更を記録します。これは Keep a Changelog の慣例に準拠しています。
（以下の変更点は提供されたコードベースから推測して作成しています。実際のコミット履歴とは差異がある可能性があります。）

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 実行用エントリポイントを追加／整備
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV によって paper_trading モード時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db をデフォルト）へ完全に分離して記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。

- 設定／環境変数周りの改善
  - config.py: .env ファイルの自動読み込み機能を実装（プロジェクトルートの .git または pyproject.toml を探索）。.env と .env.local の読み込み順序を定義し、OS 環境変数を保護する仕組みを導入。
  - .env パーサを強化: コメント処理、export プレフィックス対応、クォート内のエスケープ処理などの取り扱いを実装。
  - Settings クラスを実装し、各種設定値（DB パス、PID ファイルパス、kill flag、しきい値、環境種別判定、ログレベルなど）をプロパティとして提供。バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の妥当性チェック）を追加。

- 監視・モニタリング
  - init_monitoring_db を利用して監視用テーブルの初期化を行う（冪等実行）。
  - run_monitoring が常に本番用の sqlite_path を参照する旨を明記（モニタリングは環境に依存しない動作）。

- Execution 周りの組み立て
  - ExecutionEngine 起動時の依存組み立てを実装（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler など）。
  - RiskManager の設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで組み込み、初期ポートフォリオ値をブローカーの available_cash から初期化。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコアが 0 の場合のフォールバック処理あり）を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score の allocation_method 対応）、単元株（lot_size）での丸め処理、aggregate cap によるスケーリング処理、cost_buffer を考慮した保守的見積りなどを実装。

- 研究（research）モジュール
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベース実装）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）などのユーティリティを実装。
  - research パッケージの __all__ を整備し、zscore_normalize（外部モジュールから）も公開。

- AI / ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む処理を実装。複数銘柄のバッチ処理、トークン肥大化対策（記事・文字数トリム）、レスポンスのバリデーション、429/5xx 等に対する指数バックオフによるリトライ実装などを含む。
  - ニュース集計ウィンドウ計算（JST→UTC 変換）ユーティリティ calc_news_window を実装。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を SQLite（paper_trading DB）から集計して標準出力に整形出力する。
  - レポートの閾値（稼働率 99%、注文成功率 90% など）と P95 計算ロジック（独自パーセンタイル実装）を導入。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを実装（Windows と POSIX の差分を吸収）。権限不足や未対応環境でのフォールバック処理・警告出力あり。

Changed
- パッケージ初期化
  - kabusys.__init__ にバージョン識別子 __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ に列挙。

- DB 接続の取り扱い
  - run_execution/run_monitoring で sqlite3 と duckdb の両方を接続して使用する構成へ統一。duckdb_path の既定値は data/kabusys.duckdb。

Fixed
- 安全性・耐障害性の向上
  - 環境変数の不正値に対するフォールバックや警告を導入（MONITOR_POLL_INTERVAL が不正な場合にデフォルトへ戻す、PAPER_FILL_MODE の無効値検出）。
  - process_priority の実行で AccessDenied 等が発生した場合に警告を出して処理を継続するように変更。
  - init_monitoring_db の呼び出しを起動時に行うことで監視テーブルが存在しない場合のクラッシュを防止（冪等での初期化）。

- 算出ロジックの堅牢化
  - calc_score_weights: 全銘柄スコアが 0 のとき等金額配分にフォールバックして警告を出すようにした。
  - position_sizing: lot_size 単位での丸め、aggregate cap によるスケールダウン、端数配分ロジックを実装して資金配分が安定するように改善。
  - factor_research / feature_exploration: 入力データ不足時に None を返す等の安全な取り扱いを徹底。

Removed
- なし

Security
- なし

Notes / その他
- ドキュメント注記: 上記の変更点はソースコードからの推測に基づいて記載しています。実際のコミットメッセージや時系列とは異なる場合があります。必要であれば実際の Git 履歴やバージョン管理情報を元に正確な CHANGELOG を生成できます。