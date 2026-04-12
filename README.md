# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群（KabuSys）の一部実装です。ここではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール群です（コードベースの一部を抜粋・実装）：

- 自動売買の実行エンジン（ExecutionEngine の起動スクリプト）
- 実行・監視インフラ（System / Trade / Risk Monitor、Monitoring DB、Kill Switch、アラート）
- ポートフォリオ構成：候補選定、重み計算、リスク調整、ポジション決定
- 研究用モジュール：ファクター計算（Momentum / Volatility / Value）、特徴量解析（IC, forward returns 等）
- AI を利用したニュースセンチメント（OpenAI を利用）・市場レジーム判定
- 運用ツール：Paper Trading 検証レポート、Streamlit ダッシュボード 等

設計上の方針として、研究系・AI 系は本番口座 API へアクセスせずに DuckDB / ローカルデータのみで完結するようになっています。また、Paper Trading モードでは本番 DB と完全分離されます。

---

## 機能一覧（抜粋）

- 実行 / 監視
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV に応じて本番/ペーパー切替）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine：System / Trade / Risk Monitor を統合してポーリング・アラート送信
  - MonitoringDB：監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）永続化（SQLite）

- モニタリング / アラート
  - SystemMonitor：CPU / メモリ / ディスク / プロセス PID / データ鮮度を監視
  - TradeMonitor：滞留注文、約定価格の異常を検出
  - RiskMonitor：ドローダウン、ポジション上限を監視しリスクイベントを記録
  - KillSwitch：閾値超過時に flag ファイルを書き ExecutionEngine に停止シグナル
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウンあり）

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額 / スコア加重配分
  - セクター集中制限の適用
  - リスクベース / 等配分に基づく株数計算（単元株丸め、aggregate cap）

- 研究
  - ファクター計算（momentum / volatility / value）
  - 将来リターン calc_forward_returns、IC 計算、統計サマリー

- AI
  - news_nlp.score_news：raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込み
  - regime_detector.score_regime：ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成してレジーム判定

- ツール
  - tools/paper_verification_report.py：Paper Trading ログを集計して PASS/FAIL レポートを生成
  - monitoring/streamlit_dashboard.py：Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を表示）

---

## 必要な依存ライブラリ（主なもの）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit
- （標準ライブラリ: sqlite3, argparse, logging, datetime, pathlib など）

pip 等でインストールしてください。例：
```
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主要項目）

Settings クラスは環境変数またはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

- KABUSYS_ENV: 起動環境
  - 有効値: `development`（デフォルト）, `paper_trading`, `live`
  - `paper_trading` の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に注文履歴を記録

- DB / パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）※Monitoring は常に本番 sqlite_path を使用
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag ファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする場合は "1"

- Paper Trading 固有
  - PAPER_FILL_MODE: MockBrokerClient の約定モード（`instant`（デフォルト） / `partial` / `never` / `reject`）

- モニタリング閾値
  - CPU_THRESHOLD_PCT（デフォルト: 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト: 85.0）
  - DISK_THRESHOLD_PCT（デフォルト: 90.0）

- ログ / その他
  - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
  - JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD: 必須（kabu API 用）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用
  - OPENAI_API_KEY: AI モジュール（news_nlp / regime_detector）用

- 監視ポーリング間隔
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）。1以上の整数を指定。0以下または不正値は 60 にフォールバック。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は主要パッケージを個別にインストール（上記参照）。

4. 環境変数設定
   - プロジェクトルートに `.env` を作成して必要な変数を設定してください。
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
   - 自動読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必要なデータフォルダを作成
   ```
   mkdir -p data
   ```

6. 初回起動では monitoring DB のテーブルは実行スクリプトが自動で作成します（init_monitoring_db が呼ばれます）。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動
  - 本番 / 開発 / PaperTrading は KABUSYS_ENV によって切替
  - Paper Trading の場合は PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  ```
  # 例: 開発（デフォルト）
  python -m kabusys.run_execution

  # 例: Paper Trading
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続して ExecutionEngine を起動します。起動時に監視テーブルが存在することを保証します。

- 監視ループ起動
  ```
  # デフォルト（60秒間隔）
  python -m kabusys.run_monitoring

  # ポーリング間隔を上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  run_monitoring は SystemMonitor を定期実行し、system_status / risk_logs 等を記録します。MONITOR_POLL_INTERVAL は 1 以上の整数を指定してください（不正値は 60 秒にフォールバック）。

- Streamlit ダッシュボード（read-only）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  monitoring DB を読み取り専用で開き、Overview / Positions / Orders / System のタブを表示します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから呼ぶ例）
  - ニュース NLP（センチメントスコア）
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="OPENAI_KEY")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="OPENAI_KEY")
    ```

  ※ OpenAI API を使用するため OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバック（失敗時は中立値）を含むフェイルセーフ実装です。

---

## 運用上の注意

- Monitoring は run_monitoring を常時稼働させることを想定しています。監視が無いと ExecutionEngine の異常を検知できません。
- KillSwitch は kill.flag ファイルを書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時などに kill.flag の存在を確認して対処する設計になっています。
- Paper Trading は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- process priority / CPU affinity 設定は psutil を用いて行いますが、権限やプラットフォームによっては設定がスキップされ警告が出ます。
- DuckDB / SQLite のバージョンや executemany の挙動に依存する実装箇所があるため、運用環境では互換性に注意してください（コード内に互換性対策が記載されています）。

---

## ディレクトリ構成（主要ファイル）

以下はこの README に対応するコードベースの主要ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — Monitoring DB（SQLite）永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...（Broker API / Engine 実装等）
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
  - tools/
    - __init__.py
    - paper_verification_report.py

（上記は抜粋です。詳細はソースツリーを参照してください）

---

## 贡献 / 開発メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行います。テストや CI で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマのマイグレーションは簡易的に init_monitoring_db 内で行っています（列追加など）。
- AI 関連の外部呼び出しはリトライ・フォールバックを行う設計ですが、API キー管理やレート制限には注意してください。

---

必要に応じて README に追記します。開発環境のセットアップ手順（requirements.txt、Dockerfile、systemd unit など）が必要であれば教えてください。