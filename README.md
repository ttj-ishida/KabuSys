# KabuSys

日本株自動売買システムの一部コンポーネント群を含むリポジトリの README です。  
この README はプロジェクトの概要、主な機能、セットアップ手順、起動方法、ディレクトリ構成を日本語でまとめています。

※ 本リポジトリは複数のサブモジュール（実行エンジン、監視、リサーチ、AI 連携など）を含みます。各モジュールは原則として外部サービス（ブローカー API、OpenAI など）やローカル DB（DuckDB / SQLite）に依存します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。本コードベースには以下の機能が実装されています（抜粋）:

- シグナルを受けて発注を行う ExecutionEngine（OrderManager / RiskManager 等）
- 起動時のリコンシリエーション（Reconciler）
- 発注・約定ログやポジションを永続化する監視用 SQLite（MonitoringDB）
- システム状態・注文滞留・リスク監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- LINE を用いたアラート通知（AlertManager）
- ニュースを LLM（OpenAI）によりスコアリングする AI モジュール（news_nlp）
- 市場レジーム判定（regime_detector）
- ファクター計算 / 研究用ユーティリティ（research）
- ポートフォリオ構築ロジック（候補選定・重み付け・単元丸めなど）

設計上の特徴：
- DuckDB をデータ分析（時系列価格・財務データ）に使用
- SQLite を監視／発注ログの永続化に使用
- Paper trading（シミュレーション）時は本番 DB と分離されるよう設計
- OpenAI API 呼び出しはフェイルセーフ（失敗時はスキップ／フォールバック）で実装

---

## 主な機能一覧

- Execution
  - Signal 処理 → ブローカー発注（OrderManager / ExecutionEngine）
  - リコンシリエーション（再起動後の注文照合）
  - 発注状態の堅牢な永続化（クラッシュ耐性を考慮した二相的な永続化）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視と履歴保存
  - 注文滞留（stale order）検知、約定異常価格検知
  - ドローダウン監視・ポジション上限監視・kill switch（ファイルによる強制停止）
  - Streamlit による監視ダッシュボード
  - LINE エラート通知（クールダウン付き）
- Research / Data
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースのセンチメント評価（OpenAI を利用、JSON モードで結果整形）
  - マクロニュースと ETF MA200 を合わせた市場レジーム判定
- Utilities
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - 環境変数ローダ（.env / .env.local の自動読み込み）

---

## 依存関係（主な Python パッケージ）

最低限必要なパッケージ例:

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- (標準ライブラリ: sqlite3, logging, datetime など)

インストール例（venv を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

設定は OS 環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う場合に必要（news_nlp / regime_detector）
- KABUSYS_ENV: 起動環境。許容値: development / paper_trading / live（デフォルト: development）
  - paper_trading のときは paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker 動作 ("instant"|"partial"|"never"|"reject")
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例: 最低限必要な .env の例
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
OPENAI_API_KEY=sk-xxxx      # AI 機能を使う場合
KABUSYS_ENV=development
```

---

## セットアップ手順

1. レポジトリをクローンし、Python 仮想環境を作成・有効化する
2. 依存パッケージをインストール（上の pip コマンド参照）
3. プロジェクトルートに `.env` を作成（.env.example を参考に必要変数を設定）
4. DuckDB / SQLite の初期データ（prices_daily / raw_financials など）を用意する（研究・ファクター計算で必要）
   - データの投入は本 README 範囲外（別途 ETL / pipeline 実装を参照）

注意: Settings モジュールはプロジェクトルート（.git または pyproject.toml を含む）を基準に .env を自動読み込みします。自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（起動方法）

このパッケージはスクリプト形式の起動モジュールを持ちます。パッケージとして実行できます。

基本的なコマンド例（プロジェクトルート、仮想環境有効化済み）:

- ExecutionEngine を起動（本番 or paper_trading に応じた DB を使用）:
  ```
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を "high" に試行的に設定します（失敗しても継続）。
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、`data/paper_trading.db` を使用します。
  - PID ファイルを生成します。kill.flag が存在すると起動直後に停止シグナルとして扱うため、`kill_flag_clear_on_start` の設定に応じて削除してから起動してください。

- Monitoring（System / Trade / Risk）を定期実行:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV の影響を受けない設計）。

- Streamlit ダッシュボード（監視結果の可視化）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` 引数で読み取り専用モードの DB を指定できます（デフォルト: data/monitoring.db）。

- AI モジュール（ニューススコアリング / レジーム判定）:
  - news_nlp.score_news と regime_detector.score_regime は DuckDB 接続と target_date を受け取り実行します。OpenAI API を利用するため `OPENAI_API_KEY` の設定が必要です。
  - 直接 CLI スクリプトは提供されていませんが、スクリプトやジョブとしてこれらの関数を呼び出して利用できます。

---

## 実運用上の注意点

- kill.flag:
  - `KILL_FLAG_PATH`（デフォルト data/kill.flag）に文字列を書き込むことで ExecutionEngine に停止シグナルを与えます。KillSwitch は既存ファイルの再書き込みを行わないため冪等。
  - ExecutionEngine 起動時に `kill_flag_clear_on_start` が設定されていると、起動時に flag をクリアする挙動を想定しています（Settings を確認）。

- PID ファイル:
  - ExecutionEngine は pid ファイルを利用して稼働チェックを行います。system monitor は stale PID を検出すると削除し、リスクログに記録します。

- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合、ブローカーはモッククライアントを利用し、DB は `PAPER_TRADING_SQLITE_PATH` で分離されます。実口座に誤って注文が送られないよう隔離されています。

- OpenAI API:
  - API 呼び出しはレートリミット・ネットワーク障害に対して指数バックオフでリトライしますが、最終的に失敗した場合はスコアを生成せずフェイルセーフで継続します。
  - news_nlp / regime_detector は出力を厳密 JSON で期待しており、レスポンスのバリデーションを行います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールのサマリです。

- kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数・.env 読み込み/検証
  - run_execution.py
    - ExecutionEngine の起動スクリプト
  - run_monitoring.py
    - MonitoringEngine の起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの LLM によるスコアリング
    - regime_detector.py   — 市場レジーム判定（MA200 + マクロセンチメント）
  - execution/
    - execution_engine.py  — ExecutionEngine（シグナル処理・プッシュドレイン）
    - order_manager.py     — OrderManager（発注ワークフロー）
    - reconciler.py        — リコンシリエーション
    - order_repository.py  — 注文永続化（SQLite） ※本 README のコード抜粋に含まれますが詳細はリポジトリ参照
    - ...（broker_api, broker_factory, risk_manager 等）
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ初期化 / 永続化 API（MonitoringDB）
    - monitoring_engine.py — 複数 Monitor を束ねるポーリングエンジン
    - system_monitor.py    — システム状態とデータ鮮度の監視
    - trade_monitor.py     — 注文滞留 / 約定異常監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 管理
    - alert_manager.py     — LINE Push 通知
    - streamlit_dashboard.py — Streamlit ベースの可視化ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py   — 単元丸め・投下株数計算
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/                 — デフォルト DB 等（git 管理外想定）
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

（詳細はリポジトリのファイルツリーを参照してください）

---

## 開発メモ / トラブルシューティング

- .env 自動読み込み:
  - Settings モジュールはプロジェクトルートを .git または pyproject.toml で検出し、`.env` と `.env.local` を自動読み込みします。OS 環境変数が優先されます。
  - テスト時などで自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- MONITOR_POLL_INTERVAL:
  - `MONITOR_POLL_INTERVAL` は整数で秒数を指定します。1 未満または不正値はデフォルト 60 秒にフォールバックします。

- OpenAI 呼び出しのテスト:
  - news_nlp と regime_detector の内部で API 呼び出し関数は分離されており、ユニットテスト時はパッチして差し替え可能です（例: unittest.mock.patch）。

- 権限や OS 依存:
  - process priority / cpu affinity の設定は OS によって挙動が異なり、権限不足で失敗することがあります（警告ログ出力でスキップされます）。

---

## 最後に

この README はコードベースに含まれるコンポーネントの概要と基本的な使い方をまとめたものです。詳細な API 仕様や DB スキーマ、ETL（price データ投入）手順は別文書（ドキュメント）やコード内ドキュメントを参照してください。必要であれば、各モジュール別の詳細 README を追加で作成できます。