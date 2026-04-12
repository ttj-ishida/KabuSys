# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

## [0.1.0] - 2026-04-12

### 追加
- 初回リリース。KabuSys のコアコンポーネントを導入。
- 実行／監視用エントリポイント:
  - run_execution.py — 実行エンジン起動スクリプトを追加。Engine, OrderManager, RiskManager, Reconciler 等を組み合わせてセッションを実行する。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB とは完全に分離される。
    - BrokerClientFactory により実環境／モックのブローカークライアントを選択可能。
    - 起動時にプロセス優先度を "high" に設定する（set_process_priority を呼び出し）。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。
    - モニタリングのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトへフォールバック。
    - 監視用途は環境にかかわらず本番 sqlite_path を使用する設計（モニタリング DB の分離に関する注記あり）。
- 設定と環境変数管理（config.py）を追加:
  - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。OS 環境変数を上書きしない挙動をデフォルトとし、.env.local を使って上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - 多数の Settings プロパティを実装（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグ / CPU/MEM/DISK 閾値 / 環境判定等）。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH 等の環境変数をサポート。入力値検証を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加:
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、cost_buffer による保守的見積り。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
- リサーチ／ファクター計算（kabusys.research）を追加:
  - factor_research: momentum、volatility、value のファクター計算関数を実装。DuckDB の prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターンの計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、rank ユーティリティ。
  - DuckDB を用いた SQL ベースの高速集計を採用。
- AI ニュース NLP（kabusys.ai.news_nlp）を追加:
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装。
  - バッチ処理、トークン肥大化対策（最大記事数・最大文字数トリミング）、最大 20 銘柄/コールのチャンク、JSON Mode 期待などを備える。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
  - API キー未設定時は明示的にエラーを返す。
- ユーティリティ（kabusys.utils）を追加:
  - process_priority: Windows / POSIX の差異を吸収してプロセス優先度を設定する set_process_priority、CPU affinity を設定する set_cpu_affinity を実装。権限不足や未対応環境は警告を出して安全にスキップする。
- 監視／検証ツール（kabusys.tools）を追加:
  - paper_verification_report.py: Paper Trading の検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する。
    - SQL の存在有無に対して例外ハンドリング（OperationalError 捕捉）を行い、データ欠如時は N/A を表示。
    - 日付フィルタ（--from / --to）をサポート。PAPER_TRADING_SQLITE_PATH または --db で DB を指定可能。
- パッケージ基礎情報:
  - kabusys.__version__ = "0.1.0"

### 変更（設計上の決定／注記）
- モニタリング用 DB 初期化（init_monitoring_db）は起動時に冪等に実行される仕様とし、監視テーブルの存在を保証する。
- run_monitoring は MONITOR_POLL_INTERVAL の値検証（1 未満は無効）を行い、不正値はデフォルト（60 秒）にフォールバックして警告する。
- paper_trading 環境は発注系処理と DB を明確に分離（安全設計）。
- ニュース NLP モジュールは実行中に datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。
- .env のパースロジックはシングルクォート・ダブルクォート・エスケープ、インラインコメントの取り扱いを詳細に実装。export プレフィックスにも対応。

### 修正（バグ修正 / 安全性）
- OpenAI 呼び出し周りで、API キー未設定時は早期に ValueError を送出することで不意の API 呼び出しを回避。
- process_priority / set_cpu_affinity は権限エラー（AccessDenied）や未実装例外を捕捉し、ログ警告のうえ処理をスキップして起動継続するよう堅牢化。
- DuckDB executemany の制約を考慮し、空パラメータを渡さないチェックを設計に明示。

### 既知の注意点 / マイグレーション
- run_monitoring は「本番 sqlite_path を使用する」とコメントにあるため、監視プロセス起動時に本番 DB を参照してしまう可能性があります。監視を分離したい場合は設定（SQLITE_PATH）やプロセス起動方法を見直してください。
- PAPER_FILL_MODE の無効な値は ValueError を発生させるため、環境変数の設定ミスがあると起動時に停止します。許容値は "instant", "partial", "never", "reject" です。
- KABUSYS_ENV の許容値は "development", "paper_trading", "live" のみ。その他は起動時に例外になります。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされます。CI やパッケージ化された環境で明示的に .env を読みたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動ロードを行ってください。

### セキュリティ
- 環境変数に依存する設定（API キー等）は明確に要求・検証するように実装していますが、運用時には環境変数の取り扱いに注意してください（例: OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）。

---

今後のリリースでは以下を検討:
- 単体テスト・統合テストの追加（特に OpenAI / BrokerClient をモックしたテスト）。
- 銘柄ごとの lot_size を銘柄マスタで管理する拡張。
- 価格欠損時のフォールバック（前日終値など）実装によるエクスポージャー計算の堅牢化。
- run_monitoring の監視ターゲット DB 分離オプションの導入。