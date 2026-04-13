# KabuSys

日本株向け自動売買フレームワーク（ライブラリ＋運用ツール群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注/実行 → 監視/アラート といった自動売買パイプラインの各コンポーネントを含むサンプル実装です。DuckDB/SQLite をデータレイヤに用い、OpenAI を活用したニュース NLP / レジーム判定などの機能を備えています。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要な依存ライブラリ
- セットアップ手順
- 環境変数（主なもの）
- 実行方法（使い方）
- ディレクトリ構成
- 開発メモ / 注意点

---

## プロジェクト概要
KabuSys は日本株自動売買に関する以下の責務をモジュール化したコードベースです。

- ファクター計算（momentum, volatility, value 等）: research/
- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数決定）: portfolio/
- 実行エンジン（ブローカー抽象化、注文管理、リコンシリエーション）: execution/
- 監視（システム状態、注文滞留、リスク監視、キルスイッチ）: monitoring/
- AI（ニュースセンチメント・レジーム判定）: ai/
- 運用ツール（paper trading レポート、Streamlit ダッシュボード等）: tools/, monitoring/streamlit_dashboard.py

重要設計点:
- 本番データと paper_trading は分離（KABUSYS_ENV による切替）
- データ鮮度やプロセス生存性を監視して自動的にアラート・停止フラグを出す
- OpenAI 呼び出しはフェイルセーフ（失敗時はスキップ or 中立スコアで継続）

---

## 主な機能一覧
- SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの PID チェック、データ鮮度判定
- TradeMonitor: 注文滞留（stale）・約定異常価格の検出
- RiskMonitor: ドローダウン・ポジション上限監視、リスクイベント記録
- KillSwitch: 重大リスク発生時に flag ファイルを書き込み ExecutionEngine 停止を誘導
- AlertManager: LINE Messaging API を用いたクールダウン付き通知
- MonitoringEngine: 上記モニタ群を束ねて定期実行
- ExecutionEngine / OrderManager / Reconciler: 発注、ブローカー同期、自動リコンシリエーション
- Portfolio モジュール: 候補選定、重み付け、ポジションサイジング、セクター制約、レジーム乗数
- Research モジュール: ファクター計算、将来リターン、IC 計算、統計サマリー（DuckDB ベース）
- AI モジュール: ニュースを LLM でスコア化（ai.score_news）、レジーム判定（ai.regime_detector.score_regime）
- ツール:
  - run_monitoring.py: 監視ポーリングループ起動
  - run_execution.py: 実行エンジン起動（paper_trading モードで MockBroker を使用）
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成
  - monitoring/streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

---

## 必要な依存ライブラリ
少なくとも以下の Python パッケージが必要です（バージョンは実環境に合わせて調整してください）。

- python >= 3.9
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを利用する場合)
- sqlite3（標準ライブラリ）
- その他、プロジェクトで使用するパッケージ

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（要件管理用の requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. 仮想環境を作成して有効化（任意）
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに .env を作成（下記参照の環境変数を設定）
   - リポジトリは自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し .env / .env.local を読み込みます。
   - テストなどで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. データディレクトリ作成:
```bash
mkdir -p data
```
5. DuckDB / SQLite の初期はアプリ起動時に自動でテーブルを作成します（init_monitoring_db が冪等に作成します）。

---

## 主要な環境変数

（.env に設定しておくと便利です）

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` のとき、run_execution は MockBroker を使用し SQLite は `PAPER_TRADING_SQLITE_PATH` に書き込む。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所で）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を使用する
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。0以下や不正値はデフォルトにフォールバック。
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABU_API_PASSWORD=...
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## 実行方法（使い方）

以下は代表的なコマンド例です。プロジェクトルートで実行してください。

- 監視ループを起動（ポーリングで各種モニタを回す）
```bash
python -m kabusys.run_monitoring
# または
python src/kabusys/run_monitoring.py
# MONITOR_POLL_INTERVAL を変更する場合:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
備考:
- run_monitoring はプロセス優先度を高く設定します（set_process_priority("high")）。
- MONITOR_POLL_INTERVAL のデフォルトは 60 秒。1 未満の値は無効としてデフォルトに戻ります。
- 監視は Settings.sqlite_path を使用（環境にかかわらず本番 monitoring DB を参照します）。

- 実行エンジンを起動（発注処理）
```bash
python -m kabusys.run_execution
# または
python src/kabusys/run_execution.py
```
備考:
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、`PAPER_TRADING_SQLITE_PATH` に書き込みます（本番 DB と分離）。
- ExecutionEngine もプロセス優先度を高く設定します。

- Paper Trading 検証レポート生成
```bash
# モジュールとして実行可能
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit ダッシュボード（監視データを可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI 関連（ライブラリとして呼び出す）
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込みロジック（.env 自動ロード機能を持つ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores に書込み
    - regime_detector.py — マクロ＋MA200 を組み合わせたレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 監視エンジン
    - alert_manager.py — LINE 通知
    - kill_switch.py — kill.flag 制御
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数決定・上限・スケーリング
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・リコンロジック（一部省略）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート作成スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。全ファイルは src/kabusys 内を参照してください。）

---

## 開発メモ / 注意点
- Settings（config.py）はプロジェクトルートにある .env / .env.local を自動でロードします。OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MonitoringDB には起動時にテーブル作成と簡易マイグレーション（列追加）処理があります（init_monitoring_db）。
- run_execution は paper_trading モード時に本番 DB と分離されるよう設計されています（重要）。
- OpenAI を用いる機能は API キー漏洩に注意してください。テストでは関数の呼び出し箇所をモック可能なように実装されています（内部で API 呼び出しを抽象化）。
- プロセス優先度設定や CPU affinity は OS に依存します。権限不足で失敗することがあるため例外は警告で吸収します。
- ツール群・AI 呼び出しは外部 API 呼び出しを行うため、実運用ではレート制限・再試行ポリシーを考慮してください（コードは基本的なエクスポネンシャルバックオフを実装済み）。

---

この README はコードの理解とローカル実行開始のための最小限の案内を目的としています。さらに詳細な設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトにある場合はそちらを参照してください。必要であれば README の拡張やサンプル .env の追加、各 CLI の詳細な使い方追記を行います。