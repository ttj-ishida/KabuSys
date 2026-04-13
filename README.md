# KabuSys

日本株自動売買システムのモジュール群（ライブラリ / 実行スクリプト / 監視ツール群）

このリポジトリは、発注エンジン・モニタリング・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含む設計済みコードベースです。README はプロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は以下：

- シグナル → 発注 → 注文管理 を行う Execution エンジン
- システム稼働性・注文挙動・リスク（ドローダウン・保有数上限）を監視する Monitoring
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索
- ニュースを LLM（OpenAI）で評価して銘柄ごとのセンチメントを算出する AI モジュール
- Paper Trading（検証用環境）を分離して実行可能
- 簡易ダッシュボード（Streamlit）と各種ツール（検証レポート生成など）

設計上の注意点：
- 環境変数 / .env ファイルから設定を読み込む（自動読み込み：プロジェクトルートに .env/.env.local があれば読み込む）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- 監視系（Monitoring）は環境に依存せず本番の sqlite_path を使用する設計（run_monitoring.py）。
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は発注先がモックとなり、専用の SQLite（デフォルト `data/paper_trading.db`）に分離される（run_execution.py）。

---

## 機能一覧

- Execution（発注系）
  - OrderManager、Reconciler（起動時リコンシリエーション）
  - RiskManager（発注前チェック）
  - Broker クライアントは環境に応じて実実装 / モックを切替
- Monitoring（監視系）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション数の監視（KillSwitch による停止指示生成）
  - AlertManager：LINE Push による通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（簡易 UI）
  - monitoring DB 層（SQLite）と永続化 API（MonitoringDB）
- Portfolio（配分・ポジション決定）
  - 候補選定、等重／スコア加重、セクター上限、レジーム乗数、ポジションサイズ計算（単元株丸め・集約キャップ）
- Research（DuckDB ベース）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）/ 統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメント (ai_scores) を出力
  - regime_detector: ETF の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
  - LLM 呼び出しはリトライ・バリデーション・フェイルセーフ実装あり
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポート出力
  - streamlit_dashboard: Monitoring DB を参照するブラウザダッシュボード

---

## 必要な依存パッケージ（主なもの）

主に以下のパッケージが必要です（バージョンは適宜固定してください）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit
- その他: sqlite3 は標準ライブラリ

（requirements.txt がない場合は手動でインストールしてください。例: `pip install duckdb psutil requests openai streamlit`）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数 / .env ファイル
   - プロジェクトルートに `.env` または `.env.local` を作成して必要な環境変数を設定します。
   - 主要な変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject
     - MONITOR_POLL_INTERVAL（秒、run_monitoring 用）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - 自動読み込みを一時的に無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データディレクトリの準備（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方

以下はよく使う実行例です。

- 監視ループを起動（run_monitoring）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト60秒。
  - 実行：
    ```
    python -m kabusys.run_monitoring
    ```
  - 補足：
    - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用します（監視ログを本番 DB に残す設計）。
    - 起動時にプロセス優先度を "high" に設定しようと試みます（権限やプラットフォームにより無視される場合あり）。

- Execution（発注エンジン）を起動
  - Paper Trading の場合は `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使い、`data/paper_trading.db` に記録します（本番 DB と分離）。
  - 実行：
    ```
    python -m kabusys.run_execution
    ```

- Paper Trading 検証レポート生成（ツール）
  - デフォルト DB: data/paper_trading.db。引数で期間や DB を指定可能。
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- Streamlit 監視ダッシュボード
  - 起動例（read-only で SQLite に接続）:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- AI モジュール（プログラム的に呼ぶ）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または引数で渡す）。
  - 例: news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を渡して使用します（コード内 API を参照）。

---

## 重要な挙動・設計メモ

- .env のパーシングは柔軟な実装（`export KEY=val`、クォート・エスケープ、行内コメントの解釈など）になっています。
- Settings クラスで主要な設定を一元管理（プロパティ経由で型チェック・許容値検証を行います）。
  - KABUSYS_ENV の有効値は: `development` / `paper_trading` / `live`
  - PAPER_FILL_MODE の有効値: `"instant" | "partial" | "never" | "reject"`
- run_monitoring は `MONITOR_POLL_INTERVAL` の値が不正な場合、デフォルト 60 秒にフォールバックします。
- MonitoringDB は起動時にテーブル / インデックスの作成（冪等）と簡易マイグレーション（カラム追加）を行います。
- KillSwitch は `data/kill.flag` への書き込みで ExecutionEngine 停止を指示します。Kill flag は冪等的に作成され、必要に応じて `clear()` で削除できます。Execution 起動時にフラグをクリアするかは設定で制御可能（Settings.kill_flag_clear_on_start）。
- Process priority / CPU affinity: psutil を使い Windows / POSIX (Linux, macOS 等) の差分を吸収します。設定できない場合は警告ログでスキップします。

---

## ディレクトリ構成（主要ファイル）

以下はソースの簡易ツリー（主要ファイルのみ抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env の読み込みと Settings
  - run_monitoring.py                — SystemMonitor ポーリングループ起動
  - run_execution.py                 — ExecutionEngine 起動スクリプト（paper_trading に対応）
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成ツール
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続化層（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker / engine / order_repository 等の実装ファイル)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/  (期待されるデータディレクトリ、実行時に使用される)
    - data/kabusys.duckdb (デフォルト DUCKDB)
    - data/monitoring.db     (デフォルト SQLite for monitoring)
    - data/paper_trading.db  (paper trading 用 SQLite)

---

## 開発 / テスト時のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行われます。パッケージ配布後の動作を考慮して __file__ 起点で探索しているため、カレントワーキングディレクトリに依存しない点に注意。
- モックブローカー／テスト用 DB を使う場合は `KABUSYS_ENV=paper_trading` を使用して本番 DB を汚さないようにしてください。
- OpenAI を使う機能は API キーが必須です。ローカルテスト時はテスト用のパッチ（unittest.mock）で _call_openai_api を置き換えることを想定しています。
- Streamlit ダッシュボードは SQLite を read-only で開くことを推奨（起動時に read-only URI を渡している実装例あり）。

---

## ライセンス / 貢献

（この README にはライセンス条項や貢献フローは含んでいません。必要に応じてプロジェクトルートに LICENSE / CONTRIBUTING.md を追加してください。）

---

README に書き足してほしい点（例：環境変数のサンプル .env.example、requirements.txt、動作確認手順、Docker 起動手順など）があれば教えてください。必要に応じて追補を作成します。