# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。  
このリポジトリには、注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を用いたニュースセンチメント評価などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 注文発行・状態管理・再同期（Reconciler）を行う Execution モジュール。
- システム状態（CPU/メモリ/ディスク・データ鮮度）と取引状態（滞留注文・約定異常）を監視する Monitoring モジュール。LINE 通知や kill flag によるエンジン停止制御をサポート。
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）。
- DuckDB を用いた研究用ファクター計算・将来リターン、IC 計算などの Research モジュール。
- OpenAI（gpt-4o-mini）を用いたニュース NLP によるセンチメントスコアリング、およびその結果を使った市場レジーム判定モジュール（AI 関連は API キー必須）。
- 付帯ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、各種ツールスクリプト）

設計上のポイント:
- 計算用関数群（portfolio / research）は純粋関数で DB に副作用を与えない設計が多い。
- Monitoring は実行環境に関わらず本番用の sqlite_path を使ってログを記録する設計（監視の永続化）。
- Paper trading（KABUSYS_ENV=paper_trading）時は MockBrokerClient を用い、DB は paper_trading 専用ファイルで本番と分離。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 同期（OrderManager）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - RiskManager / OrderRepository 等の実行系コンポーネント

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク / プロセス健全性 / データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション数監視
  - KillSwitch: 条件による ExecutionEngine 停止（data/kill.flag）
  - AlertManager: LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用可視化）

- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重、リスクベース配分
  - セクターキャップ適用、レジーム乗数

- Research
  - ファクター計算（momentum, volatility, value）
  - 特徴量解析（forward returns, IC, factor summary）

- AI
  - ニュースセンチメント（OpenAI）で ai_scores に書き込み
  - マクロニュース + ma200 を使った市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
  - Streamlit ダッシュボード起動用スクリプト

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 推奨: Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（requirements.txt がある場合）
   ```
   pip install -r requirements.txt
   ```
   主要依存例:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   （requirements.txt がない場合は上のパッケージを個別にインストールしてください）

4. データディレクトリを準備
   ```
   mkdir -p data
   ```
   ※ SQLite / DuckDB ファイルはデフォルトで data/ 配下に作成されます。

5. 環境変数を設定
   - .env / .env.local に必要なキーを記述するか、OS 環境変数で設定してください。
   - 自動読み込みはデフォルトで有効。無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主要環境変数（例・必須等）:
   - JQUANTS_REFRESH_TOKEN — （必須）J-Quants API トークン
   - KABU_API_PASSWORD — （必須）kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI を使う場合に必須
   - KABUSYS_ENV — 認められる値: development, paper_trading, live（デフォルト: development）
   - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — Monitoring 用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

   参考: .env.example をプロジェクトルートで作成してコピーして使ってください。

---

## 使い方

基本的な起動コマンド例（プロジェクトルートから実行）:

- 監視ループを起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - stop 指示はプロジェクトルートの `data/stop_requested.flag` を作成すると次のループで終了します。

- ExecutionEngine を起動（注文実行系）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 実行中の停止は `data/stop_requested.flag` を作成して検知させるか、外部から kill してください。ExecutionEngine は `data/execution.pid` を使用してプロセス健全性を監視します。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で明示的に DB パス（SQLite）を指定できます。指定なければ環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を参照します。

- Streamlit ダッシュボード（監視 UI）を起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI モジュール（ニューススコアリング / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キー（引数または OPENAI_API_KEY 環境変数）を使用します。

- その他ユーティリティ
  - プロセス優先度や CPU affinity の設定は kabusys.utils.process_priority.set_process_priority / set_cpu_affinity を利用。

停止・フラグ関連:
- `data/stop_requested.flag` — run_monitoring / run_execution が監視している停止フラグ（任意のファイルを置くことで停止シグナル）。
- `data/kill.flag` — KillSwitch が書き込むファイル。ExecutionEngine 停止を示すために使用される（KillSwitch.evaluate が条件を満たしたときに書き込まれる）。
- `data/execution.pid` — 実行エンジンの PID を格納するファイル（存在しない・古い PID は stale と判断され削除される）。

ログ:
- 各スクリプトは標準の logging を使用（LOG_LEVEL 環境変数で制御）。実行時に INFO レベルで起動ログが出力されます。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下にモジュール群を配置します。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite schema / 永続化層（MonitoringDB）
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
    - order_repository.py
    - order_record.py
    - execution_engine.py         — （Engine 実装の中心。ファイルの一部未表示）
    - broker_factory.py
    - broker_api.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースからのセンチメントスコア取得
    - regime_detector.py          — マクロ + ma200 によるレジーム判定
  - data/                         — 実行時に使用するデータ / フラグファイル（ローカル作成）
    - monitoring.db (sqlite, デフォルト)
    - paper_trading.db (sqlite, paper_trading 用)
    - kabusys.duckdb (DuckDB データベース)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading レポート生成

---

## 重要な設計上の注意点 / 運用メモ

- .env の自動ロード
  - プロジェクトルートを .git または pyproject.toml を基準に検出して `.env` / `.env.local` を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env 上書き（ただし OS 環境変数は保護）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、Execution エンジンは paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番の monitoring.db とは分離されます。

- OpenAI / 外部 API の失敗耐性
  - news_nlp / regime_detector は API 呼び出し失敗時にフェイルセーフ（スコア 0.0 など）で継続する実装が入っています。ただし API キーが未設定の場合は呼び出し元で例外になります。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等（存在確認して CREATE IF NOT EXISTS）で、既存テーブルに列がない場合は add column による簡易マイグレーションも行います。

---

## よくある操作例

- 監視を一時停止しているプロセスを終了させたい
  - プロジェクトルートに `data/stop_requested.flag` を作成すると run_monitoring / run_execution は次のループで安全に終了します。

- ExecutionEngine に強制停止（KillSwitch）をトリガーしたい
  - 管理者として直接 `data/kill.flag` を書き込むのではなく、KillSwitch.evaluate により自動生成されるのを想定しています。手動で書きたい場合は reason を追記したファイルを作ることで同等の挙動になります。

---

## サポート / 開発時のヒント

- テスト時は Settings の自動 .env 読込を無効化するか、テスト専用の .env を用意してください。
- OpenAI 呼び出し部分はテスト容易性のため内部呼び出し関数（_call_openai_api 等）を patch してモックする設計になっています。
- DuckDB / SQLite のクエリはローカルの DB ファイルを参照するため、研究・検証時はデータを事前にロードしておく必要があります。

---

必要があれば、README に依存関係の pin（requirements.txt の生成）、具体的な .env.example のテンプレート、実行フロー図、API インターフェースの詳細（Broker API の仕様）などを追記できます。どの情報を優先して追加しましょうか？