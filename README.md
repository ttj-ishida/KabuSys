# KabuSys

日本株向け自動売買・リサーチ基盤の一部を切り出したコードベースです。ポートフォリオ構築、ポジションサイジング、発注管理、監視（Monitoring）やPaper Trading検証、ニュースNLP / レジーム判定などのユーティリティを含みます。

主に以下の用途を想定しています。
- 日次のファクター計算・研究（DuckDBをデータ層に使用）
- 発注エンジン（ExecutionEngine）とその復旧ロジック
- 監視エンジン（MonitoringEngine）による稼働・注文・リスク監視
- Paper Trading用検証レポート生成
- ニュースに対するLLMベースのセンチメント評価（OpenAI利用）

サンプル起動スクリプトや監視ダッシュボード用 Streamlit アプリも含まれます。

---

## 主な機能（抜粋）

- 設定管理
  - 環境変数および .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml で検出）
  - 実行環境区別（development / paper_trading / live）
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: 条件により ExecutionEngine 停止用のフラグファイルを書き込む
  - AlertManager: LINE Push API を使った通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用モードで表示可能）
- 実行（execution）
  - ExecutionEngine（起動スクリプト経由）
  - BrokerClientFactory により paper_trading 時はモックブローカーを使用（DB分離）
  - リコンシリエーション（Reconciler）でクラッシュ後の復旧対応
  - OrderManager / OrderRepository による注文状態遷移と永続化
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額・スコア加重、セクター制限、レジーム乗数、ポジションサイジング（ロット丸め・合計キャッシュによるスケーリング）
- リサーチ（research）
  - factor（モメンタム / ボラティリティ / バリュー）計算（DuckDBを使って prices_daily / raw_financials を参照）
  - 将来リターン・IC・統計サマリなどのユーティリティ
- AI関連（ai）
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集約と ai_scores 書き込み
  - regime_detector: MA200乖離 + マクロセンチメントで市場レジームを判定して DB に書き込み
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要環境・依存

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク接続（OpenAI API / LINE API 利用時）

requirements.txt があればそこからインストールしてください。なければ以下のように仮想環境を作ってインストールします。

例:
- 仮想環境作成 & 有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（概要）

1. リポジトリをチェックアウトし、プロジェクトルートへ移動
2. Python 3.10+ の仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env を用意（プロジェクトルートに配置）
   - Settings は自動で .env を読み込みます（.env.local は上書き）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. 初期データディレクトリを作成（例: data/）
6. 必要に応じて DuckDB / SQLite の初期テーブルを準備（monitoring スキーマは自動作成されます）

代表的な環境変数（最低限の例）
- JQUANTS_REFRESH_TOKEN=（J-Quants API トークン）
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- OPENAI_API_KEY=（OpenAI API キー、ai 機能を使う場合）
- KABUSYS_ENV=development | paper_trading | live
- PAPER_FILL_MODE=instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN=（任意、アラート送信用）
- LINE_USER_ID=（任意、アラート送信用）
- MONITOR_POLL_INTERVAL=（監視ループの秒間隔、デフォルト60）
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=1 または 0（起動時に kill.flag を自動でクリアするか）

.sample .env の例（プロジェクトルートに .env を作る）
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-xxxx...
- KABU_API_PASSWORD=your_pass
- JQUANTS_REFRESH_TOKEN=...
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要スクリプト）

各スクリプトはパッケージ内からモジュール実行できます（python -m ...）。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は Settings の sqlite_path（本番用）を使います：KABUSYS_ENV にかかわらず monitoring DB は sqlite_path を参照します。
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil による設定。権限によっては失敗しても継続）。
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。本番 DB と分離されます。
    - 起動時にプロセス優先度を "high" に設定します。
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - read-only モードで SQLite DB を開きます。MonitoringEngine がデータを書き込んでいることを前提とします。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 引数 api_key を渡すか、OPENAI_API_KEY 環境変数を設定してください。

注意点:
- ExecutionEngine の起動やブローカー接続には各種シークレット（KABU_API_PASSWORD など）が必要です。
- Paper Trading を利用する際は KABUSYS_ENV=paper_trading を設定してください。Paper Trading 専用の SQLite に記録され、本番 DB と分離されます。
- Kill Switch は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を作成して ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START を有効にすることで起動時の自動クリアができます。

---

## 主要な設定・挙動まとめ

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）から .env を読み込み、.env.local を上書き読み込みします。ただし OS 環境変数は保護されます（上書きされない）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 環境区分:
  - KABUSYS_ENV の有効値: development / paper_trading / live
- Paper Trading:
  - SETTINGS.is_paper が True のとき、run_execution は PAPER_TRADING_SQLITE_PATH を使用して DB を分離。
  - PAPER_FILL_MODE でモックの成行/部分約定等の挙動を制御（instant / partial / never / reject）
- 監視DB:
  - init_monitoring_db() はテーブルとインデックスを冪等に作成します（起動時に自動で呼ばれる箇所あり）。
  - monitoring の一部は常に sqlite_path（本番）を参照します。Paper Trading と分離したい用途（実際の注文ログなど）は PAPER_TRADING_SQLITE_PATH を使用してください。
- プロセス優先度 / CPU affinity:
  - set_process_priority() / set_cpu_affinity() が用意されています（psutil を利用）。プラットフォーム差分を吸収する実装です。権限により失敗する可能性がありますが、その場合は警告を出して継続します。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings
- run_monitoring.py — SystemMonitor ポーリングループ起動
- run_execution.py — ExecutionEngine 起動
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止指令
  - alert_manager.py — LINE API通知ラッパ
  - monitoring_engine.py — 各モニタの統合
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 発注ワークフロー / 状態遷移
  - reconciler.py — 起動時リコンシリエーション
  - (その他: broker_factory, execution_engine, order_repository, order_record 等)
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数算出（ロット丸め、スケーリング）
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- data/  （実行時に生成される想定）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db

（実際のファイル一覧は上記に含まれるモジュールソースを参照してください）

---

## 開発上の注意 / 実運用での留意点

- LLM 呼び出し（OpenAI）はネットワーク依存であり、API エラーやレート制限対応（リトライ、バックオフ）が組み込まれていますが、実運用ではコストと失敗時の挙動をよく確認してください。
- 監視・停止機構（KillSwitch 等）は自動停止を行います。kill.flag の運用ルール（誰がいつクリアするか）を明確にしてください。KILL_FLAG_CLEAR_ON_START による自動クリアは運用ポリシーに沿って設定してください。
- DB マイグレーションは簡易的に実装されています。スキーマ変更時は注意深く確認してください。
- 実ブローカー接続部分は外部と連携するため、シークレット管理・テスト（モック）を厳密に行ってください。

---

必要であれば、README にサンプル .env.example、より詳細な起動手順、よくあるエラーと対処（トラブルシューティング）、テスト方法などを追記します。どの情報を追加しますか？