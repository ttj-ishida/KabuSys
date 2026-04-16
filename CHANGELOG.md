Keep a Changelog
=================

すべての重要な変更点をこのファイルで記録します。  
このプロジェクトでは "Keep a Changelog" の形式に準拠しています。

フォーマット
-----------

- 変更は分類（Added, Changed, Fixed, ...）ごとにまとめます。
- 可能な限り影響範囲（該当するモジュール / ファイル）を併記します。

Unreleased
---------

（現時点で未リリースの変更はありません。）

0.1.0 - 2026-04-16
------------------

Added
- 初期リリース: 基本機能をまとめて追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカークライアント生成、ExecutionEngine のスレッド実行・停止処理を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知で安全に終了。
  - 設定管理
    - config.py: .env 自動読み込み機能（.env, .env.local）、堅牢な .env パーサ実装、Settings クラスによる環境変数ラッパを追加（DB パス、PaperTrading 用設定、監視閾値、環境種別判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）を追加。スコア合計が 0 の場合のフォールバックを実装。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。未知のレジーム/セクターの扱いとログ出力を実装。
    - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）を実装。lot サイズ丸め、per-stock 上限・aggregate cap（利用可能現金によるスケールダウン）、コストバッファを考慮した再配分ロジックを実装。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。各種ウィンドウサイズの定義と欠損時の扱いを実装。
    - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、Spearman ランク相関による IC 計算、rank / factor_summary（基本統計量）を実装。外部依存なしで標準ライブラリのみを利用。
    - research.__init__: 主要関数と zscore_normalize をエクスポート。
  - ニュース NLP（AI連携）
    - ai.news_nlp: raw_news から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを計算して ai_scores テーブルへ書き込む処理を追加。バッチ処理、トークン肥大対策、レスポンスバリデーション、リトライ（指数バックオフ）などを実装。スコアを ±1.0 にクリップ。
  - ユーティリティ
    - utils.process_priority: プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）のクロスプラットフォーム対応ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足時は安全にスキップ。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 DB から稼働率・注文成功率・送信率・レイテンシ等を集計して検証レポートを生成する CLI ツールを追加。P95 計算、閾値による PASS/FAIL 判定、DB 存在チェック、およびテーブル未存在時の耐障害性を実装。
  - パッケージ初期化
    - __init__.py: パッケージ名・バージョンを設定（__version__ = "0.1.0"）。


Changed
- DB と監視の挙動
  - run_monitoring.py: 監視用の初期化は常に本番 sqlite_path を使用する（KABUSYS_ENV に依存しない挙動を明示）。duckdb も接続して SystemMonitor に渡す。
  - run_execution.py: paper_trading 環境時は settings.paper_sqlite_path を使用して本番 DB と明確に分離する設計に変更。
- .env 読み込みの挙動
  - config.py: 自動ロードの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数を protected として .env の上書きを制御する仕組みを導入。
  - .env のパースを強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなど）。
- ログレベル・環境値の検証
  - Settings.env / log_level / PAPER_FILL_MODE などで不正な値の検出と ValueError による早期失敗を導入（デフォルトと有効値を明示）。

Fixed
- フォールバックや耐障害性の改善
  - MONITOR_POLL_INTERVAL の値が不正（0 以下や非数）な場合にデフォルト（60 秒）へフォールバックし、警告ログを出力するように修正（run_monitoring.py）。
  - position_sizing: 価格欠損（0 または None）の銘柄をスキップすることでゼロ除算や不正な株数算出を防止。
  - portfolio.calc_score_weights: 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして警告ログを出力。
  - risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限の対象外とする扱いを明確化。
  - tools.paper_verification_report: テーブルが存在しない場合に sqlite3.OperationalError を捕捉して適切にレポートできるよう改善。P95 計算関数の空リスト戻り値を扱うよう修正。

Security
- OpenAI API キーの取り扱い
  - ai.news_nlp.score_news: api_key 引数または OPENAI_API_KEY 環境変数が未設定の場合は ValueError を送出（明示的な未設定検出）。
- 最小権限での動作を想定し、プロセス優先度 / affinity 設定で権限不足時は警告ログを出してスキップする安全設計（utils.process_priority）。

Notes / Known limitations
- position_sizing: price が欠損（0.0）だとエクスポージャーが過小見積りされ、apply_sector_cap の判定に影響を与える可能性あり（TODO コメントあり）。将来的に前日終値や取得原価をフォールバック価格として導入することを検討。
- ai.news_nlp: スコアリングは OpenAI レスポンスの整合性に依存するため、部分失敗時に既存スコアを保護する仕組み（部分更新）を導入しているが、完全なトランザクション性は DuckDB の制約に依存する点に注意。
- research モジュールは DuckDB の prices_daily / raw_financials を前提に実装されており、入力データの欠損・不整合に対するガードはあるが、データ準備が前提。

Contributing
--------------
- バグ修正・改善・新機能は PR を送ってください。設定・動作に影響する変更はドキュメント（README/.env.example 等）も併せて更新してください。

License
-------
- プロジェクトのライセンス情報はリポジトリのライセンスファイルを参照してください。