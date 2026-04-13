Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に従います。日付はリリース日（このコードベースの現時点での初回リリース想定日）を使用しています。

Unreleased
----------
（未リリースの変更はここに記載します）

0.1.0 - 2026-04-13
-----------------
追加 (Added)
- 初回公開リリース: KabuSys v0.1.0
- 実行エントリ／Engine
  - run_execution.py を追加。ExecutionEngine 起動スクリプトを提供。
  - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）へ完全分離して記録する挙動を実装。
  - 起動時にプロセス優先度を "high" に設定するフローを組み込み（utils.process_priority.set_process_priority を使用）。
  - ExecutionEngine の起動に必要な依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）の組み立てを行う。

- 監視（Monitoring）
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下の値はデフォルトにフォールバック）。
  - Monitoring は実行環境にかかわらず本番 sqlite_path を使用する設計。
  - monitoring DB 初期化（init_monitoring_db）と DuckDB 接続を行う。

- 設定読み込み／Settings
  - config モジュールを導入。.env/.env.local の自動読み込み機能（プロジェクトルート検出 .git または pyproject.toml ベース）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを強化:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内でのエスケープ処理・インラインコメント対応
    - クォートなし行での # コメント処理（直前がスペース/タブの場合）
  - Settings クラスを提供し、各種環境変数の取得とバリデーションを実装（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
  - デフォルトパス設定: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）, PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）, PID_FILE_PATH など。

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートをコマンドラインで生成するスクリプト。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、PASS/FAIL 判定を出力する。
    - CLI 引数 --from / --to / --db をサポート。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

- ポートフォリオ構築（Portfolio）
  - portfolio モジュールを追加:
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（スコアソート、同点タイブレーク、スコア全0時のフォールバック等）。
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
    - position_sizing: calc_position_sizes を実装（risk_based / equal / score 配分、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全弁、lot_size 単位での残差配分）。
  - 設計注記として DB 参照を行わない純粋関数群（メモリ内計算）を採用。

- リサーチ / ファクター計算（Research）
  - research モジュールを追加:
    - factor_research: calc_momentum（1/3/6M リターン, MA200乖離）, calc_volatility（ATR20, 相対ATR, 20日平均売買代金等）, calc_value（PER/ROE）を DuckDB を使った SQL ベースで実装。
    - feature_exploration: calc_forward_returns（将来リターン）, calc_ic（Spearman ランク相関による IC）, factor_summary（基本統計量）, rank（同順位は平均ランク）を実装。
  - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計。

- AI / ニュース NLP
  - ai/news_nlp.py を追加。raw_news を OpenAI API に送信してニュースセンチメント（-1.0〜1.0）を計算し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウの算出（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を実装。
    - 記事集約、1銘柄あたり最大記事数／文字数トリム、最大バッチ 20 銘柄での API 呼び出し、JSON Mode による厳格なレスポンス検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx の指数バックオフリトライを実装。
    - OPENAI_API_KEY または引数 api_key を必須とする（未設定時は ValueError）。

- ユーティリティ
  - utils/process_priority.py を追加。set_process_priority（Windows と POSIX の差分吸収）、set_cpu_affinity（最初の N コアに固定）を実装。権限不足や未対応 OS では警告を出してスキップする安全設計。

- パッケージ情報
  - package metadata: __version__ = "0.1.0" を追加。
  - 各サブモジュールの __all__ 等エクスポートを整備。

変更 (Changed)
- 初回リリースのため、過去の変更からの差分はなし。

修正 (Fixed)
- 初回リリースのため、過去の不具合修正は無し（コード内で堅牢性強化の実装箇所あり：.env 読み込みの失敗時に warnings.warn、DB 存在チェック、NULL 安全な SQL 計算など）。

既知の設計上の注意点 / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーやコスト計算が過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- ai/news_nlp:
  - API 呼び出し失敗時はフェイルセーフで部分的にスコア書き換えを回避する設計だが、外部 API 利用に起因する部分障害の影響範囲は運用上注意が必要。
- .env の自動ロードはプロジェクトルートを検出できない場合はスキップされる。CI/デプロイ環境では環境変数での明示設定を推奨。

依存関係（主な外部パッケージ）
- duckdb
- psutil
- openai

環境変数（主なもの）
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
- PAPER_FILL_MODE (instant | partial | never | reject)
- OPENAI_API_KEY
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU / メモリ / ディスクしきい値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_DISABLE_AUTO_ENV_LOAD

その他
- ドキュメントや設計メモ（PortfolioConstruction.md, StrategyModel.md 等）への参照がソース内コメントにあり、実装はそれらの設計に準拠して行われています。

---
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は変更差分・コミット履歴を参照のうえ適宜調整してください。）