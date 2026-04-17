# KabuSys

日本株自動売買システムの一部モジュール群（ポートフォリオ構築、発注実行、監視、リサーチ、AI補助など）。このリポジトリは複数の実行スクリプト／ツールを含み、ローカル環境や Paper Trading（モックブローカー）での検証が可能です。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動方法・主要スクリプト）
- 環境変数（主要設定）
- 運用・停止についての注意
- ディレクトリ構成（抜粋）

---

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークの一部実装です。
- ポートフォリオ構築（候補選定・重み付け・株数算出）や、発注エンジンの立ち上げ・リコンシリエーション、監視（システム状態・注文監視・リスク監視）、ストリームリットによる監視ダッシュボード、Paper Trading の検証ツール、ニュース NLP / レジーム判定などの機能を含みます。
- DB は SQLite（監視ログ / orders など）と DuckDB（時系列・リサーチ向けの大規模データ格納）を利用する設計です。

主な機能
- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分・スコア加重の重み計算
  - セクター集中制限・レジーム乗数適用
  - 単元株丸め・リスクベースの株数算出・aggregate cap のスケーリング
- 実行（Execution）
  - ブローカー抽象化（実口座 / モックを切替可能）
  - OrderManager / ExecutionEngine / RiskManager / Reconciler（再起動時の自動復旧）
- 監視（Monitoring）
  - SystemMonitor: プロセス・CPU/メモリ/ディスク・株価データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ書込み（kill.flag）
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン機能付き）
  - Streamlit ダッシュボード（監視情報の可視化）
- AI / リサーチ
  - news_nlp: OpenAI を使ったニュースの銘柄単位センチメントスコア化（ai_scores への書き込み）
  - regime_detector: マクロ/価格から市場レジーム判定（bull/neutral/bear）
  - ファクター計算（momentum, volatility, value）や特徴量探索ツール
- ツール
  - Paper Trading 検証レポート生成（過去期間の稼働率・注文成功率・レイテンシ等を集計）

セットアップ手順（ローカル開発 / 実行）
1. リポジトリをクローンし、作業ディレクトリに移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存ライブラリをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主な必要パッケージ（最低限）:
     - duckdb, psutil, requests, openai, streamlit
   - 例（手動）:
     - pip install duckdb psutil requests openai streamlit

4. .env の用意（オプション・環境変数）
   - ルートに .env / .env.local を置くと自動でロードされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須の環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（実運用時）
   - OpenAI を使う機能を使う場合: OPENAI_API_KEY を設定

5. data ディレクトリや DB ファイルは起動時に自動作成されることが多いですが、必要に応じて事前に data ディレクトリを作成してください。
   - mkdir -p data

使い方（主要スクリプト / コマンド）
- 実行スクリプトはパッケージとして実行できます（src が PYTHONPATH に含まれている前提）。

1) 監視ループ起動（SystemMonitor を定期実行）
- 目的: system_status / risk_logs / trade_logs などを定期記録し、kill flag 等を監視
- 実行:
  - python -m kabusys.run_monitoring
- オプション（環境変数）:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
- 備考:
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 立ち上げ時にプロセス優先度を "high" にセットします（psutil を使用）。

2) ExecutionEngine 起動（発注エンジン）
- 目的: ブローカーへ発注、OrderRepository 管理、RiskManager などを稼働
- 実行:
  - python -m kabusys.run_execution
- 環境:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します（本番 DB と分離）。
- 停止方法:
  - プロセス間停止フラグ: data/stop_requested.flag を作成すると起動中の run_execution/run_monitoring は停止手続きを行います。

3) Streamlit ダッシュボード（監視）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - ダッシュボードは MonitoringDB の内容を読み取り表示します。監視プロセスが DB を更新している必要があります。
  - DB は読み取り専用モードで開くため、実行中の監視 DB を安全に参照できます。

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/data/paper_trading.db
  - 目的:
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL を判定します。

5) AI 関連（ニュース・レジーム）
- news_nlp.score_news / regime_detector.score_regime は Python API（DuckDB 接続を引数に取る）として使用します。
- OpenAI API キーが必要（api_key 引数、または環境変数 OPENAI_API_KEY）。

環境変数（主要）
- KABUSYS_ENV: environment。development / paper_trading / live（デフォルト: development）。paper_trading はモックブローカーを使用。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所で利用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで必須）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

運用・停止についての注意
- stop_requested.flag:
  - run_monitoring.py と run_execution.py は data/stop_requested.flag の存在を定期チェックし、あれば安全終了します。外部からの停止要求はこのフラグファイルの作成で実行できます。
- kill.flag / KillSwitch:
  - KillSwitch は内部的なリスク検知（ドローダウンやポジション上限）により kill.flag を書き込みます。ExecutionEngine はこの kill.flag を直接監視しているわけではありませんが、運用手順として kill.flag の存在を確認・運用者に通知する役割を持ちます。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイル（デフォルト data/execution.pid）を書きます。SystemMonitor はその PID ファイルが stale（プロセスが存在しない）なら削除してアラートを出します。
- DB マイグレーション:
  - init_monitoring_db は冪等にテーブル作成と簡単なマイグレーション（カラム追加）を行います。起動時に自動で呼ばれます。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 管理（.env 自動読み込みの挙動を含む）
  - run_monitoring.py
  - run_execution.py
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite を使った監視ログ永続化
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository など)
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - data/  (runtime で生成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 時)
    - kabusys.duckdb (デフォルト duckdb)

開発メモ / 実装上の注意
- .env の読み込みは config.py にて自動で行われますが、テストなどで自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- Paper Trading と本番 DB は明確に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しはリトライやレスポンスバリデーションを実装していますが、API キー未設定時は呼び出し前に ValueError を出す設計です。
- process priority / CPU affinity の設定は utils.process_priority でラップされています。権限不足や未対応 OS ではスキップされます。
- DuckDB 接続を渡して関数的にデータ処理を行う設計なので、テスト時は DuckDB にテスト用テーブルを用意して関数を呼ぶとよいです。

サンプル運用コマンド
- 監視プロセス起動（デフォルト設定で）
  - python -m kabusys.run_monitoring
- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

問い合わせ・貢献
- バグ報告や機能追加は Issue を立ててください。ユニットテストや簡単な実行手順を添えてもらえると対応が早くなります。

以上。README の補足や特定ファイル（例: ExecutionEngine の詳細な起動フローや broker の実装）を追加でまとめる必要があれば指示してください。