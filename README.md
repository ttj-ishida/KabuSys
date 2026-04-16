# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ／実行スクリプト群）。  
この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

なおソースコード内のコメントや Settings クラスを参照しているため、挙動の詳細説明は実装に基づいています。

---

プロジェクトで使われている主な外部ライブラリ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

（実際の requirements.txt があればそれを利用してください。ここでは主要な依存を列挙しています。）

---

概要
- KabuSys は日本株の自動売買を想定したコンポーネント群を提供します。
  - 注文作成・管理（ExecutionEngine など）、
  - 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）、
  - ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）、
  - リサーチ（ファクター計算、特徴量解析）、
  - AI 補助モジュール（ニュース NLP によるセンチメント、レジーム検出）、
  - 運用ツール（paper trading 検証レポート、Streamlit ダッシュボード）、
  - ユーティリティ（プロセス優先度設定等）。
- 設定は環境変数／`.env` ファイルで行います。Settings クラス（kabusys.config.Settings）で各種キーをラップしています。

---

主な機能（抜粋）
- Execution
  - Broker クライアント抽象化（本番／paper_trading 切替）
  - OrderManager / ExecutionEngine / Reconciler による発注・復旧処理
  - Paper trading モードは本番 DB と分離して `data/paper_trading.db`（デフォルト）に記録
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス 存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文チェック、約定価格の異常検知
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager：閾値超過時にフラグファイルを書き ExecutionEngine を停止、LINE でアラート送信
  - Streamlit ベースの監視ダッシュボード（read-only）
- Portfolio
  - 候補選定、等配分・スコア配分、セクターキャップ適用、ポジションサイズ計算（単元丸め・集約キャップ）
- Research
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）や将来リターン、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI (gpt-4o-mini) によるニュースセンチメント取得と ai_scores への書き込み（バッチ処理・リトライ・バリデーションあり）
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

セットアップ手順（開発 / 実行環境）
1. Python バージョン
   - Python 3.10+ を推奨（ソースでの型表記や構文に依存）。

2. 仮想環境（推奨）
   - venv を使う例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - 実際はプロジェクトの requirements.txt があればそれを利用してください:
     - pip install -r requirements.txt

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（Settings._require により未設定だと例外になるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意（主なもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | ...
     - OPENAI_API_KEY: OpenAI 利用時に必要
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モデル）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

5. data ディレクトリ
   - スクリプトが参照／書き込みするフラグや pid ファイルは `data/` 下に格納されることが多いです（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。必要に応じてディレクトリを作成してください。

---

使い方（代表的な実行方法）

※ いずれもプロジェクトルートから実行することを想定します。

1) 監視ループを起動（run_monitoring.py）
- 説明: SystemMonitor を定期ポーリングして monitoring DB にログを残します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。実行時にプロセス優先度を "high" に設定します。
- 実行例:
  - python -m kabusys.run_monitoring
- 環境変数例:
  - export MONITOR_POLL_INTERVAL=30

- 停止:
  - プロジェクトルートの data/stop_requested.flag ファイルを作成するとループを終了します（存在を検知して終了）。または Ctrl+C。

2) ExecutionEngine を起動（run_execution.py）
- 説明: ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite に記録して本番 DB と完全に分離します。
- 実行例:
  - python -m kabusys.run_execution
- 特記事項:
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止指示は data/stop_requested.flag または外部で PID にシグナルを送る等。

3) Streamlit ダッシュボード（監視 UI）
- 説明: monitoring DB の内容を簡易ダッシュボードで表示します（read-only）。
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 注意:
  - SQLite を read-only モードで開くため、MonitoringEngine が DB を生成している必要があります。

4) Paper Trading 検証レポート（tools）
- 説明: paper_trading の SQLite DB（デフォルト: data/paper_trading.db）を参照して稼働率や注文成功率、レイテンシなどの検証レポートを標準出力に出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 指定 DB を使う場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5) AI モジュール（ニュース NLP / レジーム検出）
- news_nlp.score_news / regime_detector.score_regime をプログラムから呼び出すか、スクリプト化して実行します。OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
- 例（Python 内から）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

6) KillSwitch / フラグによる停止
- KillSwitch は監視結果に基づいて `data/kill.flag` を書き込み、ExecutionEngine を停止させるための仕組みです。KillSwitch の write は冪等で、既に存在する場合は書き込みをスキップします。
- ExecutionEngine 側は `data/kill.flag` の存在を参照して停止動作を実装しています（monitoring 側での一連の連携により安全停止を実現）。

---

主要な環境変数（まとめ）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用・動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
  - MONITOR_POLL_INTERVAL: Monitoring ポーリング秒（run_monitoring 用）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化
- DB 関連
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject（mock の約定挙動）
- PID / Kill flag
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" にすると起動時に kill.flag を削除）

---

ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード、Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム検出（MA200 + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 + MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他: broker_factory, execution_engine, order_repository 等はプロジェクトに存在)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py

- data/
  - （実行時に利用する DB ファイルやフラグファイル）
  - data/monitoring.db（デフォルト）
  - data/paper_trading.db（paper_trading の場合のデフォルト）
  - data/kabusys.duckdb（DuckDB のデフォルト）
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

（上記はリポジトリの主要モジュールと、実行時に想定されるファイルをまとめたものです）

---

運用上の注意 / ヒント
- .env 自動読み込みはプロジェクトルートを .git または pyproject.toml で判定して行われます。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。
- paper_trading モードは本番 DB と分離するため、検証が本番データに影響しません。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API コールはレート制限や一時エラーを考慮してリトライロジックが組まれていますが、API キーやコスト管理は運用者で行ってください。
- Monitoring / Execution の停止には data/stop_requested.flag や data/kill.flag が利用されます。これらのファイル管理（作成・削除）に注意してください（誤って残していると起動を阻害します）。

---

貢献・拡張のポイント（参考）
- Broker クライアントや ExecutionEngine のインテグレーションテスト追加
- DuckDB スキーマ拡張・ファクター追加
- NEWS NLP のプロンプト改善やモデル切替（MODEL 名は定数化されています）
- Streamlit ダッシュボードの視認性向上・操作性向上

---

問い合わせ
- 実装内容の詳細は各モジュールの docstring / ソースコメントを参照してください。README に無い実行フローや設定は該当ファイル内コメントに記述されています。

以上。README として必要な追加説明や、サンプル .env の記載（テンプレート）を希望される場合は、その旨を教えてください。