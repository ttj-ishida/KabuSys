# KabuSys

日本株自動売買プラットフォーム（ライブラリ兼実行スクリプト群）。ポートフォリオ構築、発注管理、監視、リサーチ、LLM を用いたニューススコアリング等のコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤実装です。主な目的は以下です。

- シグナル → 注文 → 約定管理のための Execution コンポーネント
- システム稼働状況・注文状況・リスクを監視する Monitoring コンポーネント
- ポートフォリオ構築（候補選定・重み付け・サイズ算出）
- DuckDB 上の時系列データを用いたファクター計算・リサーチ
- OpenAI（LLM）を用いたニュースセンチメント評価・レジーム判定
- Paper Trading 用の分離された DB を使った検証ツール群
- Streamlit によるシンプルな監視ダッシュボード

---

## 機能一覧

- Execution
  - OrderManager / OrderRepository による発注ワークフロー
  - Reconciler による再起動時のブローカー照合と自動復旧
  - Paper Trading モード（環境変数 `KABUSYS_ENV=paper_trading`）では MockBroker を使用し、別 DB に書き込み
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウン・保有上限監視（kill.flag を書く KillSwitch 連携）
  - AlertManager: LINE Push による一方向アラート送信（クールダウン管理）
  - MonitoringEngine: 上記モニタを束ねたポーリング実行
  - Streamlit ダッシュボード（監視 DB を read-only で表示）
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - DuckDB を用いたモメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）
  - news_nlp.score_news: raw_news を集約し OpenAI API で銘柄別センチメントを算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースを LLM 評価で合成して market_regime を判定
- ツール
  - paper_verification_report: Paper Trading DB を元に稼働率・成功率・レイテンシ等の検証レポート出力

---

## 前提／依存関係（主なライブラリ）

- Python 3.10+
- duckdb
- sqlite3 （標準組み込み）
- psutil
- requests
- openai (OpenAI Python SDK)
- streamlit（ダッシュボード起動時）
- その他：標準ライブラリ（datetime, logging 等）

requirements.txt（例）
```
duckdb
psutil
requests
openai
streamlit
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```

3. 環境変数設定（.env をプロジェクトルートに置くか、環境に直接設定）
   - 自動で .env / .env.local が読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 必要な DB ディレクトリを作成（デフォルトは `data/`）
   ```
   mkdir -p data
   ```

---

## 主な環境変数（Settings による検証あり）

必須（運用時）：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション（ブローカー）API パスワード

任意／設定：
- KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBroker を使い、DB は `PAPER_TRADING_SQLITE_PATH` に分離
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール実行時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE）に通知するため

例 .env（最小）
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
JQUANTS_REFRESH_TOKEN=...
```

注意:
- Settings は `.env` と `.env.local` を自動読み込み（OS 環境変数を上書きしない / `.env.local` は上書き可）。自動ロードを停止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- `PAPER_FILL_MODE` などの値は検証され、不正値は起動時に例外が発生します。

---

## 実行方法

ソース直下で仮想環境を有効にした上で実行してください。

1. ExecutionEngine（実際の発注処理）を起動
   - モジュールとして実行:
     ```
     python -m kabusys.run_execution
     ```
   - 挙動:
     - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、データは `PAPER_TRADING_SQLITE_PATH` に記録（本番 DB と分離）。
     - プロセス優先度を "high" に設定（psutil を通じて）。権限がないと警告が出ます。
     - DuckDB / SQLite に接続し、ExecutionEngine.run_session() を実行します。

2. Monitoring（ポーリング監視）を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。1 未満の値は無効としてデフォルトにフォールバック。
   - Monitoring は常に本番用の sqlite_path を使用（環境に関わらず）。

3. Streamlit ダッシュボード（監視用）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - DB を読み取り専用で開きます。MonitoringEngine が `data/monitoring.db` を作成・更新している必要があります。

4. Paper Trading 検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` で DB ファイルを指定可能（デフォルトは `data/paper_trading.db`）。

5. AI 関連関数（プログラムからの呼び出し例）
   - ニューススコアリング（Python API）
     ```py
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     n = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
     print("written:", n)
     ```
   - レジーム判定
     ```py
     from datetime import date
     from kabusys.ai.regime_detector import score_regime
     conn = duckdb.connect("data/kabusys.duckdb")
     score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
     ```

---

## 設定と挙動の補足

- DB 初期化: run_execution/run_monitoring 起動時に監視用テーブルは `init_monitoring_db` によって冪等に作成されます（マイグレーションも一部対応）。
- Paper Trading: `KABUSYS_ENV=paper_trading` の場合、Paper 用 SQLite（デフォルト `data/paper_trading.db`）に全て書き込み、本番 DB と完全に分離されます。`PAPER_FILL_MODE` で約定動作を制御。
- プロセス優先度: 起動時に `set_process_priority("high")` を呼びます。OS によっては権限不足や未対応でスキップされます。
- Kill Switch: RiskMonitor が重大リスクを検出すると `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）に理由を書き込むことで ExecutionEngine に停止シグナルを送ります。
- モジュールは明示的な現在時刻参照（date.today()/datetime.today()）を避ける設計が多く、検証時のルックアヘッドバイアスを抑えています。

---

## ディレクトリ構成（抜粋と説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/ — 発注関連（OrderManager, Reconciler, BrokerFactory, OrderRepository など）
    - order_manager.py
    - reconciler.py
    - ...
  - monitoring/ — 監視関連
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/ — ポートフォリオ構築ロジック
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/ — ファクター計算・リサーチ
    - factor_research.py
    - feature_exploration.py
  - ai/ — LLM を使った機能
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py — psutil を使った優先度/affinity 設定
  - data/ —（実行時生成）DuckDB / SQLite ファイルや PID / flag ファイルを配置する想定

---

## よくある注意点・トラブルシューティング

- psutil による優先度変更や CPU affinity は権限が必要な場合があります。権限がないと警告が出てスキップされます。
- OpenAI API の呼び出しはネットワーク/レート制限等の影響を受けます。news_nlp/regime_detector はリトライとフォールバックの措置を持ちますが、API キーが未設定だと例外になります。
- DuckDB / SQLite ファイルのパスは Settings で制御されます。パスに対するファイルシステム権限を確認してください。
- streamlit ダッシュボードは監視 DB を read-only で開くため、MonitoringEngine が動作してデータを用意している必要があります。

---

## 参考

- .env 読み込みの挙動や変数の検証は `src/kabusys/config.py` を参照してください。
- 監視 DB のスキーマ / 永続化 API は `src/kabusys/monitoring/monitoring_db.py` に実装されています。
- Paper Trading 検証ロジックは `src/kabusys/tools/paper_verification_report.py` を参照してください。
- LLM 関連の実装（リトライ・レスポンス検証・JSON mode 利用）は `src/kabusys/ai/` にあります。

---

この README はコードベースから主要な使用法・構成をまとめたものです。実際の運用やデプロイ時は環境変数の管理、API キーの保護、DB のバックアップ等を適切に行ってください。