# KabuSys — README (日本語)

このリポジトリは「KabuSys」：日本株向け自動売買 / 研究 / 監視のための軽量フレームワークです。以下はコードベースの概要、主要機能、セットアップ／実行方法、ディレクトリ構成の説明です。

重要：この README はソースコードから抽出した設計意図と使い方をまとめたもので、実際の運用前に各種設定（APIキー、DBパス、環境変数など）を必ず確認してください。

---

## プロジェクト概要
KabuSys は以下の主要コンポーネントで構成されています。
- Execution（発注エンジン）：Broker クライアント経由で発注・状態管理を行う（本番 / Paper Trading を切り替え可能）。
- Monitoring（監視）：システム状態・注文状態・リスク（ドローダウン・ポジション数）を定期的に監視しログ・アラートを出す。
- Portfolio（銘柄選定・配分）：候補選定、重み付け、ポジションサイズ計算等の純粋関数群。
- Research（ファクター計算・分析）：DuckDB 上の履歴データからファクターや将来リターン、IC 等を算出。
- AI（ニュース NLP / レジーム判定）：OpenAI を用いたニュースセンチメント評価や市場レジーム判定（LLM 呼び出しはオプション）。
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボードなどの運用ツール。

---

## 主な機能一覧
- 環境ごとの設定管理（KABUSYS_ENV = development | paper_trading | live）
- ExecutionEngine：発注・リスク管理・注文リコンシリエーション
- MonitoringEngine：SystemMonitor・TradeMonitor・RiskMonitor の統合ポーリング
- KillSwitch：リスクトリガー時に flag ファイルを書き込み Execution を停止
- LINE への通知（AlertManager）
- DuckDB を利用したリサーチ用ファクター計算（momentum, volatility, value 等）
- OpenAI を用いたニュースセンチメント（ai/news_nlp）と市場レジーム判定（ai/regime_detector）
- Paper Trading 用の分離 DB と MockBroker（KABUSYS_ENV=paper_trading）
- Streamlit ダッシュボード（監視データ表示）
- paper trading 検証レポート生成スクリプト

---

## 必要条件（推奨）
- Python >= 3.10（ソースは PEP 604 の型アノテーション（`X | None`）を利用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- 外部ライブラリ（例）
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit

インストール例：
```bash
python -m pip install duckdb openai psutil requests streamlit
```
（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリルートへ移動（README を想定したルート）
2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージのインストール（上記参照）
4. 環境変数の設定
   - 本リポジトリはルートの `.env` / `.env.local` を自動読み込みします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化）。
   - 最低限必要な環境変数（各種モジュールで参照されます）：
     - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必要な場合）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注を行う場合）
     - OPENAI_API_KEY — OpenAI API を使う場合に必須
     - KABUSYS_ENV — 起動環境（development | paper_trading | live）。デフォルト: development
     - PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject）。デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使用する場合
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

   例（.env）:
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=xxxx
   ```

5. 必要に応じて data ディレクトリを作成:
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要エントリポイント）

注意：ソースが `src/` 下にある場合、プロジェクトルートで Python パスを設定して実行するか、パッケージをインストールしてください。
例: PYTHONPATH を使う方法
```bash
PYTHONPATH=src python -m kabusys.run_monitoring
PYTHONPATH=src python -m kabusys.run_execution
```

- 監視プロセスを起動（run_monitoring）
  - 説明: SystemMonitor をポーリングして monitoring DB に記録します。
  - 環境変数: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 停止方法:
    - プロセスに KeyboardInterrupt を送る
    - プロジェクトルート `data/stop_requested.flag` ファイルを作成するとループが検出して終了します
  - 実行例:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    PYTHONPATH=src python -m kabusys.run_monitoring
    ```

- Execution エンジンを起動（run_execution）
  - 説明: Broker クライアントを生成し ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBroker を使い DB を紙取引用に分離します。
  - 停止方法:
    - `data/stop_requested.flag` を作成するとエンジンを停止します（KillSwitch とは別の停止フラグ）。
    - KillSwitch（監視側）により `data/kill.flag` が書き込まれると実行を停止する仕組みもあります。
  - 実行例:
    ```bash
    PYTHONPATH=src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Paper Trading 検証レポート
  - スクリプト: kabusys.tools.paper_verification_report
  - 使い方:
    ```bash
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report \
      --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定できます。

- Streamlit ダッシュボード（監視データ表示）
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動方法:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で monitoring DB を開き、ダッシュボードを提供します。

---

## 停止・キルの仕組み（運用メモ）
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを監視しており、存在すると安全にシャットダウンします。
- KillSwitch (data/kill.flag)
  - 監視コンポーネント（RiskMonitor など）が致命的条件を検出すると `data/kill.flag` に理由を記述して書き込みます。ExecutionEngine 側はこのファイルを見て動作を停止する運用です（設定により実行前にクリアできます）。
- PID ファイル
  - Execution は `data/execution.pid`（デフォルト）に PID を書きます。SystemMonitor は PID が生きているかを確認し、stale PID を検出するとログ／アラートします。

---

## 主要設定項目（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabu API 用パスワード（発注する場合）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading 用）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- DUCKDB_PATH: data/kabusys.duckdb（リサーチ用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

---

## 開発・デバッグのヒント
- .env の読み込みは config.py の自動ロジックで行われます。プロジェクトルートの `.env` / `.env.local` を用意してください（OS 環境変数が優先されます）。
- DuckDB を利用した分析関数は副作用がなく、DuckDB 接続を注入して単体テストがしやすい設計です。
- OpenAI 呼び出し部は例外・429/タイムアウト等を考慮してリトライ・フォールバックしています。テストでは _call_openai_api をモックできます（ソースにその旨のコメントあり）。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主なファイル・ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env のロードと Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py        — SQLite 用永続層（監視テーブル定義）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — 注文滞留・約定異常のチェック
    - risk_monitor.py         — ドローダウン・ポジション上限のチェック
    - alert_manager.py        — LINE 通知
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（BrokerFactory, ExecutionEngine, OrderRepository 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・単元丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/value/volatility 等
    - feature_exploration.py  — forward returns / IC / summary
  - utils/
    - process_priority.py     — プロセス優先度設定ユーティリティ
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLITE_PATH のデフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
    - kabusys.duckdb (DUCKDB_PATH のデフォルト)
    - execution.pid / stop_requested.flag / kill.flag など

---

## よくある運用フロー（例）
1. リサーチ（DuckDB）で銘柄スクリーニング & ファクター計算
2. シグナル生成 → ExecutionEngine で発注
3. MonitoringEngine を常時稼働させ、System/Trade/Risk を監視
4. 異常時は LINE 通知・kill.flag による自動停止
5. Paper Trading では専用 DB に記録して本番データと完全分離、後で paper_verification_report で評価

---

## 注意事項・制約
- Python 3.10 以降を推奨（型アノテーション構文に依存）
- OpenAI / ブローカー API を使う機能は API キー／認証情報の設定が必要
- 本リポジトリのコードは運用を想定しています。実運用前に安全性（例：リスクパラメータ・最大発注量・手数料推定）を十分に検討してください
- DB スキーマやマイグレーション処理は簡易的な手法を採用しているため、大規模運用時は移行戦略を検討してください

---

必要であれば、README にサンプル `.env.example`、依存ファイル（requirements.txt）のテンプレート、あるいはデプロイ手順（systemd / supervisor 用のユニットファイル例）を追加できます。どの情報を追加しましょうか？