# KabuSys

日本株自動売買システムのコードベース README。  
このファイルはリポジトリに含まれる主要スクリプト・モジュールの概要、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ／監視モジュール群を集めたパッケージです。主な責務は以下のとおりです。

- 注文の生成・送信・状態管理（Execution）
- モニタリング（システム稼働状況、注文の滞留や約定異常、リスク監視）
- ポートフォリオ構築（銘柄選定・重みづけ・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI）
- ユーティリティツール（paper trading 検証レポート、Streamlit ダッシュボード等）

設計上の方針として、データ取得・バックエンド呼び出しを明示的に分離し、DB（SQLite / DuckDB）を用いたローカル永続化を行います。Paper trading のモードは本番 DB と完全分離されるよう設計されています。

---

## 主な機能一覧

- Execution
  - 発注フロー（OrderManager）・ブローカー抽象化（BrokerClientFactory）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス死活・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限検出とログ登録
  - KillSwitch：条件に基づく停止フラグ（data/kill.flag）書き込み
  - AlertManager：LINE Push による通知（クールダウン機能付き）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定・等重／スコア重み・リスクベースのポジションサイジング
  - セクター制約やレジーム乗数の適用
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算・IC（Information Coefficient）分析・統計サマリ
- AI
  - news_nlp：ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores に書き込み
  - regime_detector：ETF（1321）MA とマクロニュースの LLM センチメントを合成し市場レジーム判定
- ツール
  - paper_verification_report：Paper Trading DB から検証レポートを出力
  - streamlit_dashboard：監視 DB を可視化

---

## セットアップ手順

前提：
- Python 3.10+ を想定（typing の Union | などを使用）
- OS により一部機能（プロセス優先度、CPU affinity）の挙動が異なります

1. リポジトリをクローンする（省略）

2. 必要な Python パッケージをインストール
   例（最低限の依存）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   実際のプロジェクトでは requirements.txt がある想定です。なければ上記パッケージを追加してください。

3. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動環境読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を使う機能で必須
   - KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE — Paper trading の fill モード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite path（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 / 本番用 monitoring DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH — PID ファイル path（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — kill.flag path（デフォルト: data/kill.flag）
   - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

4. データディレクトリの作成
   - デフォルトの DB 保存先（data/）などを作成しておくと便利です:
     ```
     mkdir -p data
     ```

---

## 使い方（主要スクリプト）

以下は主な実行例です。各スクリプトはパッケージモジュールとして実行できます。

- 監視（Monitoring）を起動
  - デフォルトはポーリング間隔 60 秒
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（1 以上、無効値はデフォルトにフォールバック）
  ```
  python -m kabusys.run_monitoring
  ```
  - 実行時、プロセス優先度を "high" に設定し、monitoring 用 SQLite を開いてポーリングを行います。
  - 監視は Settings.sqlite_path を使用（KABUSYS_ENV に関係なく本番 sqlite_path を参照）。

- 実行エンジン（ExecutionEngine）を起動
  - Paper trading モード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    Paper trading の場合は MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に保存されます（本番 DB と完全に分離）。
  - 本番 / 通常実行:
    ```
    python -m kabusys.run_execution
    ```

- Streamlit ダッシュボード（監視）を起動
  - 監視 DB を読み取り専用で表示します
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  - SQLite DB の指定: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプション
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニュース評価・レジーム判定）
  - OpenAI API を利用するため `OPENAI_API_KEY` を設定してください。
  - モジュール API として呼び出す設計（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - 実行時は API キー解決を引数または環境変数で行います。API 呼び出しはリトライロジック・フェイルセーフ実装済みです。

---

## 主要設定の説明（Settings）

設定は `kabusys.config.Settings` へマッピングされています。重要な項目は次の通り：

- KABUSYS_ENV: "development" | "paper_trading" | "live"
  - paper_trading の場合、run_execution は paper_sqlite_path を使います
- PAPER_FILL_MODE: paper trading における約定モード（"instant","partial","never","reject"）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH: DB ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: PID／停止フラグファイルパス
- CPU/MEM/DISK 閾値: 監視動作の閾値（環境変数から上書き可）
- 自動 .env ロード:
  - リポジトリルート (.git / pyproject.toml) を起点に `.env` / `.env.local` を読み込みます
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

---

## 注意・設計メモ

- プロセス優先度設定:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます。Windows / POSIX に対する互換層が実装されていますが、権限や OS により失敗する場合は警告ログになりスキップされます。
- Monitoring DB マイグレーション:
  - `init_monitoring_db()` は冪等にテーブルを作成し、既存 DB に `peak_value` や `latency_ms` カラムが無ければ追加する軽微なマイグレーション処理を行います。
- データ鮮度チェック:
  - SystemMonitor は DuckDB を参照して prices_daily の最終日付を取得し、鮮度判定を行います（デフォルト許容: 3 日以内）。
- Kill Switch:
  - RiskMonitor の結果に応じて `data/kill.flag` を書き、ExecutionEngine に停止指示を出す仕組みがあります（冪等、既存フラグの再書き込みは行いません）。
- Paper Trading の分離:
  - Paper trading は本番 DB と完全に分離されるように設計されています（`PAPER_TRADING_SQLITE_PATH` を使用）。
- LLM（OpenAI）利用時のフェイルセーフ:
  - API 呼び出しはレート制限・接続エラー・サーバーエラーに対してバックオフリトライを行い、最終的に失敗しても処理を停止させず安全側のデフォルト（例: macro_sentiment=0.0）で続行します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - run_monitoring.py  — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py     — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みロジック
    - alert_manager.py      — LINE push 通知ラッパー
    - monitoring_engine.py  — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py— Streamlit による可視化
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他：broker_factory, execution_engine, order_repository 等)
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
    - news_nlp.py         — ニュースの LLM センチメント評価
    - regime_detector.py  — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py  — 優先度 / CPU affinity ヘルパ

（注）上記はリポジトリに含まれる主要なモジュールの抜粋です。細かい補助モジュールや execution/broker 実装は別ファイルにあります。

---

## よくある質問 / トラブルシューティング

- Q: OpenAI が使えない（API キー未設定）
  - A: `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時に api_key を渡してください。API エラー時はフェイルセーフでスコアが 0.0 になる場合がありますが、API キーが必須の処理は例外を投げます。

- Q: Monitoring が DB を開けない / read-only で開けない
  - A: Streamlit は read-only URI モードで DB を開こうとします。DB が存在しない場合は MonitoringEngine を起動して最初にテーブルを作成してください（init_monitoring_db が実行されます）。

- Q: MONITOR_POLL_INTERVAL を設定したが無視される
  - A: 値は環境変数 `MONITOR_POLL_INTERVAL`（秒）で指定。1 未満や不正な文字列は警告ログ出力の上デフォルト 60 秒にフォールバックします。

---

## 開発メモ / 貢献

- テスト可能性を考慮して各種 API 呼び出しはラップされ、テスト時に patch して置換しやすい設計になっています（例: news_nlp._call_openai_api のモックなど）。
- DuckDB / SQLite に対する SQL は内部ドキュメント（コメント）に沿っており、research モジュールは DB の prices_daily / raw_financials テーブルのみを参照します。
- 変更を加える場合は、既存の DB マイグレーションロジック（monitoring_db.init_monitoring_db）を考慮して後方互換性を維持してください。

---

以上がこのコードベースの README です。必要であればサンプル .env のテンプレートや requirements.txt、Dockerfile、systemd サービスファイルの例も追記できます。どれを追加しますか？