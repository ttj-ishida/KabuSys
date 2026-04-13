CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに基づいて記載しています。
- 日付はリリース日を示します。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

初期リリース — KabuSys のコア機能を実装した最初の公開バージョン。

Added
- 基本アーキテクチャと起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用する（KABUSYS_ENV=paper_trading 時は data/paper_trading.db を使用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 両スクリプトともプロセス優先度を起動時に設定する機能を組み込み（utils.process_priority.set_process_priority を利用）。

- 設定管理
  - config.Settings: 環境変数／.env ファイルからの読み取りを行う設定クラスを追加。
    - .env の自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を読み込む（OS 環境変数が優先、.env.local は上書き可）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須変数未設定時に明確なエラーを出す _require() を実装。
    - 各種設定プロパティを提供（DB パス、PID / kill フラグ、閾値、PAPER_FILL_MODE バリデーション等）。

- ポートフォリオ構築（純関数群、DB 非依存）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）・重み計算（calc_equal_weights, calc_score_weights）を追加。calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の配分方式に対応し、単元株（lot_size）丸め、最大ポジション上限、投下資金のスケーリング（aggregate cap）と残差処理をサポート。

- リサーチ / ファクター計算
  - research.factor_research: momentum / volatility / value ファクター計算関数を追加（DuckDB 接続を受け prices_daily / raw_financials を参照）。200 日移動平均・ATR 等を SQL ウィンドウ関数で計算。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）を追加。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_scores）を作成する機能を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）定義、記事トリム（記事数・文字数上限）、チャンク（最大 20 銘柄）ごとの API コール、リトライ（指数バックオフ）とレスポンスバリデーション、スコアクリッピング（±1.0）等を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。CPU アフィニティ設定関数も追加。
  - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL を判定する CLI。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Changed
- 仕様上の設計決定（ドキュメント化）
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（settings.sqlite_path）を使用するという挙動を明示（監視用は本番 DB を参照する設計）。
  - run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と完全分離する挙動を明示。

Fixed
- フォールバックと堅牢性の向上
  - MONITOR_POLL_INTERVAL に不正値が設定された場合、デフォルト（60 秒）へフォールバックして警告を出す処理を追加。
  - .env 読み込みでファイルアクセス失敗時に warnings.warn を出力して読み込みを継続するよう修正。
  - DuckDB への executemany 使用を念頭に置いた空パラメータ回避（ai モジュールの設計方針として言及）。
  - 各種クエリでデータ不足時に None の扱いを明確にし、レポート/集計が壊れないよう保護（paper_verification_report 等）。

Security
- OpenAI API キーは明示的に引数または環境変数から取得し、未設定時は例外を発生させることで誤動作を抑止。

Notes / Known issues
- ai.news_nlp: OpenAI との通信・レスポンス処理は堅牢化を図っているが、部分的な API 失敗時の動作（どの程度部分成功を許容するか）は運用方針に依存するため注意が必要。
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格の導入を検討している旨の TODO が残っている。
- calc_position_sizes: lot_size をグローバルで固定している（将来的に銘柄別 lot_size サポートを検討）。

開発者向け補足
- パッケージバージョンは kabusys.__version__ = "0.1.0"。
- DuckDB / SQLite を併用する設計のため、環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH の設定に注意してください。
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、配布後に想定外の動作となる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定の上、明示的に環境変数を供給してください。

References
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。動作の詳細や運用ルールはソースコード内の docstring / コメントを参照してください。