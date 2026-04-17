# KabuSys

KabuSys は日本株自動売買システムの参照実装ライブラリです。本リポジトリは売買実行・監視・ポートフォリオ構築・研究用ファクター計算・AI ニューススコアリング等のコンポーネントを含みます。  
以下はコードベースに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は次の主要コンポーネントを提供します。

- Execution（発注エンジン）: ブローカークライアント経由で注文を発行・管理する実行エンジン（ExecutionEngine）。paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離して検証できます。
- Monitoring（監視）: システムリソース、データ鮮度、注文滞留、ドローダウンなどをポーリングしてログ保存・アラート・Kill Switch を管理するモジュール群。
- Portfolio（ポートフォリオ構築）: 候補選定、配分重み計算、ポジションサイズ計算、セクター制限・レジーム乗数の適用などの純粋関数。
- Research（リサーチ）: DuckDB 上の時系列データからファクター（Momentum / Volatility / Value）や将来リターン、IC、統計要約を計算するモジュール。
- AI（ニュース NLP / レジーム判定）: OpenAI API を使ったニュースのセンチメント評価・マーケットレジーム判定のユーティリティ。
- Tools: Paper Trading の検証レポート生成スクリプトなど。

設計上のポイント:
- 設定は環境変数（および `.env`, `.env.local`）で管理。Settings クラス（kabusys.config）で参照する。
- 監視データは SQLite（デフォルト: `data/monitoring.db`）に永続化。DuckDB（デフォルト: `data/kabusys.duckdb`）は時系列・ファイナンスデータ解析に使用。
- paper_trading モードは `KABUSYS_ENV=paper_trading` で有効。paper_trading 用 DB は `data/paper_trading.db`（設定で変更可）。

---

## 機能一覧

- 発注管理
  - OrderManager / OrderRepository による注文作成・同期・リコンシリエーション
  - Reconciler による起動時の自動復旧
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセスの生存チェック、データ鮮度検査
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 指定条件で `data/kill.flag` を書き、ExecutionEngine に停止シグナルを送出
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - MonitoringEngine: 上記モニタ群の束ねとポーリングループ
  - streamlit ベースの監視ダッシュボード（`streamlit_dashboard.py`）
- ポートフォリオ構築
  - 候補選定（スコア順 / ランク順）
  - 等重・スコア重み配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（Spearman）、統計サマリー
- AI 関連
  - ニュースのセンチメントスコア生成（OpenAI を使用）
  - 市場レジーム判定（ETF MA + マクロニュースベース）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定（psutil ベース）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型アノテーションや一部の構文を想定）
- SQLite（標準ライブラリ）
- 必要パッケージ（お使いの環境に応じてインストールしてください）

例（pip）:
```bash
pip install duckdb psutil openai requests streamlit
```

プロジェクト準備:
1. リポジトリルートで data ディレクトリを作成:
   ```bash
   mkdir -p data
   ```
2. 環境変数を設定（`.env` または `.env.local` をプロジェクトルートに置くか、OS 環境変数を設定）
   - 主要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須の可能性あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: environment（development / paper_trading / live） デフォルト: development
     - LOG_LEVEL: ログレベル（DEBUG/INFO/…） デフォルト: INFO
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の fill モード（instant/partial/never/reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
3. （任意）.env 自動読み込みは既定で有効。無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

DB の初期化:
- Monitoring 用 SQLite, DuckDB は各スクリプトが起動時に必要なテーブルを作成（init_monitoring_db）します。最初の起動で自動的に作られます。

依存ライブラリの例（requirements.txt を作る場合の候補）:
```
duckdb
psutil
openai
requests
streamlit
```

---

## 使い方

以下は主要スクリプトの起動方法と用途例です。

1) 監視ループ（SystemMonitor の単独起動）
- デフォルトでは MONITOR_POLL_INTERVAL=60 秒
- 実行:
  ```bash
  python -m kabusys.run_monitoring
  ```
- 環境変数で間隔上書き:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 注意: Monitoring は Settings.sqlite_path（デフォルト `data/monitoring.db`）を本番環境に関係なく使用します（常に監視ログ DB に書きます）。

2) ExecutionEngine（実際の発注エンジン）
- 実行:
  ```bash
  python -m kabusys.run_execution
  ```
- paper_trading モード（MockBroker を使用し、paper_trading 専用 DB に書き込む）:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  この場合、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用されます。
- ExecutionEngine は起動時に `data/execution.pid`（デフォルト）に PID を書き、停止は `data/stop_requested.flag` ファイルの作成で行えます。Kill Switch は `data/kill.flag` を生成することでエンジンへ停止指令を与えます。

3) Streamlit ダッシュボード（監視ビュー）
- 起動:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- `--db` で監視 DB のパスを指定。デフォルトは `data/monitoring.db`。

4) Paper Trading 検証レポート
- スクリプト:
  - `src/kabusys/tools/paper_verification_report.py`
- 実行例:
  ```bash
  # デフォルト DB を使う場合
  python -m kabusys.tools.paper_verification_report

  # 期間指定・DB指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
- 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ等のサマリと PASS/FAIL 判定。

5) AI モジュール（ライブラリ API）
- ニューススコアリング:
  - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - 必要: `OPENAI_API_KEY` または `api_key` 引数
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 必要: `OPENAI_API_KEY`
- いずれも DuckDB 接続 (`duckdb.connect(...)`) を渡して使用します。

運用用フラグ:
- 停止要求（プロセスを安全に終わらせる）:
  - `data/stop_requested.flag` を作成すると `run_monitoring` / `run_execution` が検知してループを終了します（実行スクリプトがチェックします）。
- Kill Switch:
  - `KillSwitch` が条件を満たすと `data/kill.flag` を書き、ExecutionEngine の停止を促します（デフォルトの flag path は Settings.kill_flag_path）。

ログ:
- 各スクリプトは標準の logging を使用。`LOG_LEVEL` で制御（Settings.log_level）。

その他ユーティリティ:
- プロセス優先度: 起動直後に `set_process_priority("high")` が呼ばれます。psutil の権限により失敗する可能性がありますが安全にログを出してスキップします。

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、default: instant）
- PID_FILE_PATH: Execution PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: Kill flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

Settings クラスは `.env` / `.env.local` をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は本コードベースの主要ファイル一覧（抜粋）です。実際のリポジトリでは更に多くのファイルがある可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
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
      - (その他発注関連のモジュール: broker_factory, execution_engine, order_repository, order_record など)
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
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (実行時に利用するディレクトリ、Git 管理外で良い)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb (DuckDB)

---

## 開発・運用上の注意・トラブルシューティング

- DB マイグレーション: monitoring_db.init_monitoring_db は起動時にテーブルと必要カラムを作成・マイグレーション（冪等）します。ただし DuckDB 側のスキーマは外部スクリプトで準備する必要があるケースがあります（prices_daily / raw_financials 等のソースデータ）。
- AI 機能: OpenAI への呼び出しはネットワークエラーやレートリミットに対して指数バックオフでリトライします。API キー・課金設定に注意してください。
- プロセス優先度 / CPU affinity: 権限不足で設定に失敗しても安全にスキップしますが、期待通りに優先度が変わらない場合があります。
- フラグファイル: `data/stop_requested.flag` や `data/kill.flag` の存在・削除は手動で行えます。起動時に kill.flag を自動でクリアするオプション（KILL_FLAG_CLEAR_ON_START）が設定されているか確認してください。
- paper_trading: 実際のブローカーとの接続を伴わない検証環境です。paper_trading 用 DB は本番 DB と物理的に分離されますが、設定ミスで同じパスを指定すると混在してしまうので注意してください。

---

この README は提供されたコードベースを元に作成しています。実際の運用・追加機能に応じて README を拡張してください。必要であれば各コンポーネント（ExecutionEngine、OrderRepository、AI モジュールなど）向けの詳しいドキュメントも作成します。