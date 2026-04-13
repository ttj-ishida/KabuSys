KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買および研究用ツール群です。本リポジトリには以下の主要な機能群が含まれます。

- 実行コンポーネント（ExecutionEngine）: 注文発行・リスク管理・リコンシリエーション
- 監視コンポーネント（MonitoringEngine）: システム状態、注文滞留、ドローダウン監視・アラート
- ポートフォリオ構築ユーティリティ: 候補選定・重量算出・ポジションサイズ計算・セクター制限
- 研究モジュール: ファクター計算（モメンタム／ボラティリティ／バリュー）、特徴量解析
- AI 支援モジュール: ニュースセンチメント評価（OpenAI API を利用）
- 運用ツール: Paper Trading 検証レポート、Streamlit ダッシュボード など

主な特徴
--------
- 環境変数（.env）ベースの設定（Settings）
- 実運用と paper_trading を分離する DB 設計（paper_trading 用 SQLite）
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials）
- LINE への通知（AlertManager）
- kill.flag による外部停止シグナル（KillSwitch）
- 冪等な DB 初期化 / マイグレーション処理（monitoring_db.init_monitoring_db）
- OpenAI を使ったニュース NLP（バッチ・リトライ・レスポンス検証を実装）

前提条件
--------
- Python 3.9+
- DuckDB（Python パッケージ duckdb）
- sqlite3 (標準ライブラリ)
- psutil
- requests
- openai (OpenAI の Python SDK) — AI 機能を使う場合
- streamlit — ダッシュボードを使う場合

簡単なセットアップ例
-------------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt が無い場合は個別に）:
   pip install duckdb psutil requests openai streamlit
4. 環境変数を設定:
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
     - KABU_API_PASSWORD: kabuステーション API 用（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視（monitoring）用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（空なら通知は行わない）
     - PID_FILE_PATH / KILL_FLAG_PATH: 実行 pid ファイル・kill flag のパス（デフォルト: data/execution.pid, data/kill.flag）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

注: Settings モジュール内で既定値や妥当性検査が実装されています。必須項目は _require によって未設定時に ValueError が投げられます。

使い方
------

1) 監視ループ (Monitoring)
- スクリプト: src/kabusys/run_monitoring.py
- 動作:
  - プロセス優先度を "high" に設定（可能な場合）
  - monitoring 用 SQLite（Settings.sqlite_path）と DuckDB に接続
  - SystemMonitor を用いたポーリングループを開始（MONITOR_POLL_INTERVAL で間隔を指定可能）
  - 監視は実行環境にかかわらず production の sqlite_path を使用する点に注意（意図的な設計）
- 実行例:
  KABUSYS_ENV=development python -m kabusys.run_monitoring
  （MONITOR_POLL_INTERVAL を上書きする場合: MONITOR_POLL_INTERVAL=30 ...）

2) 実行エンジン (ExecutionEngine)
- スクリプト: src/kabusys/run_execution.py
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に書き込む
  - リコンシリエーション、リスクマネージャ、OrderManager 等のコンポーネントを組み立ててセッションを実行
- 実行例:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3) Streamlit ダッシュボード
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動方法:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - monitoring DB を read-only で開いてダッシュボードを表示します
  - 監視データが無い場合は案内メッセージが出ます

4) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 使用例:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- 内容:
  - 指定期間の稼働率、注文成功率、送信率、レイテンシなどを集計して PASS/FAIL 判定を出力します
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）

5) AI モジュール（ニュース NLP / レジーム判定）
- 主要関数:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 備考:
  - OpenAI API キー（OPENAI_API_KEY または引数 api_key）が必須
  - DuckDB 接続（prices_daily/raw_news/ai_scores 等のテーブル）を渡して呼び出します
  - レスポンスの検証・再試行ロジック・スコアのクリッピングなど安全機構を内蔵しています

設定（環境変数）
----------------
主なキーと説明（デフォルトを含む）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（空なら送信スキップ）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: "1" で ExecutionEngine 起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動ロードを無効化

注意点・運用メモ
----------------
- monitoring は Settings.env にかかわらず monitoring 用 sqlite_path（Settings.sqlite_path）を使用します。paper_trading と監視 DB は分離されている点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading の時のみ paper_trading 用 sqlite を使用します（本番 DB とは分離）。
- kill.flag (Settings.kill_flag_path) は KillSwitch により書き込まれ、ExecutionEngine はこのフラグの存在を検知して停止する想定です。Execution 起動時にフラグをクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- streamlit ダッシュボードは DB を read-only で開きます。監視プロセスが稼働中でない場合はメッセージが表示されます。
- AI 機能は外部 API を使うためネットワークや料金に注意してください。API 呼び出しはリトライとバックオフ、レスポンス検証を行いますが、失敗時は安全側（スコア 0.0、処理スキップ等）にフォールバックします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

- monitoring/
  - __init__.py
  - monitoring_db.py             — SQLite による監視ログ永続化層
  - system_monitor.py            — CPU/Memory/Disk / データ鮮度 / PID チェック
  - trade_monitor.py             — 注文滞留・約定異常チェック
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - alert_manager.py             — LINE 通知ラッパ
  - monitoring_engine.py         — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py       — Streamlit UI

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - execution_engine.py
  - broker_factory.py
  - ...（注文管理・ブローカー抽象など）

- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 株数算出・集約上限・lot 単位丸め
  - risk_adjustment.py           — セクター上限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py           — momentum/value/volatility 計算（DuckDB）
  - feature_exploration.py       — 将来リターン、IC、統計要約
  - __init__.py

- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI）処理
  - regime_detector.py           — 市場レジーム判定（ETF + マクロセンチメント）
  - __init__.py

- data/
  - pipeline.py                  — （prices_daily などの入出力ユーティリティを含む想定）
  - stats.py                     — zscore_normalize 等の統計ユーティリティ

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
  - __init__.py

ドキュメント / 参考
------------------
ソース内の docstring に各モジュールの仕様・設計方針・制約が詳述されています。特に以下ファイルは運用時に役立つ説明を含みます。

- src/kabusys/config.py
- src/kabusys/monitoring/monitoring_db.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/portfolio/*

貢献 / 開発
-----------
- テスト: 現状テストスクリプトは含まれていませんが、個々の純粋関数（portfolio, research など）はユニットテストが書きやすく設計されています。
- .env.example をベースに環境変数を準備し、まずは KABUSYS_ENV=paper_trading で動作確認することを推奨します。
- OpenAI 呼び出し部分は外部依存が強いので、ユニットテスト時は関数のモック（unittest.mock.patch）を利用してください（ソース内にもその旨のコメントがあります）。

最後に
------
この README はコードベース内の docstring と実装に基づき作成しています。実運用の際は .env（もしくは環境変数）で必須値を正しく設定し、まず paper_trading モードで安全に動作確認を行ってください。質問や補足が必要であれば、どの部分について詳しく知りたいか教えてください。