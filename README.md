KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行う軽量なPythonパッケージ群です。本リポジトリは以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象（paper/live分離）
- 監視サブシステム（System / Trade / Risk モニタ、kill-switch、LINE アラート）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチツール（ファクター計算・前方リターン・IC 計算）
- ニュース NLP（OpenAI を用いたニュースセンチメント評価）
- Streamlit ダッシュボード、検証レポート生成ツール

主な特徴
--------
- 環境切替：KABUSYS_ENV により development / paper_trading / live を切替え可能。paper_trading 時はブローカーはモックを使い、DB も分離（data/paper_trading.db）。
- 監視と自動停止（Kill Switch）：ドローダウンやポジション上限等を監視して停止フラグ（data/kill.flag）を書き込めます。
- DuckDB を用いたリサーチ向け高速集計（prices_daily / raw_financials 等を参照）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントと市場レジーム判定（API 呼び出しは冪等・リトライを実装）。
- Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を表示）。

前提（依存パッケージ）
--------------------
主な依存（抜粋）:
- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit

（プロジェクト内に requirements.txt が無い場合は上記を pip でインストールしてください）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートに設定します。
   - パッケージは src/ 配下にあるため、実行時はプロジェクトルートが PYTHONPATH に含まれるか、パッケージをインストールしてください（pip install -e . など）。

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai requests streamlit

3. 環境変数の設定:
   - プロジェクトルートに .env を置くことで自動ロードされます（.env.local は上書き）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 重要な環境変数（代表例）:
   - KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ニュースNLP / レジーム判定で必須）
   - LINE_CHANNEL_ACCESS_TOKEN: LINE push 用トークン（任意）
   - LINE_USER_ID: LINE push 宛先ユーザID（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 参照（デフォルト値あり）

   詳細は kabusys.config.Settings のプロパティをご確認ください。

使い方（主要コマンド）
--------------------

- 監視ループ（SystemMonitor のポーリング）
  - 簡易起動:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足:
    - 監視は常に本番用 sqlite_path を使用します（環境に依らず monitoring DB は同一パスを使用）。

- 実行エンジン（ExecutionEngine）
  - デフォルト（development / live）:
    - python -m kabusys.run_execution
  - Paper Trading（モックブローカー、DB 分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 補足:
    - paper_trading の場合、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）が使用され、本番 DB と完全に分離されます。

- Paper Trading 検証レポート（コマンドライン）
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で SQLite ファイルパスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH との優先度: --db > 環境変数 > デフォルト）

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースは読み取り専用 URI で開かれます（start 前に MonitoringEngine が DB を作成/更新している必要があります）。

- OpenAI を使った処理
  - ニューススコア（ai.score_news）:
    - Python から呼ぶ例:
      - from kabusys.ai import score_news
      - score_news(duckdb_conn, target_date, api_key="YOUR_KEY")
    - またはモジュールを通じて組み込み処理として呼び出します。OPENAI_API_KEY を設定しておくと api_key 引数を省略できます。
  - レジーム判定（ai.regime_detector.score_regime）:
    - 同様に duckdb_conn と target_date、api_key を渡して実行します。

内部の挙動・注意点
-----------------
- .env ロード:
  - .env（および .env.local）はプロジェクトルート（.git または pyproject.toml を探索）を基準に自動読み込みされます。
  - 既存 OS 環境変数は保護され、.env.local は上書きモードで読み込まれます。
- DB 初期化:
  - Monitoring 用 SQLite は init_monitoring_db() により必要テーブルが自動作成されます（冪等的）。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil が必要）。権限不足や非対応 OS の場合は警告してスキップします。
- OpenAI 呼び出し:
  - レート制限や一時的な通信エラーに対して指数バックオフでリトライします。失敗時はフォールバック（0.0 等）して継続する設計です。
- 安全性:
  - ExecutionEngine は paper_trading と live を明確に分離する設計。実運用時は env 設定を慎重に行ってください。
- ロギング:
  - デフォルトは logging.INFO。Settings.log_level で制御できます。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py — パッケージ初期化
- config.py — 環境変数 / 設定管理（Settings）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — monitoring DB のスキーマ定義・永続化 API（MonitoringDB）
- system_monitor.py — システム状態 / データ鮮度チェック
- trade_monitor.py — 注文滞留 / 約定異常検出
- risk_monitor.py — ドローダウン・ポジション数監視
- kill_switch.py — kill.flag 管理（Execution 停止シグナル）
- alert_manager.py — LINE による通知
- monitoring_engine.py — 各 Monitor をまとめるエンジン
- streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

src/kabusys/execution/
- order_manager.py, reconciler.py, ... — 注文管理・再同期ロジック（OrderManager / Reconciler）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・等重 / スコア重み
- risk_adjustment.py — セクターキャップ・レジーム乗数
- position_sizing.py — 株数計算・ロット丸め・資金スケール

src/kabusys/research/
- factor_research.py — Momentum / Value / Volatility ファクター計算（DuckDB を使用）
- feature_exploration.py — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py — raw_news を OpenAI に送って ai_scores を生成
- regime_detector.py — マクロニュース + ETF MA200 乖離を合成して市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の簡易検証レポート出力ツール

その他
-----
- データファイルのデフォルトパスは Settings に定義されています（data/*.duckdb, data/*.db, data/kill.flag など）。
- ユニットテスト・CI 用に .env の自動読み込みを抑止する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

トラブルシューティング
---------------------
- DB が見つからない／開けない（Streamlit 等）:
  - MonitoringEngine を先に起動して monitoring DB を作成してください。
- OpenAI キー未設定:
  - OpenAI 関連関数は api_key 引数か OPENAI_API_KEY 環境変数が必須です。設定がないと ValueError になります。
- psutil による優先度設定失敗:
  - パーミッションやプラットフォームの制約で例外が出ることがありますが、コードはこれを警告してスキップします。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報や貢献ルールは該当ファイル（LICENSE / CONTRIBUTING）を参照してください（プロジェクトルートにあるはずのファイルを確認してください）。

以上が主要な利用説明です。詳細実装や追加のコマンドはソースコード内の docstring・コメントを参照してください。必要であれば README の英語版や具体的な起動スクリプトの systemd / Docker 化などの追加ドキュメント作成も対応します。