Changelog
=========

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベースの状態から推測して作成した初期リリースの変更履歴です。

Unreleased
----------

- （現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 初期リリース。パッケージメタ情報:
  - kabusys バージョン 0.1.0
- 実行/監視スクリプト:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() 実行。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視用 DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用（設計上の意図）。
    - 起動時にプロセス優先度を設定。
- 設定管理:
  - config.py
    - .env/.env.local の自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env のパースは export 付き、引用符／エスケープ対応、インラインコメント処理などをサポート。
    - 環境変数の保護（OS 環境変数を上書き禁止）や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスで多数の設定値を提供（DB パス、PID ファイル、監視しきい値、ログレベル、環境種別判定、paper_trading 用オプション等）。
    - 値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）は明示的に ValueError を発生させる。
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder
    - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数を返却（未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各種配分方式（risk_based / equal / score）に対応した発注量計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り。
- 研究（research）モジュール:
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算（MA200、ATR20、リターン等）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターンの一括取得（任意ホライズン）。
    - calc_ic: スピアマン順位相関（IC）計算（ランク処理を含む）。
    - factor_summary / rank: 基本統計量と順位変換ユーティリティ。
  - research.__init__.py で主要関数をエクスポート。
- AI ニューススコアリング:
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別にセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込み。
    - バッチサイズ、トークン肥大化対策（記事数・文字数の上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング、部分失敗時の既存スコア保護（対象コードのみ削除→挿入）などの堅牢化処理を実装。
    - API キー未設定時は ValueError を発生。
- ユーティリティ:
  - utils.process_priority
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定（権限不足時は警告でスキップ）。
    - set_cpu_affinity: 最初の N コアへピンニング（未対応環境では警告でスキップ）。
- ツール:
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプト（コマンドライン実行可）。
    - 稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数などを集計し PASS/FAIL 判定を行う。閾値はソース内定義（稼働率 99% 等）。
    - 日付フィルタ、DB パス引数のサポート、DB 存在チェック、DuckDB ではなく SQLite 参照。
- DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。
- DB 接続:
  - DuckDB と SQLite を併用する設計（分析は DuckDB、監視/オーダー等は SQLite）。

Changed
- （初版のため過去の変更はなし。ただし設計上の注意点として以下を明記）
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。監視 DB を環境により切り替えたい場合は設定の見直しが必要。
  - .env 読み込み順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）。

Fixed
- 該当なし（初期リリースとして既知の修正はなし）。

Security
- OpenAI API キー等の機密情報は環境変数で管理することを想定。config.py は .env 自動ロード時に既存 OS 環境変数を保護する実装を行っている。

Notes / Known issues / TODO
- news_nlp.score_news は OpenAI API へ依存（api_key が必須）。API 使用量に注意が必要。
- portfolio.position_sizing:
  - price が欠損（0.0）の場合、エクスポージャーが過少評価される可能性がある旨コメントあり（将来的にフォールバック価格実装予定）。
  - lot_size は現状グローバル共通。将来的に銘柄毎の lot_map に対応する TODO コメントあり。
- research モジュールは DuckDB に格納された prices_daily / raw_financials の品質に依存。データ不足時は None を返す設計。
- run_monitoring/run_execution は起動時にプロセス優先度を設定するが、権限がない場合は警告で続行する設計。
- tests や CI の有無はコードからは不明。自動テストの追加を推奨。

依存関係（コードから推定）
- duckdb
- psutil
- openai（OpenAI Python SDK）
- 標準ライブラリ（sqlite3, logging, argparse, datetime, os, math 等）

署名
- 本 CHANGELOG は提供されたソースコードの内容を元に推測して作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴やリリース管理情報に基づいて作成してください。