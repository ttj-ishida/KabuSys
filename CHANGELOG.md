CHANGELOG
=========
すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリース: KabuSys の主要コンポーネントを追加。
- 実行エントリ:
  - run_execution.py: ExecutionEngine をデーモン的に実行する起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）で本番DBと分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理:
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml を基準）、.env/.env.local の自動読み込み（OS 環境変数の保護、ロード無効化フラグあり）と堅牢なパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - Settings クラス: 多数の環境設定プロパティを実装（DB パス・API トークン・PID / kill フラグパス・監視しきい値・PAPER_FILL_MODE のバリデーション等）。
- ユーティリティ:
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows と POSIX(Linux/Mac/FreeBSD) の差分を吸収し、アクセス拒否や未対応環境では安全にスキップする。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順・タイブレーク）と等金額・スコア加重の重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の対象外にする仕様。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method（"risk_based","equal","score"）対応、単元株（lot_size）丸め、コストバッファの考慮、aggregate cap によるスケールダウンと余剰配分アルゴリズムを搭載。
- リサーチ / ファクター:
  - research/factor_research.py: DuckDB を用いたモメンタム / ボラティリティ / バリューのファクター計算を実装（prices_daily / raw_financials テーブル参照）。MA200, ATR20, turnover 等を SQL で効率的に計算。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー、ランク関数を実装。外部ライブラリに依存せず純 Python 実装。
- AI ニュース NLP:
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント解析し ai_scores テーブルへ書き込む処理を実装。銘柄別集約、トークン肥大化対策（記事数・文字数上限）、API の再試行（指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）などを備える。ニュース収集ウィンドウの計算ユーティリティ（calc_news_window）を提供。
- ツール:
  - tools/paper_verification_report.py: ペーパートレーディング検証用のレポート生成ツールを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を行う。コマンドライン引数で期間・DB パスを指定可能。

Changed
- DB 初期化の安全性:
  - run_execution/run_monitoring 内で init_monitoring_db を呼び、監視テーブルが存在することを保証（冪等処理）。
- run_execution の動作:
  - エンジンは別スレッドで実行し、data/stop_requested.flag により安全に停止できる。停止時は ExecutionEngine.stop() を呼んでクリーンに終了を試みる。
  - 起動時に停止フラグが既に立っている場合は起動を行わずログ出力のうえ終了する。
- 環境変数・設定バリデーション:
  - Settings.env, log_level, PAPER_FILL_MODE 等で不正値に対する明示的なエラーを発生させるよう改善。
- ロギング/エラーハンドリング:
  - run_monitoring のポーリングループ内で check_once() が例外を投げてもログ出力して次ポーリングへフォールスルーするようにし、監視プロセスがクラッシュしないよう強化。
  - monitor のポーリング間隔取得（MONITOR_POLL_INTERVAL）で無効な値時に警告ログを出しデフォルトにフォールバックする処理を追加。

Fixed
- 並列性・リソース管理:
  - run_execution/run_monitoring の終了処理での DB 接続のクローズを finally ブロックで確実に行うようにしてリソースリークを防止。
- .env 読み込みの堅牢化:
  - _parse_env_line におけるクォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント処理を改善し、想定外の .env 記述でも正しくパースされるよう修正。
- ポートフォリオ / サイズ計算:
  - position_sizing の単元丸め・上限チェック・aggregate スケーリングで端数処理や上限超過を考慮するロジックを実装し、不適切なサイズ決定を低減。
- process_priority の安全性:
  - アクセス権限不足や未対応プラットフォームでの例外をキャッチして警告を出し処理を継続するよう修正（システム依存でのクラッシュ回避）。

Security
- 特記事項なし。

Notes / Known issues
- ai/news_nlp.py は OpenAI API 呼び出しを行うため、実行環境に OPENAI_API_KEY が必要。キー未設定時は明示的にエラーを送出する実装。
- news_nlp の一部処理（ファイル中断時のトランケーションや詳細な部分）は実装途中の可能性があるため、実運用前にエンドツーエンドテストを推奨。
- 一部 TODO（例: position_sizing の銘柄別 lot_size サポート、price のフォールバック戦略等）がソース内に残っているため将来的な改善余地あり。

Contributing
- バグ報告・機能追加提案は issue を作成してください。コード規約・テスト追加に関する指針はリポジトリの CONTRIBUTING.md（存在する場合）に従ってください。