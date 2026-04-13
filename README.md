# KabuSys

日本株向け自動売買プラットフォーム（モジュール群）の参照実装です。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ/ファクター解析、AI を用いたニュースセンチメント等のコンポーネントを含みます。

主な目的は、実運用を想定した設計（永続化、冪等性、フェイルセーフ、外部 API の抽象化）を示すことです。

---

## 主な機能（概要）

- 実行エンジン起動スクリプト（run_execution）
  - 本番 / Paper Trading 切替（環境変数 KABUSYS_ENV）
  - Broker クライアント抽象化（MockBroker を含む）
  - オーダー管理、リスク管理、リコンシリエーション（自動復旧）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 上記監視をポーリングし、Kill Switch 判定、LINE 通知（AlertManager）
  - SQLite に監視ログ保存（monitoring_db.init_monitoring_db）

- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分/スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ

- AI（OpenAI）連携
  - ニュース記事のセンチメント評価（news_nlp.score_news）
  - マクロセンチメント + MA200 を用いた市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しはフェイルセーフ・リトライ実装あり

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit ベース監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## 必要条件（推奨）

- Python 3.10+
  - PEP 604 の型記法（X | None）を使用しているため Python 3.10 以上が必要です。
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
  - 他（プロジェクトで必要な場合：pydantic 等は含まれていませんが実環境に応じて追加）

サンプルインストールコマンド（仮の requirements）:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

※ 実際の production では requirements.txt を用意して管理してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール（上記参照）
4. 環境変数を用意する
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
     - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視/停止用）
5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要コマンド／実行方法）

- 監視ループを起動（SystemMonitor の単体スクリプト）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト: 60）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 監視は Settings.sqlite_path を使用して SQLite にログを保存します（監視は環境にかかわらず production の sqlite_path を使用）。

- ExecutionEngine（発注実行）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動直後に Reconciler が走って未確定注文の同期などを行います。

- Paper Trading 検証レポート生成（コマンドラインツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（プログラムから呼び出す例）
  - ニューススコア（ai_scores に書き込む）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    print("scored:", count)
    ```
  - レジーム判定
    ```python
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

---

## 主要設定項目（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用監視 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

.env のサンプル（最低限）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_key
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
LOG_LEVEL=INFO
```

---

## 実装上の注意点 / 補足

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込みます。
  - OS 環境変数は上書きされません。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

- Paper Trading
  - KABUSYS_ENV=paper_trading 時は MockBroker を使い、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と完全に分離されます。

- 監視データベース
  - monitoring_db.init_monitoring_db は冪等でテーブルやインデックスを作成します。既存 DB のマイグレーション（列追加）も簡易的に扱います。

- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI API の失敗に対してリトライとフォールバック（score=0.0 等）を実装しています。
  - API キーやコスト管理は運用側で行ってください。

- プロセス優先度の設定
  - set_process_priority() は psutil を利用し OS に応じて優先度を変えます。権限がない場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み）
- run_monitoring.py — SystemMonitor ポーリングループ起動
- run_execution.py — ExecutionEngine 起動
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート生成
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
  - __init__.py
- execution/
  - reconciler.py
  - order_manager.py
  - order_repository.py (省略されているが存在)
  - execution_engine.py (省略されているが存在)
  - broker_factory.py (省略されているが存在)
  - broker_api.py (プロトコル定義)
  - order_record.py (状態管理)
- utils/
  - process_priority.py
  - __init__.py

（上記は主要モジュールの抜粋です。実際のファイル全体はリポジトリを参照してください。）

---

## 追加情報 / 開発のヒント

- DuckDB は大規模な時系列データ分析（prices_daily / raw_financials など）に利用します。データロード処理は data.pipeline 等の別モジュールで扱われます（本スニペットには一部のみ含まれます）。
- テスト時は OpenAI や外部 API 呼び出しをモックしてください（news_nlp._call_openai_api / regime_detector._call_openai_api は差し替え可能）。
- ロギングやアラートの閾値は Settings の環境変数で調整できます（CPU/MEM/DISK のしきい値や監視間隔など）。

---

この README はコードベースの主要部分に基づき要点をまとめたものです。追加で「運用手順」「CI/CD」「詳細設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）」の記載が必要であれば内容を提示してください。