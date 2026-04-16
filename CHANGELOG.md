Keep a Changelog — 変更履歴
========================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

Added
- 起動スクリプトを追加/整理
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag により行う。監視は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使い MockBrokerClient を利用可能。停止フラグ / PID 管理とスレッド実行・シャットダウン監視を備える。
- 設定管理強化（kabusys.config）
  - .env / .env.local を自動ロード（プロジェクトルート検出: .git または pyproject.toml）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export 形式・クォート・インラインコメント等を考慮）。
  - Settings クラスに各種設定プロパティを実装（DB パス、Paper Trading 用パス/振る舞い、監視閾値、ログレベル、env 判定等）。不正値時は明示的な例外を投げる。
- 分散モジュール（トレード/ポートフォリオ/監視/研究/AI）
  - portfolio: 銘柄選定（select_candidates）、等配分/スコア配分（calc_equal_weights / calc_score_weights）、ポジションサイズ算出（calc_position_sizes）、セクター制限およびレジーム乗数（apply_sector_cap / calc_regime_multiplier）を実装。単元株（lot_size）やコストバッファ、aggregate cap のスケーリングロジックを含む。
  - research: ファクター計算（calc_momentum, calc_volatility, calc_value）、将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）を実装。DuckDB 接続を受けて prices_daily / raw_financials 等のテーブルを参照する設計。
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_scores）を算出・格納する処理を設計。時間ウィンドウ、トークン肥大化対策、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）などを考慮。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の集計・判定ロジックと CLI（--from/--to/--db）を提供。閾値と判定基準を定義。
- utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装（Windows / POSIX 対応）。CPU アフィニティ設定関数も提供。権限不足等のケースはログ警告でスキップ。
- DB 初期化ヘルパ: 監視用 DB テーブルが存在することを保証する init_monitoring_db 呼び出しを起動時に行う（冪等）。
- パッケージ化: パッケージルートの __version__ を 0.1.0 として設定。各モジュールの __all__ エクスポートを整理。

Changed
- 監視/実行起動時にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority を利用）。

Fixed
- （設計上のフェイルセーフ）DB や API 呼び出しでの OperationalError / API エラーを起動ループやレポート生成で適切に捕捉して処理継続するように改善（monitoring の check_once() 例外捕捉、paper_verification_report の各クエリ例外ハンドリングなど）。

Notes / Usage
- 環境変数の主なデフォルト
  - SQLITE_PATH: data/monitoring.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - MONITOR_POLL_INTERVAL: 60 (秒)
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 経由で取得可能
- Paper Trading: KABUSYS_ENV=paper_trading 時は実取引 API ではなく MockBroker を使い DB を分離する想定（data/paper_trading.db）。
- .env パースは export 形式、クォート、エスケープ、インラインコメントを扱えるため、柔軟な環境設定が可能。
- AI ニューススコアリングは OpenAI API キー（OPENAI_API_KEY）が必須。バッチ処理・部分書き換えを採用し、部分失敗時の既存データ保護を意図。

[0.1.0] - 2026-04-16
--------------------
Added
- 初回リリース相当。上記「Unreleased: Added」に記載した主要機能を実装・公開:
  - 起動スクリプト: run_execution, run_monitoring
  - 設定管理: .env 自動読み込み & Settings クラス
  - ポートフォリオ構築: 候補選定、重み算出、ポジションサイズ計算、リスク調整
  - リサーチ: ファクター計算（Momentum / Volatility / Value）、特徴量探索ツール（forward returns, IC, summary）
  - AI ニューススコアリング設計（OpenAI バッチスコアリング）
  - ユーティリティ: process priority / cpu affinity 設定
  - ツール: Paper Trading 検証レポート生成スクリプト
  - DB 周り: DuckDB + SQLite を想定したクエリ実装と初期化ヘルパ

Changed
- 初版のため該当なし

Fixed
- 初版のため該当なし

Deprecated
- なし

Security
- OpenAI API キーや各種秘密値は環境変数から参照する設計。.env の自動ロードはテスト用途等で明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Acknowledgements / TODO
- 各モジュール内に将来改善を示す TODO コメントあり（例: price フォールバック、銘柄別 lot_size マスタ、AI レスポンスのより厳格なバリデーションなど）。
- 実運用前に以下を確認推奨:
  - 実ブローカ接続時のリスク設定と rate limit の最適化
  - 権限のない環境でのプロセス優先度設定失敗に対する運用手順
  - DuckDB / SQLite のファイルローテーション・バックアップ方針

以上。必要であれば各リリースノートをより詳細に分割（監視・実行・研究・AI・ポートフォリオ）して出力できます。どのレベルの粒度がよいか指定してください。