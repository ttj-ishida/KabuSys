KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株の自動売買・検証・監視を想定した Python ベースのプロジェクトです。  
主な目的は以下の通りです：

- 戦略に基づく発注（ExecutionEngine / OrderManager）
- 実行・約定のリコンシリエーション（Reconciler）
- システム・注文・リスク監視（Monitoring モジュール）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- 研究用ファクター計算（DuckDB を利用したファクター群）
- Paper Trading 用の検証レポート生成
- ニュースを使った NLP スコアリングおよびレジーム判定（OpenAI 利用）
- ストリームリットによる監視ダッシュボード

特徴
----
- モジュール化された設計（execution / monitoring / portfolio / research / ai / tools）
- DuckDB と SQLite を併用（価格・ファクターデータ = DuckDB、監視・発注ログ = SQLite）
- Paper Trading と Live を環境切り替えで分離（PAPER_TRADING 用 DB を別ファイルで管理）
- LINE によるアラート送信（AlertManager）
- OpenAI を用いたニュースセンチメント自動評価（エラー耐性とリトライ実装）
- 監視側に Kill Switch とフラグファイルによる安全停止機構

動作要件（代表）
----------------
- Python 3.9+
- 必須パッケージ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai (AI 機能を使う場合)
  - streamlit (ダッシュボード)
- その他、ブローカー API クライアントや追加依存がある場合は各環境に合わせて導入してください。

セットアップ手順
----------------
1. リポジトリをクローン / 展開：
   - この README 想定のパス: src/kabusys 以下にパッケージが存在

2. 仮想環境作成（任意）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt がある場合はそちらを使用してください。

4. 環境変数設定 (.env)
   - プロジェクトルートに .env（または .env.local）を置くことで自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...            (AI 機能を使う場合)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

   - .env の書式ルールは kabusys.config でパースされ、コメントやクォートをサポートします。
   - .env.example を参考に必要な変数を準備してください（プロジェクト内にある想定）。

初期データ・ディレクトリ
------------------------
- デフォルト DB/ファイルパス（Settings 参照）:
  - data/kabusys.duckdb   (DuckDB)
  - data/monitoring.db    (監視用 SQLite)
  - data/paper_trading.db (Paper Trading 用 SQLite)
  - data/execution.pid    (実行 Engine の PID)
  - data/kill.flag        (Kill Switch フラグファイル)
- monitoring DB のテーブルは init_monitoring_db() により自動作成・マイグレーションされます。

使い方（主要なコマンド）
-----------------------

1. ExecutionEngine を起動（発注エンジン）
   - 本番/開発/ペーパートレードは KABUSYS_ENV により切替
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と完全分離）
     - 実行中は PID ファイルを書き、data/stop_requested.flag や data/kill.flag により停止を検知する

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
   - 挙動:
     - SystemMonitor / TradeMonitor / RiskMonitor 等を使って定期チェックを行い、監視ログを SQLite に保存。LINE 通知や kill.flag 書き込みを行う。

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で表示します。MonitoringEngine を先に起動してデータを蓄積してください。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db。別 DB を使う場合は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を指定。

5. AI / ニュース NLP（プログラム的に利用）
   - 例（Python REPL やスクリプト内）:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  # OpenAI API キー必須（または環境変数 OPENAI_API_KEY）
   - score_news は raw_news と news_symbols を集約して OpenAI に送信し、ai_scores テーブルへ書き込みます。
   - market regime 判定は kabusys.ai.regime_detector.score_regime を利用可能（OpenAI キー必要）。

構成（ディレクトリ概要）
-----------------------
以下は主要なパッケージ / ファイルと役割の要約（src/kabusys 配下）:

- __init__.py
  - パッケージ公開情報（バージョン等）

- config.py
  - 環境変数の読み込み・Settings クラス（設定値の集中管理）

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV による Paper/Live 挙動の切替や PID 管理。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL をサポート。

- execution/
  - broker_api, broker_factory, execution_engine, order_manager, order_repository, reconciler など
  - 発注・ブローカー連携・再同期ロジックを含む

- monitoring/
  - monitoring_db.py : 監視ログ用 SQLite のスキーマと永続化 API（init_monitoring_db, MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py : 個別チェックロジック
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : LINE push を使った通知
  - kill_switch.py : フラグファイルで ExecutionEngine 停止判定
  - streamlit_dashboard.py : 監視ダッシュボード

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み計算・ポジションサイズ算出・セクター制限等の純粋関数群

- research/
  - factor_research.py : モメンタム / ボラティリティ / バリュー計算（DuckDB SQL）
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー等

- ai/
  - news_nlp.py : raw_news → OpenAI による銘柄別センチメント付与（ai_scores へ書込）
  - regime_detector.py : ETF MA とマクロニュースの LLM 結果を合成して市場レジーム判定

- tools/
  - paper_verification_report.py : Paper Trading の検証レポート生成（CLI）

- utils/
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

重要な実装上の注意
-----------------
- DB 分離:
  - Paper Trading (KABUSYS_ENV=paper_trading) の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring DB と分離します。
- モニタリングは常に本番 sqlite_path を使います（run_monitoring の実装上の仕様）。
- OpenAI を使う機能:
  - API キー（OPENAI_API_KEY）または各関数呼び出しで明示的に api_key を指定する必要があります。
  - レート制限・ネットワークエラーに対してリトライ/フォールバック処理が組み込まれています。
- プロセス優先度設定:
  - 起動スクリプトは set_process_priority("high") を試みます。権限や OS により失敗する場合があります（警告ログ）。

トラブルシューティング
----------------------
- .env 読み込み:
  - プロジェクトルートは .git または pyproject.toml を起点に自動検出されます。ルートが検出できないと自動ロードをスキップします。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に対して後方互換的にカラム追加（peak_value, latency_ms）を行います。
- PID / フラグファイル:
  - stale PID（存在しない PID が書かれた execution.pid）を検出すると削除してアラートを上げます。
  - kill.flag を手動で書くことで ExecutionEngine を安全に停止させられます（KillSwitch）。

開発・拡張
----------
- 各モジュールは比較的独立しており、テストしやすい純粋関数（portfolio 等）と副作用を持つ I/O 層（monitoring_db, order_repository 等）に分離されています。
- AI 呼び出し部は _call_openai_api をモックすることでユニットテスト可能です（実装内に注記あり）。
- DuckDB クエリは関数内で構築されているため、研究用途の拡張が容易です。

ライセンス・貢献
----------------
- この README ではライセンス情報を含めていません。リポジトリに LICENSE があればそちらを参照してください。  
- バグ報告や PR はリポジトリルールに従ってください。

付録: 実行例
--------------
- 監視ループを 30 秒間隔で実行（UNIX 系の一時的な設定例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine を Paper Trading モードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上が本プロジェクトの概要・導入手順・主要な使い方です。実装の詳細や追加の設定は該当モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば README を拡張してデプロイ手順・CI・テスト実行方法などを追加します。