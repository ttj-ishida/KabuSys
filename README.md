KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下のような主要機能が含まれます。

- 注文管理・発注エンジン（ExecutionEngine）の起動スクリプト
- 監視（MonitoringEngine）・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・リサーチユーティリティ（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI API 利用）
- Paper Trading 用検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード（SQLite を参照）

設計思想の要点：
- DB（SQLite / DuckDB）をデータ永続化・分析に利用
- 本番 / paper_trading / development を環境で切り替え可能
- LLM 呼び出しは失敗時にフェイルセーフでフォールバックする設計

機能一覧
--------
- 実行エンジン起動: run_execution.py（KABUSYS_ENV により paper_trading を分離）
- 監視ループ起動: run_monitoring.py（システム状態・注文状態・リスク監視）
- 監視エンジン・アラート: LINE プッシュ通知（AlertManager）
- Kill Switch: フラグファイルで ExecutionEngine を安全停止
- Streamlit ダッシュボード: 監視データの可視化
- Paper Trading レポート: tools.paper_verification_report による検証レポート生成
- ポートフォリオ構築ユーティリティ: 候補選定 / 等重・スコア加重 / ポジションサイズ計算
- リサーチ: momentum/value/volatility ファクター計算、将来リターン、IC 計算
- AI モジュール: ニュースセンチメント（score_news）、市場レジーム判定（score_regime）

動作環境・依存
--------------
- Python 3.10 以上（型注釈で | を使用しているため）
- 必要パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI モジュールからの利用時)
- SQLite は標準ライブラリで利用
- 上記は例です。実際は requirements.txt を用意して pip install -r することを推奨します。

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
2. 仮想環境の作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）:
   - pip install duckdb psutil requests streamlit openai
4. 環境変数の設定:
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE — paper_trading の Fill モード: instant | partial | never | reject（デフォルト: instant）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE Push 通知用（任意）
   - PID_FILE_PATH, KILL_FLAG_PATH など監視関連設定
   - LOG_LEVEL（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
- 監視ループを起動する（永続プロセス）:
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書きできます（例: 30 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作: PID 優先度を "high" に上げ、monitoring DB（SQLITE_PATH）へログを記録します。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用します（監視ログは本番 DB に集約）。

- 実行エンジン（ExecutionEngine）を起動する:
  - paper_trading モード:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録して本番 DB と分離します。
  - 実行:
    - python -m kabusys.run_execution

- Streamlit ダッシュボードを起動する:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - オプション --db で読み込む SQLite パスを指定可能（デフォルト data/monitoring.db）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI / リサーチ機能（プログラムから呼び出す）:
  - ニュースセンチメント（ai.news_nlp）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - conn は DuckDB 接続（duckdb.connect(...) の戻り値）
      - api_key を与えない場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定（ai.regime_detector）:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API を使うため、OPENAI_API_KEY の設定を忘れないでください。失敗時はフェイルセーフなフォールバックを行う設計です（ログ出力）。

重要な挙動メモ
--------------
- .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）を探索して .env/.env.local を自動で読み込みます。
  - OS 環境変数は保護され、.env.local の override があっても OS 環境変数は上書きされません。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒単位で環境変数から上書きできます。不正値や 0 以下が設定された場合はデフォルト 60 秒にフォールバックします。
- Paper Trading:
  - KABUSYS_ENV=paper_trading によりブローカーや DB を本番と切り離して動作します（安全に検証可能）。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag に理由を書き込み ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等に書き込みを行います。
- DB 初期化:
  - monitoring_db.init_monitoring_db(conn) は冪等に監視用テーブル群を作成し、必要に応じて簡単なスキーママイグレーション（列追加）を実行します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数/設定管理（.env 自動ロード、Settings クラス）
- run_monitoring.py
  - SystemMonitor の polling ループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 分離）
- ai/
  - news_nlp.py        — ニュース NLP スコアリング（OpenAI 使用）
  - regime_detector.py — 市場レジーム判定（OpenAI 使用）
- monitoring/
  - monitoring_db.py       — SQLite ベースの監視ログ永続化層
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py       — 注文滞留・約定異常検知
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の書き込みロジック
  - alert_manager.py       — LINE Push 通知ユーティリティ
  - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ... — 発注管理・リコンシリエーション等
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数計算・制約処理
  - risk_adjustment.py     — セクター制限・レジーム乗数
- research/
  - factor_research.py     — momentum/value/volatility 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

開発・運用上の注意
------------------
- DuckDB の prices_daily / raw_financials / raw_news 等のテーブルは本リポジトリには含まれません。データ投入方法は別途用意してください。
- OpenAI API を利用する機能は外部 API 呼び出しを含むため、API キーの管理やレート制限の考慮が必要です。モジュール内でリトライ・バックオフ実装がありますが、実運用ではコスト・プライバシーに注意してください。
- run_execution/run_monitoring はプロセス優先度を上げるため OS 権限が必要な場合があります（psutil による nice/priority 設定で AccessDenied になる可能性をログに出してスキップします）。
- ログレベルは LOG_LEVEL 環境変数で制御できます（INFO がデフォルト）。

貢献
----
バグ報告・プルリクエスト歓迎です。コードやドキュメントの改善、テスト追加、デプロイ用のスクリプト（systemd ユニット等）をいただけると助かります。

以上。まずは .env を整え、監視 DB（data/monitoring.db）と DuckDB（data/kabusys.duckdb）への接続を確認してから run_monitoring/run_execution を順に動かしてみてください。必要であれば README を拡張してデータ投入手順や systemd / Docker 化のガイドも追加できます。