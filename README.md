# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ/ユーティリティ群）。

この README はコードベース（src/kabusys 以下）をもとに作成した概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・監視・リサーチ・AI（ニュースセンチメント）等の機能を持つシステムのモジュール構成を示す実装例です。本リポジトリには以下の主要機能が含まれます。

- Execution（発注エンジン）: ブローカーとのやり取り、注文管理、リコンシリエーション
- Monitoring（監視）: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視、アラート送信
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算、セクター調整
- Research（調査）: ファクター計算・特徴量探索・IC評価
- AI（ニュースNLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価と市場レジーム判定
- Tools: Paper Trading の検証レポート生成、Streamlit ダッシュボード等

設計上の特徴:
- DuckDB / SQLite を用いたデータ参照・永続化
- 環境変数 / .env による設定（自動ロード機能あり）
- Paper Trading と本番環境を明確に分離する仕組み
- フェイルセーフ（API障害・データ不足時のフォールバック）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動（run_execution.py）
  - Broker クライアント（本番／Paper Trading 切替）
  - OrderManager / OrderRepository / Reconciler（起動時の自動復旧）
  - RiskManager（発注前リスク判定）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン／ポジション上限監視
  - KillSwitch: 条件で ExecutionEngine を停止するための flag ファイル書き込み
  - AlertManager: LINE Push による通知
  - MonitoringEngine: 各 Monitor を束ねて定期実行
  - Streamlit ダッシュボード（監視用 UI）

- Portfolio
  - 候補選定（スコア順、上位 N）
  - 重み付け（等金額 / スコア加重）
  - セクターキャップ適用
  - ポジションサイズ計算（単元丸め、リスクベースなど）

- Research
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI
  - news_nlp.score_news: raw_news から銘柄ごとのセンチメントを生成して ai_scores へ書き込み（OpenAI）
  - regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime を書き込み

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（SQLite DB を読み取り）
  - streamlit_dashboard: 監視 DB を読み取るダッシュボード

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の `X | Y` 型注記を使用）
- システムに pip が利用可能

1. リポジトリをチェックアウト
   - 任意の方法でソースを取得してください（例: git clone）。

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   下記は本リポジトリで参照されている主な外部依存です。プロジェクトに requirements.txt がない場合は手動でインストールしてください。
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例:
   - pip install duckdb psutil requests openai streamlit

4. data ディレクトリを作成（自動で作られることもありますが手動作成推奨）
   - mkdir -p data

5. 環境変数設定 / .env
   - 本プロジェクトはプロジェクトルートの `.env` / `.env.local` を自動でロードします（デフォルト。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 典型的な .env に含める例（必須は用途により異なります）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...

   - 重要: `Settings` クラスで必須扱いされる環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError を発生します。Paper Trading のみで実行する場合は一部環境変数が不要になる場合がありますが、起動するモジュールに応じて確認してください。

6. DB 初期化
   - 多くの起動スクリプト（run_monitoring, run_execution）は起動時に Monitoring DB のテーブル作成（マイグレーション）を行います。初回は自動的に作成されます。

---

## 使い方

以下は主要スクリプト／コマンドの使い方例です。プロジェクトルートで実行してください。

基本的に Python モジュールとして起動できます:
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution

1. 監視ループの起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を変更可能（秒）。デフォルト 60 秒。
     例: export MONITOR_POLL_INTERVAL=30
   - 実行:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロセスの SIGINT（Ctrl+C）で終了
     - またはプロジェクトルートの data/stop_requested.flag ファイルが存在するとループは検出して終了します（外部から停止指示を出す手段）。

   特記事項:
   - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Monitoring DB）へ書き込みします（監視ログは本番 DB を参照する前提）。

2. Execution（発注エンジン）の起動
   - Paper Trading の場合、環境変数 KABUSYS_ENV=paper_trading とすると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ分離保存されます。
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると起動中のループは検出して Engine.stop() を呼び停止を試みます。
   - PID ファイル:
     - 実行時に data/execution.pid に PID を書きます（設定でパス変更可能）。

3. Streamlit ダッシュボード
   - 監視 DB を読み取り表示する UI。
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 引数 --db で監視 DB のパスを指定できます（デフォルト data/monitoring.db）。

4. Paper Trading 検証レポート
   - ツール: kabusys.tools.paper_verification_report
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション --db で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

   - レポートは稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL を出力します。

5. AI（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡し、target_date のニュースウィンドウに基づいて ai_scores に書き込みます。
     - OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY を使用。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB を参照し ma200 とマクロセンチメントを合成して market_regime テーブルに書き込みます。
   - これらは CLI ではなく関数として提供されています。自動実行ジョブやスクリプトから呼び出してください。
   - 注意: OpenAI API の呼び出しにはネットワーク・レート制限・エラー時のリトライロジックが組み込まれていますが、APIキー未設定時は ValueError を投げます。

6. フラグファイル（停止／kill）
   - data/stop_requested.flag:
     - run_monitoring.py / run_execution.py が定期的にチェックするファイル。存在すると実行ループを終了します（外部停止トリガ）。
   - data/kill.flag:
     - KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガ）。存在を Execution 側で検出して終了する運用になっています。
   - KillSwitch はドローダウンやポジション上限超過の条件で flag を書き込みます（冪等）。

---

## 環境変数（主要）

一部の重要な環境変数を抜粋します。

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須とするコード箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行用ファイルパス（Settings 経由で取得）

設定は .env / .env.local に記述しておくことで自動ロードされます（ただし OS 環境変数が優先され、.env.local は上書きが可能）。

---

## ディレクトリ構成（src/kabusys の主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings クラス（.env 自動ロードロジック含む）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（Paper Trading モード対応）
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py
      - SQLite の監視テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py
      - システム状態・データ鮮度監視（SystemMonitor）
    - trade_monitor.py
      - 注文滞留・約定異常監視（TradeMonitor）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskMonitor）
    - kill_switch.py
      - KillSwitch（フラグファイル書き込み）
    - alert_manager.py
      - LINE push 通知（AlertManager）
    - monitoring_engine.py
      - 各モニタを束ねるエンジン（MonitoringEngine）
    - streamlit_dashboard.py
      - Streamlit を使った簡易ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照されるが省略)
    - risk_manager.py (参照されるが省略)
    - execution_engine.py (参照されるが省略)
    - broker_factory.py (参照されるが省略)
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
  - utils/
    - process_priority.py
  - data/
    - （ランタイムに作成されるファイル）
      - monitoring.db（SQLite: 監視用、デフォルト）
      - kabusys.duckdb（DuckDB）
      - paper_trading.db（Paper Trading 用 SQLite）
      - execution.pid, kill.flag, stop_requested.flag など

（補足: 上記はコードベース内の主要モジュールを抜粋したものです。execution 配下の多くの実装ファイルは本要約内で一部のみ参照されています。）

---

## 運用上の注意点 / ベストプラクティス

- 環境分離
  - Paper Trading（KABUSYS_ENV=paper_trading）は紙上のブローカー実装で DB を分離するため、実運用の DB と混同しないよう環境を明確に分けること。
- API キー管理
  - OPENAI_API_KEY など機密情報は .env.local や環境変数で管理し、レポジトリに含めないでください。
- フラグファイル
  - data/stop_requested.flag / data/kill.flag の存在はプロセスの挙動に影響します。手動でフラグを削除する場合は注意してください。
- ログレベル
  - Settings.log_level を使ってログ出力レベルを制御できます（"DEBUG", "INFO", ...）。
- リソース
  - psutil を使ってプロセス優先度/CPUアフィニティを変更しています。権限制約により失敗する場合は警告になりますが動作は継続します。

---

## よくある操作例（まとめ）

- 監視を 30 秒間隔で起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper Trading で Execution 起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README にサンプル .env のテンプレート、より詳細なコマンド例（systemd ユニット、Dockerfile、CI 設定の例）や API の利用方法（関数シグネチャと引数例）を追加できます。どの情報を優先して追記しましょうか？