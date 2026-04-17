# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。  
本READMEではプロジェクト概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買・分析・監視を行うためのモジュール群です。主要な責務は次の通りです。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 取引監視・システム監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ決定）
- 研究用ファクター計算（Momentum, Volatility, Value 等）
- ニュースの自然言語処理によるセンチメント評価（OpenAI を利用）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

設計方針として、DB はローカルの SQLite / DuckDB を使用し、Paper Trading（検証用）と Live（本番）の分離、外部 API 呼び出しの失敗に対するフェイルセーフ、ルックアヘッドバイアス回避（時間参照の扱い）等に配慮されています。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（BrokerClientFactory）により本番/モックを切替可能
  - OrderManager による注文状態遷移管理（重複検知・キャンセル制御等）
  - Reconciler による再起動後の自動リコンシリエーション（注文・ポジション照合）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス・データ鮮度監視
  - TradeMonitor: 注文の滞留・約定価格異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: リスク条件で停止フラグ（data/kill.flag）を書き込み、ExecutionEngine を停止
  - AlertManager: LINE Push による一方向アラート送信（クールダウン機能）
  - Streamlit ダッシュボード（監視状況の可視化）
- Portfolio
  - 候補選定（スコア降順）、等配分 / スコア加重、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、ファクター統計サマリ
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価して ai_scores に記録（score_news）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（score_regime）
- ユーティリティ
  - 環境変数自動読み込み（.env / .env.local）、Settings クラスによる一元管理
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 監視ログ用の SQLite スキーマ初期化ユーティリティ

---

## 必要条件（推奨）

- Python 3.10 以上（型ヒントに「|」を利用）
- OS: Linux / macOS / Windows（機能の一部は OS に依存）
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- （任意）仮想環境の使用を推奨

requirements.txt がない場合は上記パッケージを pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

Settings クラスで管理されます。必須 / 任意の重要な変数を示します。

必須（実行環境による）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード（Settings.kabu_api_password）

AI 機能利用時:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使う
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH など

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` を自動で読み込みます。  
- 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. data ディレクトリを作成（PID / フラグ / DB を格納）
   ```
   mkdir -p data
   ```

5. 環境変数を設定（.env を作成するか、環境に応じて直接設定）
   - 必須値（上記参照）を .env に記述
   - Paper Trading の場合は KABUSYS_ENV=paper_trading を設定すると paper 用 DB を使用します

6. DB の初期化
   - 監視用 DB は run_monitoring / run_execution 起動時に自動で初期化されます（init_monitoring_db を利用）

---

## 使い方（主要コマンド）

- 監視ループを起動（SystemMonitor ベースのポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 本スクリプトは Settings に基づき「監視用 DB」を初期化し、プロセス優先度を上げます
  - stop フラグファイル: data/stop_requested.flag（存在するとループを終了）

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db 等）へ記録
  - 起動前に data/stop_requested.flag が存在する場合は起動せずに終了します
  - 実行中に data/stop_requested.flag が作成されると安全に停止します
  - 実行はスレッドで行われ、data/execution.pid を PID ファイルとして扱います

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視用 SQLite を読み取り専用で開きます（DB が存在しない場合はエラー表示）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。--db でパス上書き可能
  - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL を判定

- AI（ニューススコア計算 / レジーム判定）: Python API 経由で呼ぶ
  - news のスコア付け:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  ※ いずれも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）

---

## 停止・制御関連

- 停止フラグ（外部から安全停止を指示する）
  - data/stop_requested.flag: run_monitoring / run_execution がループの中でチェックする停止指示フラグ
  - data/kill.flag: KillSwitch が作成するフラグで ExecutionEngine を停止させるために利用
- PID ファイル
  - data/execution.pid（デフォルト）: 実行エンジンの PID を記録
  - SystemMonitor は PID ファイルの stale 判定（PID が存在しない場合は削除）を行います

---

## 主要ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化 & MonitoringDB（読み書き）
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
    - (Broker / Engine 等の実装が存在)
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
  - data/                       — 実行時に使用する DB / フラグ / PID (gitignore で管理推奨)
  - tools/
    - paper_verification_report.py

（ファイル全体構成は src/kabusys 以下を参照してください）

---

## 実装上の注意・設計メモ

- Settings クラスは .env 自動読み込みを行いますが、OS 環境変数は保護されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading モードでは本番 DB と完全に分離された専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用する設計です。
- AI 周りの呼び出しはリトライ、JSON 検証、スコアクリップ等の堅牢化処理を実装しています。API 失敗時はフェイルセーフ（ゼロやスキップ）で続行する設計です。
- MonitoringDB はマイグレーション処理（欠損カラムの追加）を含み、初回起動時の互換性を保つ実装です。
- process_priority/set_cpu_affinity は権限や OS によって失敗する場合があるためログのみ出力してスキップする実装になっています。

---

## 参考コマンドまとめ

- 監視開始:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- エンジン開始（Paper Trading モード）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に追記する項目（例）：
- 詳細な環境変数一覧（全キー）
- requirements.txt / Dockerfile サンプル
- 実行例・ログの読み方
- テストと CI 設定

追加で盛り込みたい情報があれば教えてください。