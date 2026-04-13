# Changelog

すべての非互換性のある変更は明記します。  
このファイルは Keep a Changelog の形式に準拠しています。  

なお、以下はコードベースから推測して記載した変更点の要約です（自動生成ドキュメント的な記述です）。

## [0.1.0] - 2026-04-13

### Added
- 初版リリース。KabuSys の自動売買/リサーチ/監視用モジュール群を追加。
- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。BrokerClientFactory によるブローカークライアント選択をサポート。
    - ExecutionEngine の構築時に OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、RiskConfig や EngineConfig（target_date）を注入。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する（監視データは本番 DB に記録）。

- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で判定）。優先順位は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサーを独自実装（`export` プレフィックス対応、クォート／エスケープ、インラインコメント処理、保護キー機能）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、PID/KILL フラグ、閾値、env/ログレベル検証など）。
    - PAPER_FILL_MODE の妥当性検証、KABUSYS_ENV / LOG_LEVEL の検証を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナル選択（スコア降順、同点のタイブレークは signal_rank）、等金額配分、スコア重み配分（スコア合計が 0 の場合は等分にフォールバック）を実装。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率に基づき当日新規の候補を除外するロジック。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - allocation_method（"risk_based", "equal", "score"）に基づく株数計算を実装。損切り率、許容リスク率、単元株（lot_size）丸め、1 銘柄上限、投下資金の aggregate cap とスケーリング（小数端数の優先配分ロジック含む）を実装。
    - cost_buffer により保守的に約定コストを見積もる機能を追加。

- 研究・ファクター計算（DuckDB ベース）
  - research.factor_research
    - モメンタム、ボラティリティ、バリューの計算関数を追加（prices_daily/raw_financials を参照）。長期 MA や ATR、出来高平均等を SQL ウィンドウ関数で算出。データ不足時の None ハンドリングあり。
  - research.feature_exploration
    - 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ランク付け（同順位は平均ランク）、ファクター統計サマリーを追加。外部ライブラリに依存しない純粋 Python 実装。
  - research.__init__ に主要 API をエクスポート（zscore_normalize は data.stats から）。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でバッチセンチメントスコア化し、ai_scores テーブルへ書き込む機能を追加。
    - タイムウィンドウ計算（target_date に対する前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を実装。
    - 銘柄ごとに記事を集約してトリム（最大記事数・文字数）、最大 20 銘柄/バッチで JSON Mode により API に送る設計。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコア ±1.0 のクリッピング、部分成功時の部分置換（DELETE → INSERT）による耐障害性を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) により Windows / POSIX（Linux/Mac/FreeBSD）で優先度を設定するユーティリティを追加。権限不足や非対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加（指定コア数にプロセスをピン留め）。不正値や権限不足は警告でスキップ。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を判定する。各種閾値と出力フォーマットを実装。
    - SQL クエリは期間フィルタに対応し、存在しないテーブルに対しては例外を補足して安全に N/A を出力。

- パッケージメタ情報
  - __init__.py にバージョン `__version__ = "0.1.0"` を設定。

### Changed
- 設計上の防御的実装
  - .env パーサーや DB クエリ周り、外部 API 呼び出し（OpenAI）において、エラー時にスキップもしくはフォールバックするように実装（フェイルセーフ設計）。
  - DuckDB クエリのスキャン範囲にバッファ（日数倍率）を入れて週末・祝日を吸収する設計。

### Fixed
- 環境変数パースの不具合を考慮した堅牢化
  - export キーワード、クォート内エスケープ、インラインコメント、保護キーの扱い等を考慮して .env の読み込みロジックを整備。

### Removed
- なし（初版）

### Security
- API キーの扱いは明示的に引数/環境変数から読み取る仕様にし、未設定時はエラーにより誤作動を防止。

## 参考・注意事項
- run_monitoring/run_execution は DB 接続を行うため、実行環境の環境変数（SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH 等）を適切に設定してください。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等は妥当性チェックが入るため不正な値は ValueError を発生させます。
- process priority / cpu affinity の操作は権限やプラットフォーム制約により失敗する場合があり、その場合は警告を出して処理を継続します。

---
（この CHANGELOG はコードの内容から推測して作成しています。実際の変更履歴管理やリリースノートはプロジェクトの運用ルールに合わせて必要に応じて調整してください。）