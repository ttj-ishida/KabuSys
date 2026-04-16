# KabuSys

日本株自動売買システムのサブコンポーネント群。ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュースNLU／レジーム判定）等の機能を持つモジュール群です。

この README はリポジトリ内のコード（src/kabusys/*）に基づいて作成しています。

注意: 本文書はコードから読み取れる振る舞いをまとめたもので、運用上の安全ルール（実口座での利用など）は別途運用ドキュメントに従ってください。

## 概要

- ExecutionEngine: 発注実行の主要コンポーネント（Broker クライアント、OrderManager、RiskManager、Reconciler 等）。
- Monitoring: 実行プロセスや注文の状態、システム資源・データ鮮度をポーリングしてログ・アラート管理を行う。
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム調整などの純関数群。
- Research: DuckDB 上の価格・財務データからファクターを計算・解析するモジュール群。
- AI: ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定（MA200 + マクロセンチメント）。
- Tools: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード等のユーティリティ。

## 主な機能一覧

- 発注・状態管理（OrderManager / OrderRepository）
- 再起動リコンシリエーション（Reconciler）
- リスク制御（RiskManager、RiskMonitor、KillSwitch）
- システム監視（CPU/Memory/Disk、プロセス死活、データ鮮度）
- 注文監視（滞留注文、約定価格異常）
- 監視ログ永続化（SQLite、MonitoringDB）
- DuckDB ベースのファクター計算・リサーチ（momentum / volatility / value 等）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）、市場レジーム判定（ETF MA200 + LLM）
- Paper Trading 用 DB の分離（paper_trading 環境）
- Streamlit ダッシュボード（監視データの可視化）
- Paper Trading 検証レポート生成ツール

## 前提 / 依存

- Python 3.10+
- 必要パッケージ（一部）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- 標準ライブラリの sqlite3, threading, logging 等を使用

インストール例（venv 利用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # もし requirements.txt があれば
# 例:
pip install duckdb psutil openai requests streamlit
```

## 環境変数（主なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、MockBrokerClient が利用され、paper_trading 用 SQLite（data/paper_trading.db）を使用。
- SQLITE_PATH: 監視 SQLite DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等: 各 API / 通知用
- PAPER_FILL_MODE: paper_trading の約定挙動（"instant" | "partial" | "never" | "reject"、デフォルト: "instant"）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）。0以下・不正値はデフォルトにフォールバック。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化

.env ファイルはプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数が優先されます）。

## セットアップ手順（簡易）

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成し依存をインストール
3. 必要な環境変数を .env に設定（例は下記）
4. data/ ディレクトリを作成（必要に応じて）
5. DuckDB / SQLite の DB ファイルは初回起動で必要なテーブルを作成します（init_monitoring_db が自動で実行されます）

例 .env（最低限の例）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

## 実行方法（代表的なコマンド）

- 監視ループ起動（Monitoring）
  - モジュール実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 特記事項:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を調整できます（デフォルト: 60）。
    - run_monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（Settings.sqlite_path）を使用します。
    - 停止: プロセスに SIGINT（Ctrl+C）を送るか、リポジトリルートの data/stop_requested.flag を作成するとループが検知して終了します。

- 発注実行エンジン起動（Execution）
  - モジュール実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag があると起動をスキップします。
    - 起動中は PID を data/execution.pid に書きます。監視側は PID の有無でプロセス生存を判定します。
    - 停止は data/stop_requested.flag を作成することで実行エンジンに指示できます（run_execution の監視ループが検知して engine.stop() を呼びます）。

- Streamlit ダッシュボード（監視用）
  - 起動:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- AI（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定後、ライブラリ API を呼び出します（呼び出し例はコード中の public 関数参照）。
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行は DuckDB 接続を用意してこれら関数を呼び出します。API 呼び出しはリトライ・フェイルセーフの考慮がありますが、API キーは必須です。

## 停止 / キルロジック

- data/stop_requested.flag: run_monitoring / run_execution の起動ループが存在を検知すると安全に終了します。停止トリガーとして使えます。
- KillSwitch（監視側）: RiskMonitor 等の評価によって data/kill.flag を書き込み、ExecutionEngine 側で事前に用意した kill flag パスを参照して停止を促します（Settings.kill_flag_path）。
- PID ファイル: ExecutionEngine は data/execution.pid に PID を書きます。SystemMonitor はこれを参照してプロセス存否を確認します。PID が stale（存在しないプロセス ID）と判断された場合、ファイルを削除してリスクイベントを記録します。

## データファイルとデフォルトパス

- data/monitoring.db (SQLite) — 監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）
- data/paper_trading.db (SQLite) — paper_trading 用（分離）
- data/kabusys.duckdb (DuckDB) — 価格・財務・ニュース等の分析データ
- data/execution.pid — ExecutionEngine の PID（デフォルト）
- data/kill.flag — KillSwitch による停止理由の保存先（デフォルト）
- data/stop_requested.flag — 手動停止フラグ

（これらは Settings クラスのプロパティで上書き可能）

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定読み込みロジック（.env 自動ロード機能）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・CRUD ラッパ）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py — 滞留注文・約定価格異常のチェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 確認
  - alert_manager.py — LINE への Push 通知ラッパ
  - monitoring_engine.py — モニター統括（ポーリング・アラート送信）
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, risk_manager.py, ...（発注・再同期・リスク管理系）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・aggregate cap 等
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py — ニュースセンチメントの LLM スコアリング
  - regime_detector.py — 市場レジーム判定（MA200 + LLM）
- tools/
  - paper_verification_report.py — paper_trading の検証レポート出力
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（上記は主要ファイル群の抜粋です）

## 運用上の注意 / ヒント

- Monitoring は常に production 用の sqlite_path（Settings.sqlite_path）を使用します。環境に応じて path を明示的に分けることを推奨します。
- run_execution は paper_trading モードで DB を分離します。実運用時に誤って paper_trading データを本番DBへ書き込まないよう環境変数に注意してください。
- process priority の設定（psutil による nice / priority 設定）は権限に依存します。アクセス拒否が発生した場合は警告ログが出て処理は継続します。
- OpenAI API 呼び出しを伴う機能（news_nlp / regime_detector）は API キーと通信が要ります。API 呼び出しにはレート制限や通信エラー対策が実装されていますが、コストと運用リスクを考慮してください。
- monitoring_db.init_monitoring_db() により初回起動時に必要テーブルと簡易マイグレーション（カラム追加）を行います。

## よくあるコマンドまとめ

- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースから機能・挙動を抽出してまとめたものです。実運用に際しては追加の手順（APIキー管理、バックアップ、運用監視、テスト手順、セキュリティ対応等）を整備してください。必要であれば、運用マニュアルや設計ドキュメントのテンプレートも作成します。