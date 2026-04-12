# KabuSys

日本株自動売買システムのパイロット実装（ライブラリ群 & 実行スクリプト）

このリポジトリは以下の主要コンポーネントで構成されています：
- 発注・実行エンジン（ExecutionEngine / OrderManager / BrokerClientFactory 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメントによるスコアリング、レジーム判定）
- ユーティリティ（プロセス優先度設定、設定管理）
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

以下は、このコードベースの概要、セットアップ手順、使い方、ディレクトリ構成などのドキュメントです。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの構成要素をモジュール化した実装です。  
目的は以下のとおりです：

- 発注フローの管理と実行（実ブローカーまたはモックブローカーでの Paper Trading 対応）
- 実行中の監視（プロセス生存、システムリソース、注文滞留、約定異常、ドローダウン等）
- ポートフォリオ構築（シグナルに基づく候補選定、重み付け、ポジションサイズ計算）
- 研究用途（DuckDB を使ったファクター計算・IC 計算など）
- ニュースを用いた AI ベースのセンチメントスコアリングとマーケットレジーム判定
- 運用用ツール（Paper Trading 検証レポート、監視ダッシュボード）

設計方針として、「外部実口座や本番 DB への不要なアクセスを避ける」「ルックアヘッドバイアス対策」「フォールバックを備えたフェイルセーフ」等が反映されています。

---

## 主な機能一覧

- Execution
  - OrderManager、OrderRepository、ExecutionEngine による発注・状態管理
  - BrokerClientFactory により KABUSYS_ENV に応じた本番/モックブローカー選択（paper_trading モードをサポート）
  - Reconciler による再起動時の自動同期（OrderSent のリコンシリエーション、ポジション差分検出）

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor：滞留注文（stale order）、約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新・リスクログ出力
  - KillSwitch：条件に応じてフラグファイル（data/kill.flag）を作成し ExecutionEngine に停止シグナルを送信
  - AlertManager：LINE プッシュ通知によるアラート送信（クールダウン管理）

- Portfolio
  - 候補選定、等配分/スコア配分、セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元株丸め・aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI
  - news_nlp.score_news：OpenAI（gpt-4o-mini）でニュースをセンチメント評価し ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定し保存

- Tools
  - tools.paper_verification_report：Paper Trading DB を解析して運用検証レポートを生成
  - monitoring/streamlit_dashboard.py：監視情報を可視化する Streamlit ダッシュボード

---

## 環境変数 / 設定（主要）

設定管理は `kabusys.config.Settings` を通して行います。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（必要に応じて無効化可）。

主要な環境変数（デフォルト含む）：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- SQLITE_PATH: 監視用 SQLite（production 用）デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境時に使用）デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper ブローカーの fill 動作（instant|partial|never|reject）デフォルト: instant
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル デフォルト: data/execution.pid
- KILL_FLAG_PATH: Kill Switch 用 flag ファイル デフォルト: data/kill.flag
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視の閾値（%）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証に必要（未設定時は Settings がエラーを投げる）

自動 .env 読み込みを無効化する場合：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

監視ループ間隔:
- MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（デフォルト 60）。無効な値（0 以下など）はデフォルトにフォールバックします。

---

## 必要な依存パッケージ（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit

（requirements.txt はプロジェクトに含まれていない場合があるため、上記を pip でインストールしてください）

例:
pip install duckdb psutil openai requests streamlit

開発時は仮想環境の作成を推奨します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または
   - pip install duckdb psutil openai requests streamlit
4. プロジェクトルートに `.env` を作成（` .env.example` を参考に必要な環境変数を設定）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（環境により不要）
   - OpenAI を使う場合は OPENAI_API_KEY を設定
5. DuckDB / SQLite のデータディレクトリを作成
   - mkdir -p data

---

## 起動・使い方

以下は典型的な起動例です。各コマンドはプロジェクトルートで実行してください。

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - デフォルト: 本番 monitoring DB (Settings.sqlite_path) を使う
  - 実行:
    - python -m kabusys.run_monitoring
  - 環境変数例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - Paper Trading モード（モックブローカー & 専用 DB）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番 / development モード:
    - python -m kabusys.run_execution
  - 注意: ExecutionEngine は起動時に PID ファイルを作成します。kill.flag が存在すると停止する設計があるため、Settings.kill_flag_clear_on_start の挙動に注意してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH を設定

- Streamlit ダッシュボード
  - 起動方法（既に monitoring DB が存在していて read-only 開く場合）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール（スクリプト呼び出しが無いものは Python から直接呼ぶ）
  - 例: ニューススコア付けを実行する（DuckDB 接続を渡す）
    - Python REPL またはスクリプト内:
      from openai import OpenAI
      import duckdb
      from datetime import date
      conn = duckdb.connect("data/kabusys.duckdb")
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date=date(2026,4,10), api_key="sk-xxxx")
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,10), api_key="sk-xxxx")

- プロセス優先度設定ユーティリティ
  - コード経由で set_process_priority("high") を使用（実行スクリプト内で既に呼ばれています）
  - 注意: 権限不足や未対応 OS の場合は警告を出してスキップします

---

## 運用上の注意点

- Paper Trading（KABUSYS_ENV=paper_trading）時は paper_sqlite_path（デフォルト data/paper_trading.db）に完全に分離して記録されます。本番 SQLite（monitoring.db）へは書き込みしません。
- Monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番パス）を使用する設計です。監視と実行の DB を分離したい場合は環境変数を調整してください。
- KillSwitch は条件に応じて kill.flag を作成します。ExecutionEngine はこのフラグを見て停止する想定なのでファイルを削除する際は注意してください（KillSwitch.clear() を利用可）。
- OpenAI の呼び出しは外部 API を利用するため API キーとコストに注意してください。API の失敗は適切にフェイルバック（スコア 0.0 等）する実装が含まれますが、運用設計に注意してください。
- DuckDB への書き込み（ai_scores、market_regime 等）はトランザクションで行われるように設計されていますが、DuckDB のバージョン差異により executemany の挙動が異なるため注意が必要です（コード上に互換処理あり）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス（.env 自動読み込み、必須チェック）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードで MockBroker を使用）
  - utils/
    - process_priority.py：プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py：SQLite を使った監視ログ永続化（テーブル定義、CRUD）
    - system_monitor.py：CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py：滞留注文・約定異常の検出
    - risk_monitor.py：ドローダウン・ポジション上限監視
    - kill_switch.py：flag ファイルによる停止シグナル管理
    - alert_manager.py：LINE プッシュ通知送信
    - monitoring_engine.py：複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py：Streamlit ダッシュボード
  - execution/
    - order_manager.py：OrderState 遷移を管理する OrderManager
    - order_repository.py：Order の SQLite 永続化（ファイルの一部がここに含まれている想定）
    - reconciler.py：再起動時のリコンシリエーション
    - broker_factory.py、broker_api.py（ブローカー関連インタフェース/実装） ※実装の一部は省略
  - portfolio/
    - portfolio_builder.py：候補選定・スコア順ソート
    - position_sizing.py：株数（単元）計算・リスク制限・スケールダウン
    - risk_adjustment.py：セクター制限・レジーム乗数
  - research/
    - factor_research.py：Momentum / Volatility / Value のファクター計算（DuckDB 使用）
    - feature_exploration.py：将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py：ニュースの LLM センチメント評価と ai_scores 書き込み
    - regime_detector.py：マクロニュース + ETF MA 乖離によるレジーム判定
  - tools/
    - paper_verification_report.py：Paper Trading DB を解析して検証レポートを印字
  - data/
    - （実行時に生成される SQLite / DuckDB ファイルを想定。デフォルトパス: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）

---

## 開発・拡張のヒント

- DuckDB を用いた計算モジュール（research/*.py）は外部 API を使わずにローカルデータのみ参照する設計です。ユニットテスト作成が容易です。
- AI 関連は API 呼び出し部分を小さな関数（_call_openai_api 等）に分離しているため、テスト時はモックで差し替え可能です（unittest.mock.patch 等）。
- monitoring/monitoring_db.py はスキーマの冪等性と簡単なマイグレーション処理（ALTER TABLE ADD COLUMN）を実装しています。スキーマ変更時はここを調整してください。

---

## 参考コマンド一覧

- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README はここまでです。必要であれば以下を追加できます：
- requirements.txt の具体例
- .env.example のテンプレート
- より詳細な API ドキュメント（各モジュールの public 関数 / クラスの使用例）
- 単体テストの実行方法・テストカバレッジ指針

どれを追加しますか？