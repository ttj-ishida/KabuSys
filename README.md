# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ユーティリティ、LLM を使ったニュースセンチメント等のモジュールを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買フレームワークです。

- シグナル → ポートフォリオ構築 → 発注までの ExecutionEngine
- 注文管理・リコンシリエーション（再起動時の自動復旧）
- 監視サブシステム（CPU/メモリ/Disk、データ鮮度、滞留注文、ドローダウン監視）
- LINE 経由のアラート通知
- Paper Trading（本番 DB と分離したモード）
- DuckDB を用いたファクター計算・研究モジュール
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP / レジーム判定
- Streamlit ダッシュボードと検証レポート生成ツール

---

## 主な機能一覧

- execution
  - ExecutionEngine（発注ループ、リスク管理、OrderManager）
  - Reconciler（再起動後の状態同期）
- monitoring
  - SystemMonitor（プロセス生存・CPU/Memory/Disk・データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限検出、ダッシュボード更新）
  - KillSwitch（条件に応じて停止フラグを書き込み、Engine を停止）
  - AlertManager（LINE へプッシュ通知）
  - Streamlit ダッシュボード（監視データ可視化）
- ai
  - news_nlp（ニュース記事を LLM でスコアリングして ai_scores に書込）
  - regime_detector（MA とマクロセンチメントで market_regime を判定）
- research
  - factor_research（Momentum / Volatility / Value 等のファクター計算）
  - feature_exploration（将来リターン計算・IC 評価・統計サマリー）
- tools
  - paper_verification_report（Paper Trading の検証レポート生成）

---

## 必要条件（推奨）

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ）
- ネットワークアクセス（LINE、OpenAI を使う場合）

（requirements.txt は本リポジトリに含まれていない想定のため、上記パッケージを仮想環境にインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリへ移動
2. 仮想環境を作成・有効化して依存パッケージをインストール
3. data ディレクトリを作成（必要なファイルは実行時に自動作成されることが多い）
   ```
   mkdir -p data
   ```
4. 環境変数を設定
   - .env / .env.local をプロジェクトルートに置くと、自動でロードされます（OS 環境変数が優先）
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. 実行前に必須の環境変数を確認・設定してください（下記「環境変数」参照）

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔秒（デフォルト: 60）

例 (.env):
```
KABUSYS_ENV=paper_trading
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

注意: Settings モジュールは .env/.env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを避けたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（実行例）

プロジェクトの Python パッケージ名は `kabusys`（src/kabusys）。モジュールとして起動できます。

- Execution Engine（発注エンジン）起動
  - 本番または paper_trading に応じて DB を分離して起動します。
  ```
  python -m kabusys.run_execution
  ```
  - 起動条件:
    - `data/stop_requested.flag` が既に存在する場合は起動しません（停止済み扱い）。
    - 実行中は PID ファイル（デフォルト: data/execution.pid）が作成されます。
  - 停止:
    - 外部から `data/stop_requested.flag` を作成すると、実行ループは検知して停止します。
    - KillSwitch（監視サブシステム）が `data/kill.flag` を書き込むと停止対象になります。

- Monitoring（SystemMonitor の単独起動）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）。例:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開き、ダッシュボードを表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 引数 `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も使用できます。

- AI / リサーチ機能の呼び出し（ライブラリとして）
  - 例: ニューススコア付け（Python コンソールなどから）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
    ```
  - market_regime のスコア付け:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
    ```

---

## 停止・Kill フラグについて

- 停止フラグ（全体停止）:
  - data/stop_requested.flag（run scripts が参照）
  - このファイルが存在すると run_execution/run_monitoring はループを抜けて終了します。
- Kill Switch:
  - 監視ロジック（RiskMonitor 等）が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。
  - ExecutionEngine 起動時に kill.flag が存在すると起動を拒否します。起動中もループで検出して停止します。
- フラグの削除:
  - 手動でファイルを削除してください（例: rm data/kill.flag）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env ロードと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py, execution_engine.py, reconciler.py, order_repository.py, broker_factory.py, ...（発注周り）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 層（テーブル作成・マイグレーション含む）
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - kill_switch.py, alert_manager.py, streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - data/ (実行時に使用/作成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - execution.pid, stop_requested.flag, kill.flag

（上記は抜粋です。実際には execution や data 関係にさらにサブモジュールがあります。）

---

## 実装上の注意点 / 運用メモ

- Settings はプロジェクトルートの .env / .env.local を自動ロードします。自動ロード順は OS 環境変数 > .env.local > .env。
- Monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（デフォルト 60 秒）。不正値（0 以下・非整数）は無視されデフォルトにフォールバックします。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離された SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- OpenAI / LINE など外部 API を使う処理は、API キー未設定時や API エラー時にフェイルセーフ（警告ログやスキップ）を行う設計ですが、本番運用時は API 制限や料金に注意してください。
- Process priority / CPU affinity の設定には psutil を使用しています。アクセス権限や OS により設定が失敗する場合があります（警告ログのみ）。

---

README は必要に応じてプロジェクト特有の実行スクリプト、requirements.txt、.env.example、運用手順書（起動順序、監視・障害対応フロー）を追記してください。必要であれば README に記載する起動コマンドやサンプル .env をさらに具体化します。