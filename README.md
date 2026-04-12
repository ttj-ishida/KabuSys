# KabuSys

日本株向けの自動売買／リサーチ基盤の一部コードベースです。本リポジトリは以下の主要機能（監視・発注・ポートフォリオ構築・ファクター計算・AIニューススコアリング等）を持つモジュール群で構成されています。

> 注: この README はソースコード（src/kabusys 以下）に基づいて作成しています。環境ごとの運用方針や外部サービスの取り扱い（実口座、APIキー管理など）は別途運用ドキュメントに従ってください。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- 自動発注（ExecutionEngine / OrderManager / Reconciler 等）
- 取引・システム監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- ファクター計算・研究（momentum / volatility / value 等）
- AI を使ったニュースセンチメント解析（OpenAI を利用）
- Paper Trading 向けの検証ツール（レポート生成、専用 DB）

主要特徴:
- 本番・紙上（paper_trading）環境の分離（paper_trading 用 DB に記録）
- DuckDB / SQLite によるデータ処理と永続化
- LINE によるアラート送信（AlertManager）
- Streamlit による監視ダッシュボード（読み取り専用）

---

## 機能一覧（抜粋）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出、kill.flag 生成
  - MonitoringEngine: 監視ループ & アラート連携
  - streamlit_dashboard.py: 監視ダッシュボード（read-only）

- 発注・実行
  - OrderManager: 注文作成・送信・状態管理
  - Reconciler: 再起動時のブローカー突合（OrderSent の同期 / ポジション差分検出）
  - ExecutionEngine（起動スクリプト run_execution.py で起動）

- ポートフォリオ / 配分
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース / 等配分 等）
  - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）

- リサーチ
  - calc_momentum / calc_volatility / calc_value（DuckDB を利用したファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（特徴量解析）

- AI
  - news_nlp.score_news: raw_news を集約し OpenAI へ投げて ai_scores を作成
  - regime_detector.score_regime: MA とマクロニュース（LLM）を合成して市場レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート CLI

---

## セットアップ手順

前提
- Python 3.10 以上（ソース内での型注釈（X | Y）を利用）
- SQLite, DuckDB を利用可能な環境
- ネットワーク環境（OpenAI / LINE API 等を利用する場合）

1. リポジトリをクローンし Python 仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（代表的なパッケージ）
   ※requirements.txt がない場合は下記をインストールしてください。
   ```bash
   pip install duckdb psutil openai requests streamlit
   ```
   - openai: news_nlp / regime_detector が利用
   - psutil: プロセス優先度・CPU affinity、システム指標取得
   - duckdb: ファクター計算 / AI モジュールが DuckDB を利用
   - streamlit: ダッシュボード起動
   - requests: LINE API 通信

3. データディレクトリ作成
   ```bash
   mkdir -p data
   ```
   デフォルトの DB パス:
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db

4. 環境変数設定（.env ファイルをプロジェクトルートに置くと自動ロードされます）
   自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。

   代表的なキー（.env 例）
   ```
   KABUSYS_ENV=development   # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant
   LOG_LEVEL=INFO
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=1
   ```

注意点:
- paper_trading 環境は実ブローカーではなく MockBrokerClient を使い、data/paper_trading.db に記録されます（本番 DB と分離）。
- OpenAI を使う機能は OPENAI_API_KEY が必須です（score_news, score_regime）。

---

## 使い方（実行コマンド・例）

各スクリプトはモジュールとして起動できます。以下は主要な起動方法の例です。

- 監視ループ（Monitoring を定期実行）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を上書き:
    ```bash
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - 実行時にプロセス優先度を "high" に設定し、monitoring DB を初期化します（init_monitoring_db）。

- ExecutionEngine 起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（paper_trading 用 SQLite）を使用します。

- Streamlit 監視ダッシュボード（読み取り専用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（CLI）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプションで --db PATH を指定して別 DB を参照可能。

- AI ニューススコアリング（プログラム呼び出し例）
  score_news は Python API で呼び出します（OpenAI API キー必須）。
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

- 市場レジーム判定（score_regime）
  ```py
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

---

## 環境変数一覧（主要なもの）

- KABUSYS_ENV: 開発モード等（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE による通知設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 注意・運用メモ

- process_priority の設定は psutil を使って行いますが、OS 権限に依存するため権限不足で失敗する可能性があります（警告ログが出るのみで継続）。
- DuckDB によるクエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。データ投入パイプライン（kabusys.data.pipeline 等）が必要です。
- AI 関連処理は外部 API に依存するため、障害時はフォールバック（スコア 0.0 を使用など）する設計になっていますが、API キー漏洩などには注意してください。
- kill.flag を用いた強制停止は冪等設計（既存ファイルは上書きしない）です。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと自動でクリアします。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定して実行してください（本番 DB と分離されます）。

---

## ディレクトリ構成（主要ファイルの簡易説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ / モジュール
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py — マクロ + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite ベースの永続層（テーブル初期化 / CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE Push 通知実装
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 発注フロー管理（OrderManager）
  - reconciler.py — 起動時の再同期処理
  - （その他の execution モジュールは実装参照）
- portfolio/
  - portfolio_builder.py — 候補選定・重みづけ
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プロセス優先度・CPU affinity のユーティリティ

（上記はコードベースの抜粋です。実際のリポジトリには data/ や追加モジュールが存在する場合があります。）

---

## 開発・貢献メモ

- .env のパースや自動ロードは config.py 内で実装されています。開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。
- DuckDB クエリは SQL と Python の組合せで書かれているため、テーブルスキーマ変更時は関連クエリの修正が必要です。
- API 呼び出し箇所（OpenAI / LINE / ブローカー）はリトライやフォールバックを組み込んでいる箇所が多く、テスト時はモックで置き換えることを推奨します（例: news_nlp._call_openai_api の patch）。

---

もし README に追加したい内容（例: CI 設定、より詳しい運用手順、環境別のデプロイ手順、依存バージョン固定の requirements.txt 生成など）があれば教えてください。必要に応じてサンプル .env.example や簡単な運用手順も用意します。