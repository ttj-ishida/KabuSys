CHANGELOG
=========

すべての重要な変更は本ファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。  

注: この CHANGELOG は与えられたコードベースの内容から機能・設計・既知の制約を推測して作成したものです。

Unreleased
----------

- なし

0.1.0 - 2026-04-12
------------------

Added
- 基本機能の初期実装（パッケージの初回リリース想定）。
  - パッケージメタ情報を追加
    - kabusys.__version__ = "0.1.0"
  - 実行エントリスクリプト
    - run_execution.py: ExecutionEngine の起動スクリプトを実装。  
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用する分離動作。
      - プロセス優先度を起動時に "high" に設定。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を呼ぶ。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効扱いでフォールバック）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（monitoring テーブルを初期化）。
      - プロセス優先度を起動時に "high" に設定。
  - ツール
    - tools.paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。  
      - DB（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出して標準出力でレポート化。  
      - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を実施。
  - 設定管理
    - config.Settings: 環境変数読み取りと検証ロジックを実装。  
      - .env / .env.local の自動ロード機能（プロジェクトルートの .git または pyproject.toml を基準に検出）。  
      - 読み込み優先度: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
      - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID ファイルパス / 環境判定フラグ等）。  
      - 値検証: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等は有効値チェックを行う（不正な場合は ValueError を送出）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、単元（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
    - portfolio.__init__ で主要 API をエクスポート。
  - 研究・リサーチ機能
    - research.factor_research: momentum / volatility / value ファクター計算を DuckDB を用いて実装。prices_daily / raw_financials を参照。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン ρ）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）。
    - research.__init__ で zscore_normalize を含む主要 API をエクスポート。
  - ニュース NLP（AI）モジュール
    - ai.news_nlp: raw_news を集計して OpenAI（gpt-4o-mini）でセンチメントスコアを生成し、ai_scores テーブルへ書き込む処理を実装。  
      - タイムウィンドウ（前日15:00 JST〜当日08:30 JST 相当）を正確に計算して記事を抽出。  
      - 1 銘柄あたりの記事・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。  
      - 最大 20 銘柄バッチで API コール、JSON Mode で厳密な JSON 出力を期待。  
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。  
      - レスポンス検証、スコアを ±1.0 でクリップ、部分成功に備えた安全な DB 更新（該当コードのみ置換）。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティを提供。psutil に基づく実装でアクセス許可エラー時は警告でスキップ。

Changed
- 初期リリースのため変更履歴は該当なし。

Fixed
- 初期リリースのため修正履歴は該当なし。

Deprecated
- なし

Removed
- なし

Security
- 外部 API キー（OpenAI 等）は Settings 経由または引数で明示的に与える設計。README 等でシークレットの管理を指示することを推奨。

Notes / Known limitations / TODOs
- .env パーサは多くのケースをサポート（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等）。ただし極端に複雑な .env 構成で未対応の可能性あり。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price=0.0（欠損）があるとエクスポージャーが過少見積りされブロックが外れる可能性がある。将来的には前日終値等のフォールバック実装を検討中（TODO コメントあり）。
- position_sizing:
  - 現状 lot_size は全銘柄共通パラメータ。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO コメントあり）。
- utils.process_priority / set_cpu_affinity:
  - psutil の権限不足 (AccessDenied) や未対応プラットフォームでは警告を出してスキップするため、コンテナや制限環境で期待どおりに動作しない場合がある。
- ai.news_nlp:
  - API 呼び出しの失敗や部分失敗時はフェイルセーフで継続する設計。ただし API レスポンスの形式依存（厳密な JSON）やトークン制限には注意が必要。
  - DuckDB の executemany に関する制約を回避するため、パラメータリストが空でないことを事前チェックする実装方針が採られている。
- tools.paper_verification_report:
  - DB に該当テーブルが存在しない場合は N/A を返す堅牢化を実装（sqlite3.OperationalError をハンドリング）。
  - P95 の計算は単純なパーセンタイル実装（データが空の場合は N/A）。
- Settings:
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等は不正値で例外を投げるため、環境設定ミスは起動時に早期に検出される。

開発者向け補足
- パッケージは DuckDB および sqlite3 をデータレイヤに使用します。ローカル環境では data/ 以下に DB ファイルを置くことを想定しています。
- 実行時の主要環境変数:
  - KABUSYS_ENV (development|paper_trading|live)
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
  - MONITOR_POLL_INTERVAL
  - OPENAI_API_KEY
  - PAPER_FILL_MODE
  - その他（KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN, LINE_CHANNEL_ACCESS_TOKEN など）
- CLI モジュールは python -m kabusys.tools.paper_verification_report 等から利用可能。

今後の予定（提案）
- price fallback の導入（前日終値や取得原価による補完）。
- 銘柄別 lot_size サポート。
- ai.news_nlp の結果をより堅牢にするためのローカル検証ツール（模擬 API レスポンス）やテストスイートの追加。
- 実運用向けにはログレベル/ログ出力先の細かな設定、メトリクス収集（Prometheus など）を導入。

--- 

（以上）