# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。
このファイルはコードベースから推測して作成した変更履歴です（自動生成・推測に基づくものであり、実際のコミット履歴とは異なる可能性があります）。

## [Unreleased]

### Added
- プロジェクト初期リリースに相当する機能群を追加。
  - 全体
    - パッケージメタ情報: kabusys.__version__ = 0.1.0 を設定。
  - 実行系
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を使って環境に応じたブローカークライアントを生成（Mock/実ブローカー切替対応を想定）。
      - OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立てと ExecutionEngine の起動ロジックを実装。
      - 停止フラグ（data/stop_requested.flag）を監視し安全に停止する仕組みを実装。
      - プロセス優先度を高（"high"）に設定して起動する。
  - 監視系
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト60秒、負値や0はデフォルトへフォールバック）。
      - 監視は環境にかかわらず本番の sqlite_path（data/monitoring.db）を使用する挙動を明示。
      - 停止フラグ（data/stop_requested.flag）でループ終了。
      - プロセス優先度を高に設定して起動する。
  - 設定 / 環境管理
    - config.py: 環境変数・設定管理を実装。
      - .env/.env.local の自動ロード機構（OS 環境変数 > .env.local > .env の優先度）。
      - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env パーサの実装（コメント、export 形式、クォート、エスケープ対応）。
      - Settings クラスによるプロパティベースの設定取得（各種パス、閾値、PAPER_FILL_MODE の検証、env の妥当性検査など）。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
      - Windows / POSIX（Linux, macOS, FreeBSD）に差分吸収して優先度設定 (high/normal/low) を提供。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
      - 権限不足・未対応環境では警告を出してスキップする安全策を実装。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのソート（スコア降順、同点は signal_rank 昇順）と上位 N 選出。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が0の時は等金額にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有を評価して新規候補を除外）。"unknown" セクターは上限適用除外。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull:1.0 / neutral:0.7 / bear:0.3、未知レジームは1.0でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積もり。
      - スケーリングで残余キャッシュを使って端数を lot_size 単位で配分する再配分ロジックを実装。
      - 将来的な拡張（銘柄別 lot_size）をコメントで明示。
  - 研究・因子計算
    - research/factor_research.py
      - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを参照し、モメンタム／ボラティリティ／バリュー系ファクターを計算（ウィンドウ処理、欠損時は None）。
      - 計算スキャン範囲やウィンドウサイズの定数を定義し、欠損データ耐性あり。
    - research/feature_exploration.py
      - calc_forward_returns: 指定ホライズンの将来リターンを一括 SQL で取得。horizons の検証を実施。
      - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク付け（同順位は平均ランク）、基本統計量サマリを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - research/__init__.py に主要関数をエクスポート。
  - ツール / レポート
    - tools/paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI を追加。
      - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。
      - 指標: 稼働率 (uptime)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を計算し、PASS/FAIL を出力（閾値はソース内定義）。コマンドライン引数 --from/--to/--db に対応。
  - AI / NLP
    - ai/news_nlp.py
      - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントをスコア化し ai_scores テーブルへ書き込む処理の下地を実装。
      - ニュース収集ウィンドウ計算（calc_news_window）やバッチ処理方針、スコアのクリップ、リトライ（429/ネットワーク/5xx）方針、出力 JSON バリデーション等を設計。
      - API キー未設定時の ValueError を明示。

### Changed
- （当初リリース相当のため該当なし）

### Fixed
- （当初リリース相当のため該当なし）

### Deprecated
- （当初リリース相当のため該当なし）

### Removed
- （当初リリース相当のため該当なし）

### Security
- OpenAI API キー等の機密情報は Settings / 環境変数経由で取得する設計になっており、.env 自動ロードは OS 環境変数を上書きしない保護付き（protected keys）で実装。

---

## 補足（実装上の注意 / 既知の制約・TODO）
- config._find_project_root() は .git または pyproject.toml を探索してプロジェクトルートを特定するため、配布パッケージ化後や特殊な配置では自動 .env ロードがスキップされる場合がある。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。
- run_monitoring は Monitoring 用に常に本番 sqlite_path を使用する（意図的な分離）。必要に応じて設定で切り替えることを検討してください。
- position_sizing.calc_position_sizes の price が欠損（0.0）の場合、エクスポージャーや上限計算で誤差が生じる可能性があり、将来的には前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- ai/news_nlp.py はファイル末尾が未完（スニペットが途中で終わっている）ため、記事取得・API 呼び出し・DB 更新の完全実装は要確認・補完が必要。
- DuckDB / SQLite 周りのテーブル名（prices_daily, raw_financials, trade_logs, system_status 等）はコードに依存するため、DB スキーマの整合性に注意すること。
- process_priority の優先度設定は権限（特に POSIX の負の nice 値）やプラットフォームに依存するため、権限不足時は警告を出して設定をスキップする設計。

---

## 0.1.0 - 2026-04-17
- 初回公開相当のリリースとして上記機能群をまとめてリリース。
- 参考: パッケージメタ情報に __version__ = "0.1.0" を設定。

（注）日付はコードの解析日時に基づく推測です。実際のリリース日やコミット履歴が必要な場合は git の履歴等を参照してください。