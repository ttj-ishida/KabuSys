# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の主要機能を持ち、小さなプロダクション／ペーパートレーディング環境で動作することを想定しています。

> バージョン: 0.1.0

---

## プロジェクト概要

- 株式のシグナル生成 → ポートフォリオ構築 → 注文管理 → 実行（ExecutionEngine） の一連の流れをサポートします。
- 監視（Monitoring）モジュールによりシステム状態・注文状況・リスクを定期的にチェックし、アラート送信や自動停止（kill）を行います。
- DuckDB を使ったリサーチ（ファクター計算・特徴量分析）、OpenAI を用いたニュース NLP スコアリング、市場レジーム判定などの機能を備えます。
- Paper Trading モードは本番 DB と分離された専用 SQLite を使用し、fill の挙動も切り替えられます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・注文状態管理・リスク管理・リコンシリエーション）
  - Broker クライアント切替（実口座 / Mock（paper_trading））
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、PIDチェック、データ鮮度確認）
  - TradeMonitor（滞留注文、約定異常価格チェック）
  - RiskMonitor（ドローダウン・ポジション上限の監視）
  - KillSwitch（閾値到達時に停止フラグ書き込み）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio construction
  - 候補選定・重み計算・単元丸め・リスク調整（等金額・スコア加重・リスクベース）
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の統計処理
- AI
  - news_nlp: raw_news を LLM によるセンチメント分析 → ai_scores に格納
  - regime_detector: ETF MA とマクロセンチメントの合成によるレジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## 必要条件（例）

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリで利用）

pip でのインストール例（仮の requirements）:
```
pip install duckdb psutil openai requests streamlit
```

必要に応じてプロジェクト固有の requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージを配置
   - ソースは `src/kabusys/` 以下にあります。適切に PYTHONPATH を設定するかパッケージとしてインストールしてください。

2. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
     - LOG_LEVEL: "DEBUG" | "INFO" | ...
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値 など

   - .env のパースは強化されており、シングル/ダブルクォートや export プレフィックスにも対応します。

3. データディレクトリの準備
   - デフォルトで使う DB / フラグファイル等を置く `data/` ディレクトリを作成してください。
   - 例:
     ```
     mkdir -p data
     touch data/monitoring.db data/kabusys.duckdb
     ```

---

## 使い方（起動 / 実行例）

- 監視プロセス起動（monitoring ポーリング）
  - コマンド:
    ```
    python -m kabusys.run_monitoring
    ```
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。1 未満や不正な値はデフォルトにフォールバックします。
    - Monitoring モジュールは KABUSYS_ENV に関わらず本番の sqlite_path（Settings.sqlite_path）を使います。
    - プロセス優先度を "high" に設定しようとします（psutil による操作。権限により失敗する場合は警告を出します）。
    - 停止はプロジェクトルートの data/stop_requested.flag の存在で検知します（ファイルを置くとループを終了）。

- 実行エンジン起動（ExecutionEngine）
  - コマンド:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading を設定した場合、MockBrokerClient を使い、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と完全に分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中の停止は同じく data/stop_requested.flag の作成によりトリガーします。
    - 実行時は data/execution.pid に PID を書きます（pid_file のパスは Settings で指定可能）。

- Streamlit ダッシュボード（監視 DB を可視化）
  - コマンド:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 補足:
    - 読み取り専用で DB を開きます（存在しない場合はエラー表示）。
    - Dashboard, Positions, Orders, System タブを提供。

- Paper Trading 検証レポート
  - コマンド例:
    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```
  - 出力:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を表示します。
  - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH による上書き可）

- AI 関連機能
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols から記事を集約して OpenAI に投げ、ai_scores に書き込みます。
    - OPENAI_API_KEY（もしくは引数で api_key） が必要です。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA200 乖離とマクロニュースによる LLM センチメントを合成して market_regime テーブルに書き込みます。
    - OPENAI_API_KEY が必要です。

---

## 停止・Kill の仕組み

- 手動停止（全体監視プロセス / 実行エンジン共通）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全に終了または停止します。

- 自動停止（監視が起こす停止）
  - KillSwitch（監視）により基準超過（ドローダウン・ポジション数等）が検出されると、Settings.kill_flag_path（デフォルト data/kill.flag）へ理由文字列を書き込みます。ExecutionEngine はこの kill.flag を検出して停止する設計です。
  - 起動時に KILL_FLAG_CLEAR_ON_START が "1" のときは起動時に kill.flag を自動でクリアするオプションがあります。

---

## 設定の要点（Settings）

- KABUSYS_ENV の値:
  - development, paper_trading, live
  - paper_trading の場合、Execution は paper_sqlite_path を使用し Mock ブローカーで動作します。
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID / フラグ:
  - PID_FILE_PATH: デフォルト data/execution.pid
  - KILL_FLAG_PATH: デフォルト data/kill.flag
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / Settings
- run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py     — Paper Trading 検証レポート
- ai/
  - news_nlp.py                      — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py               — 市場レジーム判定（OpenAI）
- monitoring/
  - __init__.py
  - monitoring_db.py                 — SQLite 永続化層 / 初期化
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
  - ... (Broker / Engine / OrderRepository 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください。）

---

## .env 例（抜粋）

例として `.env` に最低限必要なキーを置く：
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
MONITOR_POLL_INTERVAL=60
```

---

## 注意事項 / 実運用メモ

- Monitoring は監視 DB（SQLITE_PATH）を使います。データ破損を避けるためバックアップやローテーションを検討してください。
- OpenAI API を使う機能は API 利用料が発生します。バッチサイズ・リトライ戦略は実装されていますが、利用量の管理に注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存・権限依存です。権限不足時は警告を出してスキップします。
- DuckDB を利用した解析は大規模データでも高速ですが、ファイルパスや接続設定に注意してください。
- Paper Trading は本番 DB と分離することを必ず確認してください（PAPER_TRADING_SQLITE_PATH を適切に設定）。

---

## サポート / テスト

- ユニットテストや CI の設定はこの説明に含まれていません。ローカルでの動作確認を行い、必要に応じてユニットテストを追加してください。
- OpenAI 呼び出し部や外部 API 部分はモック可能な設計（テスト時に差し替え）になっています。

---

必要であれば README にサンプル .env.example、依存関係リスト（requirements.txt）、起動 systemd / supervisor サンプルやデバッグ手順を追加できます。追加したい項目を教えてください。