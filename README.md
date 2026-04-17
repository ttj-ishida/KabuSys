# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群です。  
本リポジトリは、発注エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI を使ったニュース評価などのコンポーネントで構成されています。

以下はコードベース（src/kabusys）を元にした README です。

---

## プロジェクト概要

- 日本株自動売買システムのコアライブラリ群。発注、監視、リスク管理、ポートフォリオ構築、リサーチ（ファクター計算）、
  およびニュースの NLP スコアリング（OpenAI 利用）を含みます。
- 設定は環境変数（およびプロジェクトルートの `.env` / `.env.local`）で行います。`kabusys.config.Settings` を通じて参照されます。
- SQLite / DuckDB をデータ永続層に使用します。Paper Trading（検証）用に本番 DB と分離する仕組みがあります。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine / OrderManager / OrderRepository により注文作成・同期・キャンセルを管理
  - Reconciler による再起動時の自動復旧（ブローカー照合）
  - paper_trading 環境では MockBrokerClient を使用し専用 DB に記録（本番 DB と分離）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度を監視
  - TradeMonitor: 注文滞留（stale orders）や約定価格異常を検出
  - RiskMonitor: ドローダウン、ポジション数上限を監視しリスクイベントを記録
  - KillSwitch: 条件を満たすとデータディレクトリに `kill.flag` を書き込みエンジン停止を促す
  - AlertManager: LINE Messaging API による通知（クールダウン管理）

- Portfolio（銘柄選定・配分）
  - 候補選定、等分配／スコア加重、リスクベースの株数決定、セクターキャップ、レジーム乗数など

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリー

- AI（ニュース評価・レジーム検出）
  - news_nlp: raw_news を OpenAI に送り銘柄別センチメント（ai_scores）を生成
  - regime_detector: 200日 MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定
  - Streamlit ダッシュボードで監視データの可視化
  - Paper Trading 検証レポート生成ツール

---

## 前提 / 必要ソフトウェア

- Python 3.8+
  - 型表記や from __future__ が使われているため少なくとも 3.8 以上を推奨
- SQLite（標準ライブラリで利用）
- 推奨パッケージ（概略）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

例（pip インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

※ 実際の requirements.txt は本リポジトリに含まれていません。プロダクション運用ではバージョン固定した requirements を用意してください。

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリを src を含むルートに設定するか、パッケージをインストールしてください。

   - 開発環境で直接実行する場合:
     - PYTHONPATH に `src` を追加して実行するか、src 配下に移動して `python -m` でモジュール実行します。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. 環境変数 / `.env` の準備
   - プロジェクトルートに `.env`（もしくは `.env.local`）を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、monitoring スクリプトで使用）

4. データディレクトリ作成
```
mkdir -p data
```
（SQLite / DuckDB ファイルは初回実行時に生成されます）

---

## 使い方

以下は主な実行方法の例です。環境に応じて PYTHONPATH やパッケージインストール方法を調整してください。

- Monitoring の起動（長時間ポーリング）
  - 環境変数でポーリング間隔を変更可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 例:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path を参照して SQLite にログを記録します（Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します）。
  - 停止させるにはプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C。

- ExecutionEngine（発注エンジン）の起動
  - Paper Trading と本番で使用する SQLite が切り替わります。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用。
  - 例（Paper Trading）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止します。

- Streamlit ダッシュボード（監視 UI）
  - ローカルで監視 DB を参照する read-only 表示:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードではダッシュボード集計、ポジション、最近の注文、最新のシステム状態、最近のリスクログなどを表示します。

- Paper Trading 検証レポート生成ツール
  - 例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB は `data/paper_trading.db`。`--db` でパス指定可。
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95 など）と合格判定（PASS/FAIL）。

- AI（ニューススコア・レジーム判定）の呼び出し（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（prices_daily/raw_news 等）を渡し、指定日向けにニュースをスコアリングして ai_scores テーブルへ書き込みます。
    - api_key 引数を指定しない場合は環境変数 OPENAI_API_KEY を参照します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ保存します。

---

## 環境変数と設定の詳細（抜粋）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。
  - 既存 OS 環境変数は保護され、`.env.local` は上書き可能（ただし OS 環境変数は保護される）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- 重要な Settings プロパティ（おもなもの）
  - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
  - kabu_api_password (KABU_API_PASSWORD 必須)
  - OPENAI_API_KEY（AI を使う場合）
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_FILL_MODE: instant | partial | never | reject
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - PID_FILE_PATH / KILL_FLAG_PATH

---

## 停止フラグ・PID・Kill Switch

- stop_requested.flag
  - 実行スクリプト（run_monitoring, run_execution）は `data/stop_requested.flag` の存在を監視し、存在すると安全に終了します。

- kill.flag
  - KillSwitch によりリスク条件（ドローダウン超過等）を満たした場合に `data/kill.flag` が書き込まれます。ExecutionEngine は起動時にこのフラグが存在する場合は起動を行いません。KillSwitch は理由テキストをファイルに書き込みます。

- PID
  - 実行時に PID をファイルに書き出す仕組み（Settings.pid_file_path 等）を使用しています。SystemMonitor は PID ファイルの stale チェックを行います。

---

## ディレクトリ構成

（主要ファイルのみ、src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み / Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースの LLM センチメント評価（ai_scores 書き込み）
    - regime_detector.py — マクロ＋MA200 で市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / MonitoringDB（永続化レイヤ）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 読み書き
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor の束ね（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード

  - execution/
    - reconciler.py — 再起動・照合作業
    - order_manager.py — 注文作成・状態遷移 API
    - order_repository.py — Orders DB 操作（SQLite）（ファイル参照あり）
    - (その他 BrokerFactory, ExecutionEngine 等が含まれる想定)

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケール調整
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力ツール

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 開発 / テストに関する注意点 / ベストプラクティス

- DB のマイグレーションは monitoring_db.init_monitoring_db 内で一部処理（列追加）を行います。既存 DB に互換性のない変更を行う場合は注意してください。
- AI（OpenAI）呼び出しは外部 API を使用するため、API キーの管理・レート制限・エラーハンドリングに注意してください。実装ではリトライ・フェイルセーフ（失敗時はスコア 0.0 等）を取り入れています。
- Paper Trading モードを用意しているため、実際のブローカー API に接続する前に Paper Trading で動作確認を行うことを推奨します。
- .env やシークレット情報はリポジトリに含めないでください（.gitignore で除外すること）。

---

## よく使うコマンドまとめ

- 監視を起動
  ```
  python -m kabusys.run_monitoring
  ```

- 発注エンジンを起動（Paper Trading）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README では開発者が最初に知っておくべきポイントを簡潔にまとめました。必要であれば、個別モジュール（ExecutionEngine、OrderRepository、BrokerAdapter 等）のドキュメントや API 使用例、requirements.txt、デプロイ手順（systemd / Docker / Supervisor など）についても追記できます。どの箇所を詳細化したいか教えてください。