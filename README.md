# KabuSys — README

以下は、このコードベース（src/kabusys 以下）に対する日本語の README です。プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を含みます。

注意: 実行例はリポジトリルート（pyproject.toml ある場所）を想定しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買＆運用支援を目的としたモジュール群です。主な機能は以下のとおりで、発注エンジン・監視（Monitoring）・ポートフォリオ構築ロジック・リサーチ/ファクター計算・ニュース NLP（OpenAI）連携などを備えています。

設計方針の特徴:
- DuckDB / SQLite をデータレイヤに使用（ローカル DB に SQL でアクセス）
- モジュールは本番 / ペーパー（paper_trading）環境を想定して分離可能
- LLM（OpenAI）を使ったニュースセンチメント / レジーム判定機能を提供
- 監視（Monitoring）により稼働・滞留注文・ドローダウン等を検知し、LINE 等へ通知可能
- フェイルセーフ（API失敗時のフォールバック、部分失敗保護等）を重視

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - Broker クライアントのファクトリ（paper_trading 時は MockBroker を利用）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期）

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス / データ鮮度監視
  - TradeMonitor：滞留注文、約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：停止フラグ（data/kill.flag）生成による Execution 停止
  - AlertManager：LINE Push による通知
  - MonitoringEngine：上記を束ねたポーリングループ
  - streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み付け、セクター制限、ポジションサイズ計算（単元株丸め等）

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）・統計サマリ

- AI（LLM 統合）
  - news_nlp.py：ニュース記事をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores へ書き込む
  - regime_detector.py：ETF の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定

- Tools
  - paper_verification_report.py：Paper Trading DB を解析して検証レポートを生成
  - その他ユーティリティ（プロセス優先度設定など）

- 設定管理
  - config.py：.env 自動ロード（.env, .env.local）、環境変数のラッパー（Settings）

---

## 必要環境（ざっくり）

- Python 3.10 以上（型ヒントの union 型等を使用）
- SQLite（標準の sqlite3 モジュールを使用）
- 必要な Python パッケージ（下記参照）

推奨パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit
- (必要に応じて) その他：pytest 等（開発用）

例: pip インストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（リポジトリに requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンしてルートへ移動
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. データディレクトリを作成（デフォルトの DB パスに合わせる）
```
mkdir -p data
```
5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は上書き可）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主要な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使用し、paper DB に記録されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な場合）
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 設定
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（INFO など）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値など

例 .env（最小）
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 実行方法（主要なスクリプト／使い方）

- 監視ループ（Monitoring）
  - run_monitoring.py は SystemMonitor のポーリングループを起動します。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き可能（デフォルト 60 秒）。
  - 実行例:
    ```
    python -m kabusys.run_monitoring
    ```
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検出して終了します。

  注意: Monitoring は「環境（KABUSYS_ENV）」に関わらず本番用の sqlite_path（Settings.sqlite_path）を使用します（設計上の意図）。

- Execution（発注エンジン）
  - run_execution.py は ExecutionEngine を起動します。KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番環境では本番 DB を使用します。
  - 実行例:
    ```
    python -m kabusys.run_execution
    ```
  - 停止: `data/stop_requested.flag` を作成するとエンジンが検出して停止処理を行います。
  - run_execution は起動時に `data/execution.pid` を使用／管理します。

- Streamlit ダッシュボード
  - 監視 DB（SQLite）を参照するダッシュボードです。
  - 起動例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードは読み取り専用で DB が開けない場合はエラー表示します。

- Paper Trading 検証レポート
  - ツール: paper_verification_report.py
  - 例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション `--db` で DB パスを指定できます。デフォルトは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。

- AI モジュール（プログラムからの呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して呼び出します。OPENAI_API_KEY が必要。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB 接続 + API キー。DB 書き込みを伴います（冪等）。

- Kill Switch / Flags
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止を要求します。KillSwitch の評価は Monitoring 側で行われます。
  - Execution 側は `data/stop_requested.flag` を監視して安全停止します（両者は用途が異なります）。

---

## 設定の詳細（Settings のポイント）

- 自動 .env ロード:
  - デフォルトではプロジェクトルートの `.env` と `.env.local` が読み込まれます（OS 環境変数を保護）。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- KABUSYS_ENV:
  - 値: development | paper_trading | live
  - paper_trading の場合、発注系はペーパー DB に完全分離されます。
- PAPER_FILL_MODE（paper_trading 用）
  - instant | partial | never | reject（未定義値は例外）
- 監視閾値:
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（Settings で参照）

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys をルートとした構成の抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、.env 自動ロードロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル初期化・永続化レイヤ
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 監視コンポーネント束ね（ポーリングループと run_once）
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 発注制御（OrderState マシンの外向き API）
  - reconciler.py — 起動時の注文/ポジション突合せ
  - その他: broker_factory/ order_repository / execution_engine 等（発注周りのコンポーネント）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定（リスクベース / 等配分）
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM に流して銘柄別スコアを生成・書き込み
  - regime_detector.py — 市場レジーム判定（MA + LLM）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading DB の検証レポート生成ツール

- src/kabusys/utils/
  - process_priority.py — OS 横断のプロセス優先度 / CPU affinity 設定ユーティリティ

- data/（実行時に使用することが多い）
  - monitoring.db（デフォルトの監視 SQLite）
  - paper_trading.db（paper_trading 用 DB）
  - kabusys.duckdb（DuckDB データベースファイル）
  - execution.pid（実行エンジンの PID）
  - kill.flag, stop_requested.flag（フラグファイル）

---

## 運用上の注意 / 補足

- Monitoring は Settings.sqlite_path（監視 DB）を使用します。環境（KABUSYS_ENV）が paper_trading でも監視は本番用 monitoring.db を参照する設計です。必要に応じて設定を変更してください。
- Paper Trading は発注（broker）を分離しており、誤って本番ブローカーで発注しないよう .env を適切に設定してください。
- OpenAI 統合（news_nlp / regime_detector）は API キー必須です。API の失敗時はフォールバックロジックがありますが、料金とレイテンシには注意してください。
- PID / flag ファイルを用いたプロセス制御（stop, kill）を採用しています。手動でフラグを書き換える場合は内容とタイミングに注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB をチェックし、必要なカラム追加（例: peak_value, latency_ms）を行いますが、重大なスキーマ変更は別途検討してください。

---

必要に応じて README に追記できます（例: 開発用スクリプト、CI 設定、より詳しい環境変数一覧、API ドキュメントなど）。追加してほしい項目があれば教えてください。