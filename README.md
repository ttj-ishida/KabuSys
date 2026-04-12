# KabuSys

KabuSys は日本株の自動売買／研究／監視を目的とした Python パッケージです。本リポジトリは発注・リスク管理・監視・ポートフォリオ構築・ファクター計算・ニュースNLP 等のモジュール群を含みます。

以下は本コードベースの概要、機能、セットアップ手順、使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株自動売買システムのコア機能（ExecutionEngine、OrderManager、Reconciler、RiskManager 等）と、運用監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、AlertManager）および研究用途（ファクター計算、特徴量解析、ニュースNLP、レジーム判定）を提供します。
- DB: SQLite（監視・紙取引用）と DuckDB（時系列・ファクターデータ）を使用。
- 環境分離: `KABUSYS_ENV` により `development` / `paper_trading` / `live` を切替。`paper_trading` では本番 DB と分離して `data/paper_trading.db` を使用します。
- 外部 API: kabuステーション（Kabu API）、J-Quants、OpenAI（ニュースセンチメント / レジーム判定）を利用可能。（APIキーや設定は環境変数で指定）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注セッション実行）
  - OrderManager（注文作成・送信・同期）
  - Reconciler（再起動時の整合性チェック）
  - RiskManager（ポジション上限・drawdown 等の制御）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、プロセス/PID、データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検知）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（異常時にフラグファイルを書いて Execution を停止）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（複数モニタの統合ポーリング・アラート）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio / Strategy 支援
  - 銘柄候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI を利用）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書込
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

---

## 必須環境・依存パッケージ（一例）

- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（Python の標準ライブラリに含まれる）
- ネットワーク接続（外部 API を使う場合）

インストール例（仮の requirements）:
```
pip install duckdb psutil openai requests streamlit
```

※ 実際の requirements.txt があればそれを利用してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュースNLP・レジームで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（1 に設定）

設定は .env / .env.local から自動ロードされます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成・アクティベート
3. 依存パッケージをインストール（上記参照）
4. 必要なディレクトリを作成
   ```
   mkdir -p data
   ```
5. 必須の環境変数を設定（.env を作成するか、環境変数で指定）
   - 少なくとも JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を設定してください
   - OpenAI を利用する場合は OPENAI_API_KEY を設定
6. DuckDB / SQLite の DB ファイルは初回起動時にテーブル作成マイグレーションが自動実行されます（init_monitoring_db 等）

---

## 使い方（起動コマンド例）

- ExecutionEngine（注文実行プロセス）を起動
  - 本番/開発共通（KABUSYS_ENV に従う）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading モード例:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 動作: paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録します。

- Monitoring（監視プロセス）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 注意: run_monitoring は監視用の SQLite を「環境にかかわらず」production sqlite_path（Settings.sqlite_path）で使用します（設計上の仕様）。

- Streamlit ダッシュボード起動（監視データの可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラム的利用例）
  - ニューススコア付与
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date=date(2026,4,11), api_key='YOUR_OPENAI_KEY')
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, target_date=date(2026,4,11), api_key='YOUR_OPENAI_KEY')
    ```

---

## 注意点 / 運用上のメモ

- PID / Kill Flag
  - ExecutionEngine は起動時に PID ファイルを書きます（Settings.pid_file_path）。Monitoring はこの PID を見て実行プロセスの存否をチェックします。
  - KillSwitch は `KILL_FLAG_PATH`（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側では起動時に `kill_flag_clear_on_start` を参照してフラグをクリアするオプションがあります。
- .env 読み込み
  - .env / .env.local はプロジェクトルート（.git or pyproject.toml）を基準に自動読み込みします。既存の OS 環境変数は保護されます。
- Paper Trading 分離
  - paper_trading モードでは発注・約定の挙動をモック化し、本番 DB と完全に分離して記録します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI の呼び出しはレート制限・ネットワーク問題に対してリトライとフォールバック（失敗時はスキップまたは中立値）する設計です。
- process priority / CPU affinity
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による優先度変更に失敗した場合は警告を出しますが続行します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の一覧です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — Settings クラス（環境変数 / .env 読み込み・検証）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - order_manager.py — OrderManager（注文作成・送信）
  - order_repository.py — （注文データ永続化）※一部ファイルは省略
  - reconciler.py — 再起動時のリコンシリエーション
  - execution_engine.py — ExecutionEngine（セッション管理）※参照

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化と DB ラッパー（MonitoringDB）
  - system_monitor.py — CPU/メモリ/Disk、データ鮮度、PID チェック
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — モニタ群の統合（ポーリング実行）
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数計算・スケーリング
  - risk_adjustment.py — セクターキャップ / レジーム乗数
  - __init__.py

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py — ニュース記事を LLM で評価して ai_scores に書込む
  - regime_detector.py — MA200 と LLM を合成して市場レジーム判定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート（コマンドライン）

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## さらに詳しく / 拡張ポイント

- Broker クライアント実装（本番接続 / Mock）や ExecutionEngine の詳細設定は execution 配下に実装されています。実際のブローカー API を組み込む際は BrokerAPIProtocol を実装してください。
- ポジションサイズ計算やリスク制約のパラメータ（max_position_pct, max_utilization, risk_pct 等）は Engine 側で設定可能です。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はデータパイプラインで投入する前提です。データ不足時のフォールバック処理は一部実装されています。

---

もし README に追加したい内容（例: 具体的な設定例の .env.example、CI / デプロイ手順、テスト実行方法、requirements.txt の内容など）があれば教えてください。必要に応じて追記します。