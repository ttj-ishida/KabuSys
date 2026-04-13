# KabuSys — 日本株自動売買システム

このリポジトリは日本株向け自動売買フレームワークの主要コンポーネント群を含みます。  
主に「ExecutionEngine（発注実行）」「Monitoring（監視）」「Research（ファクター計算）」「Portfolio（銘柄選定・配分）」「AI（ニュース NLP / レジーム判定）」などのモジュールで構成されています。

目次
- プロジェクト概要
- 主な機能
- 前提条件（依存）
- セットアップ手順
- 環境変数と設定
- 実行例（使い方）
- ディレクトリ構成（ファイル一覧と説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的とした内部モジュール群です。  
設計上の特徴：
- Execution（発注）と Monitoring（監視）を分離し、監視側から安全に Execution を停止する「kill flag」等の仕組みを備えています。
- DuckDB / SQLite をデータレイヤに使用し、リサーチ（ファクター計算）や AI（ニュースセンチメント / レジーム検出）モジュールを備えます。
- Paper Trading 用の完全分離 DB を用意し、実運用と切り離して検証可能です。
- プラットフォーム依存を抽象化したユーティリティ（プロセス優先度設定、CPU affinity 等）を提供します。

---

## 主な機能（機能一覧）

- Execution（実行）
  - ExecutionEngine、OrderManager、Reconciler 等による発注フローと再同期処理
  - Paper Trading モード（MockBrokerClient を利用し data/paper_trading.db に記録）
  - リスク管理（RiskManager）と注文履歴の永続化

- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク使用率、プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：フラグファイル（data/kill.flag）を書き込んで Execution 停止を促す
  - AlertManager：LINE Messaging API 経由のアラート送信（オプション）
  - Streamlit ダッシュボード（監視情報の可視化）

- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（情報係数）計算、特徴量サマリ

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み付け、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ決定（単元株丸め、投下上限、aggregate cap）

- AI
  - news_nlp：OpenAI を用いたニュースセンチメント付与（ai_scores テーブル）
  - regime_detector：市場レジーム判定（ETF MA200 乖離 + マクロニュースセンチメント）

- Tools
  - Paper Trading 検証レポート生成（paper_verification_report）
  - 各種ユーティリティ群（プロセス優先度設定など）

---

## 前提条件（依存）

- Python 3.10+
- 主な Python パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI / LINE を利用する場合）

インストール例:
```bash
python -m pip install "duckdb" "psutil" "openai" "requests" "streamlit"
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成してアクティベート
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール（上記参照）
4. 設定（環境変数）
   - プロジェクトルートに `.env` / `.env.local` を置くことで環境変数を自動で読み込みます（既存の OS 環境変数は上書きされません。.env.local は上書き可能）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. 必須環境変数（運用に必要）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（optional）: development | paper_trading | live（デフォルト: development）
6. DB 初期化
   - 監視 DB は各起動スクリプト内で init_monitoring_db() が呼ばれます（冪等）。手動で初期化する必要は基本的にありませんが、data フォルダ等を事前に作成しておくと良いです。

---

## 環境変数（主要）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、Execution は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、MockBroker を利用する想定
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE でのアラート送信に必要（未設定時は送信をスキップ）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等（Settings から確認可能）

設定は .env / .env.local に記載できます。自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を検出して行われます。

---

## 実行例（使い方）

- ExecutionEngine を起動（本番／PaperTrading を Settings に応じて切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を HIGH に設定し、DB を接続して ExecutionEngine を実行します。
  - KABUSYS_ENV=paper_trading とすると paper_sqlite_path を使用し MockBrokerClient が選択されます。

- SystemMonitor の単独起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは本番 DB を想定）。

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 読み取り専用で DB を開き、ダッシュボードを表示します。

- Paper Trading 検証レポート（コマンドライン）
  ```bash
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能の利用（例）
  - news_nlp.score_news や ai.regime_detector.score_regime は Python から呼び出して target_date を渡して実行します（OPENAI_API_KEY が必要）。
  - 例（簡易）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 4, 1), api_key="sk-...")
    ```

---

## 主要な実装上の注意点 / 運用メモ

- Monitoring は監視 DB（SQLite）にログを永続化します。init_monitoring_db() は冪等的にテーブルと簡単なマイグレーション（カラム追加）を行います。
- run_monitoring は MONITOR_POLL_INTERVAL（環境変数）を読みます。0 以下や不正値はデフォルト 60 秒にフォールバックします。
- Execution 実行前に kill.flag をクリーンにする設定があり（Settings.kill_flag_clear_on_start）、起動時に flag のクリアを行うことができます。
- process priority（優先度）設定は psutil を使いプラットフォーム差分を吸収しますが、権限不足で設定できない場合は警告を出してスキップします。
- Paper Trading は本番 DB と分離されるよう設計されています（SQLITE_PATH と PAPER_TRADING_SQLITE_PATH を使い分け）。
- AI（OpenAI）周りはネットワークエラーや API レート制限に対するリトライ処理、レスポンスのバリデーションを実装していますが、API キー未設定時は例外となる箇所があります。運用時は OPENAI_API_KEY を必ず設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルと簡単な説明です。完全なファイル一覧はリポジトリを参照してください。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_execution.py — ExecutionEngine の起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト

- src/kabusys/execution/
  - execution_engine.py — 実行エンジン本体（起動・セッション管理）
  - order_manager.py — 発注の外向き API（Order State Machine）
  - order_repository.py — 注文を SQLite に永続化するリポジトリ
  - reconciler.py — 再起動時の注文・ポジションリコンシリエーション
  - broker_factory.py, broker_api.py — ブローカークライアント抽象化

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義・読み書きユーティリティ
  - system_monitor.py — システム状態 / データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込み管理
  - alert_manager.py — LINE push 通知ラッパー
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視 UI

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 数量決定・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でセンチメント付与し ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 最後に（トラブルシューティング）

- DB やファイルパスでアクセスエラーが出る場合、パスの所有権／パーミッションを確認してください。
- OpenAI / LINE 連携でエラーが出た場合は API キーやトークンが正しく設定されているか、ネットワーク経路が許可されているかを確認してください。
- モジュール間は明確に責務分離されているため、単体コンポーネントを Python スクリプトや REPL から直接呼び出して動作確認することを推奨します（例：research の factor 計算や ai.score_news の単独実行など）。

ご不明点や README に追加してほしい実行例・図解などあれば教えてください。