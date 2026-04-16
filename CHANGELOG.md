CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

### Added
- MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔上書き（無効値時はデフォルト60秒にフォールバックし、警告ログを出力）。
- run_monitoring/run_execution 起動スクリプト:
  - プロセス優先度を高優先（"high"）に設定する処理を起動時に実行。
  - プロセス停止のためのファイルフラグ（data/stop_requested.flag）による安全なシャットダウン制御を追加。
  - run_execution は paper_trading 環境で MockBroker を使用し、paper_trading 用 DB を分離して利用する挙動をサポート。
- Settings 設定管理:
  - .env/.env.local の自動ロード機能をプロジェクトルート（.git または pyproject.toml）から行う仕組みを実装。
  - 環境変数の必須チェック（_require）と各種設定値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を追加。
  - Paper Trading 用 DB パス、PID/kill フラグパス、各種しきい値（CPU/MEM/DISK）などのプロパティを提供。
- Portfolio モジュール:
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - ポジションサイズ計算（calc_position_sizes）: risk_based / equal / score の割当方式、単元株丸め、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を考慮した安全な配分ロジックを実装。
  - セクター集中制限（apply_sector_cap）と市場レジームに基づく投資乗数（calc_regime_multiplier）。
- Research モジュール:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）：DuckDB の prices_daily / raw_financials テーブルを使用してモメンタム・ボラティリティ・バリュー指標を算出。
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）：将来リターン計算、スピアマンランク相関（IC）、基本統計量出力を標準ライブラリのみで提供。
  - DuckDB 接続を受けることで外部 API に依存せずに分析可能。
- AI ニュース NLP（ai/news_nlp）:
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントスコアを ai_scores に書き込む処理を実装（バッチサイズ、トークン肥大化対策、スコアクリップ、部分書き換えによる部分失敗耐性を考慮）。
  - ニュースウィンドウ計算（JST → UTC 変換）ユーティリティを提供。
  - API 再試行（429/接続断/タイムアウト/5xx）を指数バックオフで行う方針を導入。
- tools:
  - paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し、PASS/FAIL 判定を出力。日付フィルタと DB パスのオーバーライドに対応。
- ユーティリティ:
  - process_priority: Windows/Linux/Mac の差分を吸収してプロセス優先度を設定するユーティリティと、CPU affinity 設定関数を追加（権限不足や非対応プラットフォームでは警告ログを出してスキップ）。

### Changed
- Settings の .env 自動ロードは OS 環境変数を保護するため .env/.env.local 読み込み時に OS 環境変数を上書きしない（.env.local は override=True だが protected により OS 環境変数は保護）。
- run_monitoring は KABUSYS_ENV に依存せず監視用の本番 sqlite_path を使用するように明記（監視の一貫性確保）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全に分離。

### Fixed
- .env パーサーの強化:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理を正しく扱うよう改善。
  - 無効行・空行・コメント行の判定を堅牢化。
- 各種入力検証の強化（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL, calc_forward_returns の horizons 引数など）により、不正な環境変数や API 呼び出し引数で早期にエラーを検出。

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY のみを受け付け、未設定時は明示的にエラーを返すようにして誤設定による情報漏洩リスクを低減。

0.1.0 - 2026-04-16
------------------

初期リリース — ベースライン機能を実装。

### Added
- プロジェクト初期パッケージ構成を追加:
  - kabusys パッケージ本体（__init__ にバージョン 0.1.0 を設定）。
  - サブパッケージ: portfolio, research, ai, tools, monitoring, execution, utils, config 等。
- 実運用向け起動スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループ起動、停止フラグ検知、DB 初期化処理、DuckDB 接続サポート。
  - run_execution.py: ExecutionEngine 起動、BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行スレッド管理、停止フラグ検知、paper_trading 用 DB 分離。
- 核心ロジック:
  - portfolio: 候補選定、重み付け、ポジションサイズ算出、リスク調整（セクター上限・レジーム乗数）。
  - research: ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン計算、IC 計算、統計サマリー。
  - ai/news_nlp: ニュース集約→OpenAI でセンチメント評価→ai_scores テーブル書込のワークフロー（バッチ・トリム・バリデーション・再試行）。
  - monitoring DB 初期化ユーティリティ（init_monitoring_db を介して監視テーブルの冪等初期化）。
- 開発支援ツール:
  - tools/paper_verification_report.py による Paper Trading の運用検証レポート出力（期間指定、DB パス指定、複数指標の PASS/FAIL 判定）。

### Changed
- プロジェクトルート検出機能を導入し、.env 自動読み込みをプロジェクト構成に依存して行うようにした（CWD に依存しない動作）。
- config.Settings による集中管理を導入し、環境ごとの分岐（development/paper_trading/live）や各種パス・閾値・挙動を統一的に取得可能にした。

### Fixed
- 起動/運用上の堅牢性を向上:
  - 起動時にプロセス優先度設定や監視 DB の初期化を行い、例外発生時も接続を確実にクローズするようにした。
  - run_execution のエンジンスレッド監視で停止フラグを検出した際に安全に停止処理を行うロジックを追加。

### Documentation
- 各モジュールに詳細な docstring を追加し、設計方針や入力/出力・例外条件を明記。

---

注: 上記はコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートに基づくものではありません。