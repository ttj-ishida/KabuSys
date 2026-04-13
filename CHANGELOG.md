# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。  
初期リリースの内容は、ソースコードから推測して作成しています。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ情報を追加
  - パッケージ version を __version__ = "0.1.0" として定義。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離して動作。  
    - 起動時にプロセス優先度を High に設定する処理を追加（utils.process_priority.set_process_priority を利用）。  
    - ブローカークライアント生成（BrokerClientFactory）および OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine.run_session() を実行。  
    - duckdb 接続（duckdb_path）を ExecutionEngine に渡す。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告出力。  
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明記。  
    - 起動時にプロセス優先度を High に設定。sqlite3 / duckdb への接続と SystemMonitor の check_once を定期実行。

- 設定・環境変数管理
  - config.Settings クラスを導入し、環境変数（およびプロジェクトルートの .env / .env.local）から設定を取得する機能を追加。  
    - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行う。CWD に依存しない実装。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。  
    - .env パーサは export 形式、クォート、インラインコメント、エスケープ等に対応。既存 OS 環境変数の上書きを防ぐ protected 対応あり。  
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグパス、閾値、環境種別判定など）。  
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の入力バリデーションを実装（不正値は ValueError を送出）。

- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db を用いた監視テーブル初期化（冪等）を実装。run_execution/run_monitoring 起動時に保証。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）・等配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。  
    - スコア全0の際は等配分にフォールバックし警告ログを出す。
  - portfolio.risk_adjustment: セクター集中の上限適用（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。  
    - セクター不明 ("unknown") は上限適用対象外にする等の挙動を定義。未知のレジームは警告して 1.0 でフォールバック。
  - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）を実装。  
    - lot_size（単元株）考慮、max_position_pct・max_utilization・cost_buffer を用いた aggregate cap（スケールダウン）処理、残差に基づく追加配分ロジックなどを実装。

- 研究（research）モジュール
  - research.factor_research: DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）を実装。  
    - mom_1m/3m/6m、ma200_dev、atr_20/atr_pct/avg_turnover/volume_ratio、per/roe などを計算。データ不足時は None を返す仕様。  
    - SQL ウィンドウ関数を多用し効率的に実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ランク相関による IC 計算（calc_ic）、ファクター統計要約（factor_summary）、ランク付けユーティリティ（rank）を実装。  
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。horizons のバリデーションあり。

- AI ニュース NLP（OpenAI 連携）
  - ai.news_nlp: raw_news から銘柄ごとに記事を集約し OpenAI API（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。  
    - 時間ウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）とルックアヘッドバイアス回避設計。  
    - バッチ（最大 20 銘柄）送信、最大トークン肥大回避のため記事数/文字数上限を設定（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。  
    - 429 / ネットワーク / 5xx 等に対する指数バックオフリトライ（最大リトライ回数設定）。  
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に他銘柄の既存スコアを保護するための DB 操作（コード絞り込み DELETE → INSERT）設計。  
    - OPENAI_API_KEY 必須（引数または環境変数）。

- ユーティリティ
  - utils.process_priority: Windows / POSIX (Linux, Darwin, FreeBSD) を吸収したプロセス優先度設定と CPU affinity 設定を実装。  
    - set_process_priority(level): "high"/"normal"/"low" をサポート。アクセス拒否や未サポート環境では警告ログでスキップ。  
    - set_cpu_affinity(cpu_count): 指定数にプロセスをピン留め。invalid 値（<1）では ValueError。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。  
    - レポートは稼働率・注文成功率・送信率・P95 レイテンシなどを出力。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）で PASS/FAIL 判定。  
    - --from/--to/--db オプションを提供。DB 存在チェックと sqlite3.OperationalError への耐性あり。

### Changed
- DB ハンドリング方針の明確化
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を参照する仕様を明示（run_monitoring.py）。一方、実行エンジンは paper_trading 環境時に専用 DB を利用するよう切り分け。

- 設定読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む仕様を採用。既存 OS 環境変数はプロテクトされ上書きされない。

### Fixed
- 環境変数パーサの堅牢化
  - .env のクォート処理、エスケープ、コメント判定を改善し、export 形式やインラインコメントの取り扱いを安定化。

- ポートフォリオ配分におけるスコア全0ケース
  - calc_score_weights で全スコアが 0.0 の場合に等金額配分へフォールバックするようにし、無効な分配を防止。

- position_sizing の aggregate cap 実装
  - 合計投資額が利用可能現金を超えた場合のスケールダウンロジックと、lot_size 単位での残余配分ロジックを実装し、端数処理の再現性を確保。

### Security
- OpenAI API キーの取り扱い
  - ai.news_nlp は明示的に api_key 引数または OPENAI_API_KEY 環境変数を要求し、未設定時は ValueError を投げることでキー漏洩リスクの曖昧さを低減。

### Notes / Known behavior
- MONITOR_POLL_INTERVAL の値が 0 以下や非整数の場合はデフォルト 60 秒にフォールバックし警告を出力します（sleep に 0 や負値を渡さないための設計）。  
- Settings の一部プロパティは不正値時に ValueError を送出します（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。起動スクリプトはこれを前提にしているため、環境変数の設定ミスで即時終了する可能性があります。  
- ai.news_nlp は API 呼び出しの失敗に頑健に設計されているが、部分的な失敗時の DB 挙動（削除/挿入の粒度）やレスポンス検証ルールに依存するため、運用時の監視を推奨します。

--- 

この CHANGELOG はソースコードの実装（関数名、コメント、定数、挙動）から推測して作成しています。実際のリリースノートとして利用する場合は、追加のリリース日・変更履歴の補足・影響範囲（BREAKING CHANGES 等）を開発チームで検証してください。