# KabuSys

日本株自動売買システムの一部コンポーネント群（ポートフォリオ構築、リサーチ、監視、Execution 起動スクリプト、AI ニュース解析など）。

以下はリポジトリ内の主要機能と使い方の概要ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な目的は以下。

- シグナルに基づくポートフォリオ構築、位置サイズ算出
- ファクター計算や特徴量解析などのリサーチユーティリティ（DuckDB を想定）
- OpenAI を用いたニュースの自然言語センチメント解析（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 実行エンジン（ExecutionEngine）起動スクリプト（本番／PaperTrading 切替）
- 監視（MonitoringEngine）とアラート（LINE Push）・kill switch／flag を使った停止シグナリング
- Streamlit ベースの監視ダッシュボード
- Paper Trading の検証レポート生成ツール

設計上の注記：
- DuckDB と SQLite を併用（prices_raw 等の分析は DuckDB、監視ログ等は SQLite）。
- 環境分離：`KABUSYS_ENV=paper_trading` のときはモックブローカーを使い、paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）に記録される。
- .env（および .env.local）から環境変数を自動ロード（プロジェクトルート検出: .git または pyproject.toml）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 機能一覧（抜粋）

- portfolio
  - 候補選定（select_candidates）
  - 等金額 / スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - 単元丸め・投資額制限を考慮した株数算出（calc_position_sizes）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続を受ける純粋関数）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ

- ai
  - news_nlp.score_news: raw_news を OpenAI に送り銘柄ごとの sentiment / ai_score を ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を作成

- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（DB への永続化を含む）
  - MonitoringEngine（ポーリングループ）
  - AlertManager（LINE push）
  - KillSwitch（flag ファイルによる ExecutionEngine 停止）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- execution（起動用スクリプト）
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV に応じて本番 or paper_trading を分離）
  - run_monitoring.py: SystemMonitor の単独ループ（ポーリング）

- tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

---

## 必要な前提 / 依存パッケージ（代表例）

この README はコードから推測した依存を記載します。プロジェクトには pyproject.toml や requirements.txt があればそちらを参照してください。

- Python 3.9+
- duckdb
- psutil
- requests
- openai（OpenAI Python SDK）
- streamlit（ダッシュボード用）
- その他 SQLite は標準ライブラリで利用可能

インストール例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

必須/期待される環境変数（一部）：

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag ファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60。1 未満の値は無効でデフォルトにフォールバック）

.env / .env.local を利用できます。config.Settings モジュールで自動ロードされます（プロジェクトルート検出が成功した場合）。OS 環境変数は .env によって上書きされないよう保護されます。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートに移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt がない場合は上記の主要パッケージを直接インストール）
4. .env を作成（プロジェクトルート）。最低限必要な値（例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   OPENAI_API_KEY=your_openai_key
   LINE_CHANNEL_ACCESS_TOKEN=（通知を使う場合）
   LINE_USER_ID=（通知先）
   ```
   - .env.local を使ってローカル専用の上書きも可能（自動ロードは .env → .env.local の順、OS 環境は保護）。

5. 必要に応じて data ディレクトリを作成
   ```
   mkdir -p data
   ```

---

## 使い方（実行例）

実行コマンドはプロジェクトの構成や実行方法により変わります。ここでは module 実行 / スクリプト実行の例を示します。

- Monitoring（システム監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  あるいは
  ```
  python src/kabusys/run_monitoring.py
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）
  - stop フラグ: `data/stop_requested.flag` を作成するとループは終了します
  - 監視は Settings.sqlite_path（環境にかかわらず本番 sqlite_path）を使用して DB にログを書きます

- ExecutionEngine 起動
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に保存して本番 DB と分離します
  - 実行中に `data/stop_requested.flag` が作られるとエンジンに停止要求が送られます
  - PID ファイルは `data/execution.pid`（デフォルト）へ書き込まれます

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - データベースへは read-only モードで接続します（監視プロセスが先に DB を作成/書き込みしていることが前提）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite ファイルを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定できます

- AI スコアリング／レジーム判定（プログラムから呼ぶ）
  - news スコアを取得して書き込む:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 4, 1), api_key="...")  # 必要に応じて api_key 引数
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="...")
    ```

---

## 注意事項 / 運用メモ

- Paper Trading と本番 DB は明示的に分離されます（paper_trading 環境は別 SQLite を使用）。本番データを誤って上書きしないよう注意してください。
- OpenAI の呼び出しは API エラー（429、タイムアウト、5xx）に対してリトライ実装がありますが、API キーが未設定のときは例外が発生します。`OPENAI_API_KEY` をセットしてください。
- process priority / CPU affinity の設定は psutil を用いて行います。権限不足により設定できない場合は警告ログが出てスキップされます。
- Monitoring の `MONITOR_POLL_INTERVAL` は正の整数で指定してください。不正な値ではデフォルト（60秒）にフォールバックします。
- stop / kill フラグは `data/stop_requested.flag`（run_monitoring/run_execution の停止）および `data/kill.flag`（KillSwitch による Execution 停止）等のファイル存在で制御します。flag の書き込みは冪等です。

---

## ディレクトリ構成（主要部分、抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト（paper_trading 切替）
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI）→ ai_scores 書き込み
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — SQLite モデル層（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py             — LINE Push 実装
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (他に broker_factory, execution_engine, order_repository 等が参照されます)
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用デフォルト)
  - kabusys.duckdb (デフォルト)
  - execution.pid, stop_requested.flag, kill.flag など

---

## 追加情報 / トラブルシュート

- DB が見つからない／開けない（Streamlit のエラー）
  - 監視プロセス（MonitoringEngine）を先に起動して DB とテーブルを初期化してください。
  - streamlit コマンドに渡す `-- --db PATH` を正しく指定してください。

- psutil による優先度設定に失敗する（Permission エラー）
  - 管理者権限が必要な場合があります。失敗してもプロセスは続行されます（警告ログ）。

- OpenAI レスポンスが不正（JSON パースエラーなど）
  - モデル返却の形式が想定外だった場合はログに警告が出て、その銘柄のスコアはスキップされます。再試行やプロンプト調整を検討してください。

---

この README はコードベース（src/kabusys 以下）を参照して作成しています。運用上の設定や追加の起動オプションはプロジェクトの他ファイル（pyproject.toml / docs / deploy スクリプト等）を参照してください。必要であれば README に含めるサンプル .env.example やデプロイ手順のテンプレートも作成します。必要なら指示ください。