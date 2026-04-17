# KabuSys

日本株向けの自動売買・調査・監視フレームワーク（開発版）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要な依存関係
- セットアップ手順
- 実行 / 使い方
  - 実行エンジン (ExecutionEngine)
  - 監視 (Monitoring)
  - 監視ダッシュボード (Streamlit)
  - Paper Trading 検証レポート
  - AI 関連処理（ニュースNLP / レジーム判定）
- 環境変数 (主なもの)
- 停止・制御方法
- ディレクトリ構成（概要）
- 開発メモ / 注意点

---

プロジェクト概要
- KabuSys は日本株自動売買向けのモジュール群です。シグナルからポートフォリオ構築、発注管理、実行エンジン、監視・アラート、リサーチ用ファクター計算、AI（OpenAI）を使ったニュースセンチメント評価などを含みます。
- コードは純粋関数（ポートフォリオ構築等）と、DB/ブローカー連携を含む実行系で構成されています。監視・リスク管理機能を備え、必要に応じて ExecutionEngine の停止（kill flag）を発行できます。

主な機能一覧
- ExecutionEngine: ブローカーとの発注・注文状態管理、リスク管理、再起動時のリコンシリエーション
- Monitoring: システム状態・データ鮮度・注文滞留・約定異常・ドローダウン監視、アラート（LINE）送信、kill switch
- Dashboard: Streamlit ベースの監視ダッシュボード（SQLite を読み取り専用で表示）
- Portfolio construction: 候補選定、重み付け（等分/スコア加重）、ポジションサイジング、セクター制約、レジーム乗数
- Research: DuckDB を使ったファクター計算（Momentum / Volatility / Value）・IC 計算など
- AI: OpenAI を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- ユーティリティ: プロセス優先度設定、.env ロード、DB 初期化、paper trading 用分離 DB

必要な依存関係（代表例）
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）
- その他（開発用に pytest 等）

セットアップ手順（ローカル開発向け）
1. レポジトリをクローンし、作業ディレクトリを project root とする（.git または pyproject.toml を基準に自動検出）。
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要なら requirements.txt / poetry / pipfile を使って環境構築）
4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（本番/ブローカー連携時）、OPENAI_API_KEY（AI 機能利用時）など。下記「環境変数」参照。
5. データディレクトリ
   - デフォルトの DB 等は data/ 配下を想定します（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）。
   - 初回実行時にテーブルは自動作成（init_monitoring_db）されます。

実行 / 使い方

基本的にパッケージモードで実行できます（プロジェクトルートが正しく検出されることが前提）。

1) 実行エンジン (ExecutionEngine)
- 目的: 発注・注文管理を行う実行プロセスを起動します。
- 実行:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い、paper trading 用の SQLite（デフォルト data/paper_trading.db）に記録して本番 DB から完全分離します。
  - 実行開始時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します。
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil によるため権限等で失敗することがあります）。

2) 監視 (Monitoring)
- 目的: SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行して監視ログを記録し、必要時 kill.flag を書いて ExecutionEngine を停止可能にします。
- 実行:
  - python -m kabusys.run_monitoring
- オプション・設定:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。無効値や 0 以下は無視され、デフォルトにフォールバックします。
  - 監視は Settings による sqlite_path（デフォルト data/monitoring.db）に書き込みます。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用します（paper_trading と混ぜたくないため）。
  - 監視もプロセス優先度を "high" に設定します。

3) Streamlit ダッシュボード（監視ビュー）
- 目的: monitoring.db を読み取り専用で可視化する簡易ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 備考:
  - DB を読み取り専用で開く（URI に mode=ro を付与）しているため、MonitoringEngine が稼働していることが前提です。
  - エラー時は「Start MonitoringEngine first」と表示されます。

4) Paper Trading 検証レポート
- 目的: paper trading DB のログから稼働率 / 注文成功率 / レイテンシなどを集計して PASS/FAIL 判定レポートを出力します。
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 任意期間を指定する例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - 環境変数 PAPER_TRADING_SQLITE_PATH を設定するか、--db オプションで指定できます。
- レポートで使う基準（デフォルト）:
  - 稼働率 >= 99.0%
  - 注文成功率（Filled/Created） >= 90.0%
  - 送信率（Sent/Created） >= 95.0%
  - P95 レイテンシ <= 200 ms

5) AI 関連
- ニュースセンチメント（news_nlp.score_news）
  - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) を呼ぶことで銘柄ごとの ai_score を生成して ai_scores テーブルに保存します。
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - API キーは引数または環境変数 OPENAI_API_KEY から取得します。未設定だと ValueError を送出します。
- レジーム判定（regime_detector.score_regime）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して 'bull'|'neutral'|'bear' を判定し、market_regime テーブルに保存します。
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

環境変数（代表）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルトは development。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須時は Settings が例外を投げます）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- PAPER_FILL_MODE: paper trading の MockBrokerClient の約定方式（instant | partial | never | reject）。デフォルト "instant"。
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: PID / kill flag のパスや振る舞いを制御
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

停止・制御方法
- 実行停止:
  - ExecutionEngine を優雅に停止するには data/kill.flag に理由を書き込むか、monitoring の KillSwitch を通じて作成します（KillSwitch._write_flag が行います）。ExecutionEngine は起動時に kill_flag_clear_on_start を参照する挙動がある設定もあります。
  - run_monitoring / run_execution のスクリプトはそれぞれ data/stop_requested.flag を検知するとループを抜けて終了します。
- PID 管理:
  - ExecutionEngine は pid ファイルを作成します。system_monitor は stale PID を検出して削除し、リスクログに記録することがあります。

ディレクトリ構成（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (Settings, .env ロードロジック)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (Monitoring 起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (DB 周り)
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
  - utils/
    - process_priority.py

開発メモ / 注意点
- Settings はプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の DB は production の monitoring DB を使用するよう設計されています（KABUSYS_ENV にかかわらず sqlite_path を使用）。paper_trading 実行時は paper_sqlite_path を分離して運用してください。
- psutil でプロセス優先度 / CPU affinity を操作します。権限やプラットフォームによっては設定に失敗し、警告が出ますが処理は継続します。
- OpenAI を呼ぶコードはリトライ・バリデーション処理を備えていますが、API キーやクォータ、レスポンス形式に依存するため運用時は監視とログの確認を推奨します。
- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを利用する想定です。research / ai モジュールはそれらテーブルを参照します。

ライセンス・貢献
- README 上では省略。開発元のポリシーに従ってください。

---

簡単な実行例（ローカル開発）
1. .env を作成（例）
   - KABUSYS_ENV=development
   - OPENAI_API_KEY=sk-...
   - KABU_API_PASSWORD=...
   - JQUANTS_REFRESH_TOKEN=...
2. 監視を起動
   - python -m kabusys.run_monitoring
3. 実行エンジン（paper_trading）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
4. ダッシュボード表示
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
5. Paper Trading レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要に応じて README をプロジェクト固有の運用手順・CI/CD 向けの起動方法・Dockerfile・サービス定義（systemd / docker-compose）などで拡張してください。