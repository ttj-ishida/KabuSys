README
======

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模な Python パッケージ群です。本リポジトリには以下の主要機能が含まれます:

- 実行エンジン (ExecutionEngine) — 注文作成、発注/同期、リスク管理、再コンシリエーション
- 監視コンポーネント — システム状態、注文滞留、ドローダウン等の定期チェックとログ記録
- ポートフォリオ構築ユーティリティ — 候補選定、重み付け、ポジションサイズ計算、セクター制限
- 研究モジュール — ファクター計算、将来リターン、IC 計算、統計サマリ
- AI 統合 — ニュース NLP による銘柄毎センチメント評価、レジーム判定 (OpenAI API 経由)
- 運用ツール — Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

特徴
----
- モジュール設計でテストしやすく分離された責務（DB 層 / ビジネスロジック / API 呼出しの分離）
- Paper Trading と Live を明確に分離 (別 SQLite DB を使用)
- DuckDB を使った時系列データ処理（ファクター計算等）
- OpenAI を使ったニュースセンチメント（オプション）
- 監視デーモンとダッシュボードで運用可視化

セットアップ手順
----------------

前提
- Python 3.10+（typing | match 機能はコードに依存しませんが、新しい環境を推奨）
- SQLite は標準ライブラリで利用可
- 以下の外部パッケージを使用しています（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
  - それぞれ pip でインストールしてください

仮想環境作成と依存インストール例
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil requests openai streamlit
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install --upgrade pip
  - pip install duckdb psutil requests openai streamlit

環境変数
- 推奨: プロジェクトルートに .env / .env.local を置き、必要な変数を記載します。
- 自動ロード: config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動探索して .env(.local) を読み込みます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 代表的な環境変数（必須 / 重要）:
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - JQUANTS_REFRESH_TOKEN: （必須）
  - KABU_API_PASSWORD: （必須）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に使用（未設定なら送信はスキップ）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 時の SQLite DB（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は常に本番 sqlite_path を使う設計です
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PAPER_FILL_MODE: paper_trading の MockBroker の挙動 ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
- その他: MONITOR_POLL_INTERVAL（監視ループの秒間隔をオーバーライド、デフォルト 60）

初期データディレクトリ
- data/ 以下に DB ファイルやフラグファイルを置きます（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）。
- スクリプトは起動時に必要なテーブルを作成（冪等）します。

使い方
------

実行エンジン（Execution）
- 基本起動:
  - python -m kabusys.run_execution
- Paper Trading モードで起動（MockBroker を使用し、paper_trading 用 DB に記録）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 実行の振る舞い:
  - プロセス優先度を "high" に設定しようとします（psutil により権限のない場合はログ警告でスキップ）
  - 起動時に stop flag（data/stop_requested.flag）を検査。既に立っている場合は起動せず終了します
  - 実行中に stop flag が作られるとエンジンを安全に停止します
- PID ファイル: data/execution.pid が作成されます（存在チェックにより stale PID を検出）

監視ループ（Monitoring）
- 基本起動:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- 挙動:
  - Settings.env に依らず、本番 sqlite_path（data/monitoring.db）を使って監視情報を記録します
  - SystemMonitor, TradeMonitor, RiskMonitor を定期的に実行し、MonitoringDB（system_status / trade_logs / risk_logs / positions / dashboard）に保存します
  - stop flag（data/stop_requested.flag）が出現するとループを終了します

Streamlit 監視ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - ダッシュボードは monitoring DB を read-only で開いて簡易的にメトリクス・ポジション・最近の注文・リスクログを表示します

Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定できます（デフォルトは data/paper_trading.db）
- レポート内容:
  - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などの指標を出力し PASS/FAIL を判定します

AI 機能（ニュース NLP・レジーム判定）
- これらは OpenAI API を利用します。利用には OPENAI_API_KEY が必要です。
- ニュースセンチメント:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（raw_news / news_symbols / ai_scores テーブル）を渡して日次で ai_scores を更新します
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます
- 両モジュールとも API エラーは冪容的に扱い、失敗時はフォールバック値（0.0 等）で継続する設計です

停止 / フラグの扱い
- stop_requested.flag:
  - run_monitoring.py / run_execution.py で監視する停止フラグ。プロジェクトルートの data/stop_requested.flag（スクリプトの実行パスに依存）を置くとループを安全に終了します
- kill.flag:
  - KillSwitch が生成する停止要求ファイル（ExecutionEngine に外部停止シグナルを与える用途）。path は Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch.clear() を呼ぶことで削除できます（運用ツールや手動スクリプトでクリアしてください）
- PID ファイル:
  - 実行プロセスは data/execution.pid に PID を書くことがあります。SystemMonitor は stale PID を検出すると削除しログを記録します

開発 / テストのヒント
- 自動 .env 読み込みはプロジェクトルートを基準に行われます。CI/テスト時にロードを防ぐには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で調整できます（秒、正の整数）
- psutil による優先度変更・CPU affinity 設定は権限が必要な場合あり。失敗は警告でスキップされます

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ（__version__ 等）
- config.py
  - 環境変数 / .env の読み込み、Settings クラス（KABUSYS_ENV, DB パス, 各種閾値 等）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBroker）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / CRUD
  - system_monitor.py — CPU/メモリ/Disk、データ鮮度、プロセス監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag 書込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — LINE Push 通知ラッパー
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文生成・状態管理 API
  - reconciler.py — 起動時の再同期間合 / ポジション照合
  - （その他: broker_factory, execution_engine, order_repository 等が存在）
- portfolio/
  - portfolio_builder.py — 候補選定とスコア順ソート
  - position_sizing.py — 株数計算、aggregate cap、lot rounding
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — raw_news を LLM に投げて ai_scores に保存
  - regime_detector.py — ETF 1321 MA200 とマクロニュースでレジーム判定
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）リポジトリの一部ファイル（たとえば kabusys.data や execution 内の細部など）はここに抜粋されているコードと併せて利用されます。必要に応じて該当モジュールの実装を参照してください。

ライセンス / 貢献
----------------
- 本 README ではライセンス情報が含まれていません。実際のプロジェクトでは LICENSE ファイルを追加してください。
- バグ修正・改善提案は Pull Request を歓迎します。大きな変更は設計方針（特に注文 / リスク周り）に影響するため事前相談を推奨します。

最後に
------
この README はソースから読み取れる仕様と運用上の注意点をまとめたものです。実運用前に .env 設定・API キー・DB パス・権限周り（psutil による優先度設定など）を必ず確認してください。質問や追記したい項目があれば教えてください。