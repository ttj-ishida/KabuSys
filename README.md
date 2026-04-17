# KabuSys

日本株向けの自動売買 / 監視フレームワーク。  
戦略のポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、AI を用いたニュース判定やレジーム検出、研究用ファクター計算などのコンポーネントを含むモジュール群です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数／設定
- 停止・フラグの扱い
- ディレクトリ構成（抜粋）

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株自動売買のための基盤ライブラリ／サービス群を提供する。発注・リコンシリエーション・リスク管理・監視・レポート・研究機能を含む。
- 設計方針の要点:
  - DuckDB / SQLite を用いたデータ基盤
  - Paper Trading 運用用に本番 DB と完全分離可能
  - LLM（OpenAI）を用いたニュースセンチメント / レジーム判定機能を内包
  - 監視は永続化（SQLite）＋LINE通知（オプション）で運用

---

主な機能一覧
- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト: run_execution.py
  - BrokerClientFactory により実運用 / paper_trading (Mock) を切り替え
  - Reconciler による起動時の自動復旧（注文・ポジションの突合）
  - OrderManager / OrderRepository による注文状態管理
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス PID チェック
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - MonitoringEngine: 各モニタを束ねるポーリングループ
  - MonitoringDB: SQLite によるログ保存（system_status / trade_logs / positions / risk_logs / dashboard）
  - streamlit ベースの監視ダッシュボード
  - KillSwitch: 条件に応じた停止フラグ書き込み（data/kill.flag）
  - AlertManager: LINE Messaging API によるプッシュ通知（任意）
- Portfolio / Strategy utilities
  - 銘柄選定、等配分・スコア配分、リスク調整（セクター上限・レジーム乗数）、株数決定（lot rounding、aggregate cap）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、特徴量サマリ
- AI
  - news_nlp.score_news: raw_news を LLM に渡して銘柄ごとのスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF (1321) の MA とマクロ記事の LLM センチメントを合成してレジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

セットアップ手順（ローカル開発用・最小手順）
1. 必要条件
   - Python 3.10 以上（タイプヒントで | 演算子を使用しているため）
   - システムに sqlite3（標準）、および pip でインストール可能なライブラリ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit（ダッシュボードを使う場合）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. リポジトリをクローンしてソースへ
   - git clone <repo-url>
   - cd <repo-root>
   - （本コードは src/ 以下に配置されています。PYTHONPATH を通すかパッケージインストールしてください）
   - pip install -e . などで開発インストール（setup.cfg/pyproject がある場合）

5. .env の準備
   - プロジェクトルートに .env（または .env.local）を作成して環境変数を設定します。
   - 自動ロード: デフォルトで .env/.env.local を読み込みます（OS 環境変数が優先）。自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - LINE_CHANNEL_ACCESS_TOKEN（監視通知用、任意）
     - LINE_USER_ID（監視通知用、任意）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の DB デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

6. データディレクトリ
   - data/（PID やフラグ、データベースファイルを格納）
   - 必要なら作成: mkdir -p data

---

使い方（主要コマンド・モジュール）
- 監視ループ起動（本番向け / 常時実行）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は Settings に従って sqlite_path（monitoring DB）を開きます。Monitoring は環境に依らず本番 sqlite_path を使う実装になっています。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録され、本番 DB と完全分離されます。
  - 実行時は data/execution.pid に PID が書き込まれます。停止は kill.flag / stop_requested.flag による制御で対応。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db   PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 「--」以降の引数はダッシュボードスクリプトに渡されます（DB パス指定など）。

- AI / レジーム判定（プログラムから呼ぶ例）
  - ニューススコアを取得して DB に書き込む:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - OpenAI API キーは api_key 引数で渡すか、環境変数 OPENAI_API_KEY を参照します。

---

重要な環境変数（主要）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は専用 DB を使用（PAPER_TRADING_SQLITE_PATH）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: AI 機能を使うなら必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 時の擬似約定挙動）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

設定読み込みの挙動
- プロジェクトルート（.git または pyproject.toml を基準）にある .env、.env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きできます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

停止・フラグの扱い
- run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視して安全に停止します。
- KillSwitch（条件に応じて）data/kill.flag を書き込み、ExecutionEngine 停止のトリガーにします（デフォルトの kill_flag_path は Settings.kill_flag_path）。
- 実行エンジンは data/execution.pid に PID を書き込み、SystemMonitor は PID ファイルを確認してプロセス生存を監視します。
- kill.flag の削除や stop_requested.flag の操作は運用者が行ってください（KillSwitch.clear() 等のユーティリティあり）。

---

ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - ai/
      - news_nlp.py                   — ニュース NLP（OpenAI）によるスコア付け
      - regime_detector.py            — レジーム判定（MA + macro sentiment）
    - monitoring/
      - monitoring_db.py              — SQLite テーブル作成・CRUD ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - (その他 broker / order 関連)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - data/ (実行時に生成されることが多い)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db
      - kabusys.duckdb (DUCKDB_PATH)
      - execution.pid
      - kill.flag / stop_requested.flag

---

運用上の注意
- Paper Trading は本番 DB と完全分離するよう設計されています。KABUSYS_ENV を適切に設定してください。
- OpenAI API を利用する箇所はネットワーク呼び出しを伴い、レート制限等のエラーに対してリトライやフォールバック処理を入れていますが、API キーとコスト管理に注意してください。
- Monitoring ログ（SQLite）には運用上の重要な情報が蓄積されるためバックアップ・ローテーション等を検討してください。
- process priority / cpu affinity の設定はプラットフォーム依存です。権限不足で設定に失敗した場合は警告のみ出力して処理を継続します。

---

貢献・拡張
- StrategyModel / PortfolioConstruction 等の設計ドキュメントに基づいて、戦略ロジック（シグナル生成など）を本リポジトリの戦略層に組み込むことができます。
- BrokerClient の実装を追加して新しいブローカーをサポート可能です（BrokerClientFactory を拡張）。
- ai ニュース処理／レジーム検出のプロンプトやパース方法は運用に合わせて調整してください。

---

補足（よく使うコマンド例）
- 監視を 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine を paper_trading で起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード起動（監視 DB を指定）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

以上。必要であれば README に記載する環境変数の詳細表、サンプル .env、運用手順（デプロイ・ログローテーション・監視アラート設定）などを追加します。どの情報がさらに必要か教えてください。