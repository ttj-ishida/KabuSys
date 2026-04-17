# KabuSys

日本株向け自動売買プラットフォーム（モジュール群）。本リポジトリは取引エンジン、監視、リサーチ、AI 補助（ニュース NLP / レジーム検出）、ポートフォリオ構築ユーティリティなどを含む小規模な自動売買フレームワークです。

以下はコードベースから自動生成した README です。運用・拡張の際の参照にしてください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントをモジュール化したライブラリ兼実行環境です。主な機能は以下の通りです：

- ExecutionEngine（発注ロジック、リスク管理、リコンシリエーション）
- Monitoring（システム状態・注文の監視、アラート、kill switch）
- Research（ファクター計算、特徴量探索）
- AI（ニュースセンチメントによるスコアリング、マーケットレジーム判定）
- Portfolio（候補選定、重み付け、ポジションサイズ計算）
- ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成）

設計方針としては、
- DuckDB / SQLite を中心としたオンプレミス DB 参照
- 外部 API（ブローカー / OpenAI など）呼び出しは明示的に分離
- テストやオフライン検証が可能な純粋関数群を多数提供
- 自動化運用を想定したフラグファイル（stop/kill）による制御

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカークライアント切替（paper_trading 環境では Mock を利用）
  - リコンシリエーション（再起動時の注文同期）
  - 注文状態管理（OrderManager / OrderRepository）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化
  - LINE によるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止制御（KillSwitch）
  - Streamlit ダッシュボード（簡易 UI）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - ニュースを OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存（news_nlp）
  - ETF とマクロニュースを組み合わせた市場レジーム判定（regime_detector）

- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## 必要要件（例）

以下は主な Python パッケージ（バージョンは適宜指定してください）：

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボードを使う場合)
- openai (AI 機能を利用する場合)

requirements.txt があればそれを使用するのが良いですが、存在しない場合は手動でインストールしてください。

例：
pip install duckdb psutil requests streamlit openai

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
   - （requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて .env.local）を作成できます。
   - 自動ロードはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

代表的な環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN=<...>
- KABU_API_PASSWORD=<...>
- OPENAI_API_KEY=<...>  (AI 機能を利用する場合)
- KABUSYS_ENV=development | paper_trading | live
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=<...> (通知利用時)
- LINE_USER_ID=<...>

サンプル .env（例）
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb

5. data ディレクトリを作成（PID/flag ファイルや DB を格納する想定）
   - mkdir -p data

注: DB スキーマ（監視テーブル等）は起動スクリプトが自動で初期化します（monitoring_db.init_monitoring_db を使用）。

---

## 使い方（実行例）

各スクリプトの起動方法と主要オプション。

1. ExecutionEngine を起動する
   - 通常（本番/開発）:
     KABUSYS_ENV=development python -m kabusys.run_execution
   - Paper Trading（外部ブローカーに接続せずモックを利用する）:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離します。

   動作:
   - 起動時にプロセス優先度を "high" に設定しようとします（psutil が権限により失敗する場合は警告ログ）。
   - 停止は data/stop_requested.flag の検出、または kill.flag による外部制御によって行われます。

2. Monitoring を起動する
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60）。
     例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path（Settings.sqlite_path）を参照してログ保存します。
   - 監視は SystemMonitor / TradeMonitor / RiskMonitor を用いて定期的にチェックし、MonitoringDB にログを保存します。

3. Streamlit ダッシュボード
   - 起動方法（デフォルト DB は data/monitoring.db）:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で監視 DB を表示します。MonitoringEngine を先に動かしてログを蓄積してください。

4. Paper Trading 検証レポート
   - コマンド:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     --db PATH で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。
   - レポートは稼働率・注文成功率・送信率・レイテンシなどを集計し、PASS/FAIL を判定します。

5. AI 機能（ニューススコア / レジーム判定）
   - プログラムから呼び出す:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
   - API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用します。
   - news_nlp.score_news は raw_news / news_symbols テーブルを参照し ai_scores に書き込みます。
   - 失敗時はフェイルセーフ（ゼロフォールバック）で継続する設計です。

6. 停止・強制停止
   - ExecutionEngine を外部から停止させたい場合は `data/kill.flag` を書き込みます（KillSwitch が検出して動作を停止）。
   - run_* スクリプトはまた `data/stop_requested.flag` の存在を確認して安全にシャットダウンします。
   - kill.flag は KillSwitch クラスで idempotent に書き込まれます。clear() で削除可能。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ループの間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH など監視用ファイルパス

Settings クラス（src/kabusys/config.py）を参照すると全設定項目が確認できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — 環境変数読み込み・Settings 管理
- run_execution.py — ExecutionEngine の起動スクリプト
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py — 発注管理（OrderManager）
- reconciler.py — 再起動時のリコンシリエーション
- その他：broker_api / broker_factory / execution_engine / order_repository 等（発注/ブローカー関連）

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ初期化と永続化 API（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度チェック
- trade_monitor.py — 注文滞留・約定異常検出
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 管理
- alert_manager.py — LINE push 通知
- monitoring_engine.py — 各モニタを束ねるランナー
- streamlit_dashboard.py — 可視化ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み付け
- position_sizing.py — 株数/配分計算
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
- regime_detector.py — ETF MA + マクロセンチメントでレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポートを生成する CLI スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意点 / 実装上のポイント

- 監視（run_monitoring）は MONITOR_POLL_INTERVAL に従ってループします。値は環境変数で上書き可。1 未満や不正値はデフォルト（60 秒）にフォールバックします。
- run_monitoring は KABUSYS_ENV に依らず Settings.sqlite_path（本番パス）を使用して監視ログを記録します。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（分離された DB）を使用し、MockBroker を使って発注をシミュレートします。
- OpenAI 等の外部 API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キーやネットワーク状態に依存するため運用時の監視が必要です。
- PID / flag ファイルは data 以下に作成されます（Settings でパス変更可能）。stop_requested.flag / kill.flag の扱いに注意してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）は外部データ投入が前提です。research / ai モジュールはこれらのテーブルを参照します。

---

## 開発・拡張時のヒント

- DB スキーマの初期化やマイグレーションは monitoring_db.init_monitoring_db に実装されています。必要な箇所で呼び出しておくと安全です。
- テスト時に環境変数自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はユニットテストで patch できるように分離されているので、モック化してテストしやすく設計されています。
- ポートフォリオ構築やポジションサイズ計算は純粋関数群として実装されており、DB 参照なしで単体テストが容易です。

---

必要に応じて README に追記します（例: requirements.txt の完全リスト、デプロイ手順、CI 設定、DB の初期データ投入スクリプトなど）。どの情報を優先して追加しますか？