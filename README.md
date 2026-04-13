# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行コンポーネント群）のソースコードです。  
このリポジトリはトレーディングの実行エンジン、監視・アラート、ポートフォリオ構築、ファクター研究、AIによるニュースセンチメント評価などを含みます。

---

## プロジェクト概要

KabuSys は以下機能を備えた小規模な自動売買プラットフォームです。

- 注文管理・実行（ブローカークライアント抽象化）
- ExecutionEngine（トレーディングセッションの実行）
- 監視（システム状態・注文滞留・リスク監視）と通知（LINE）
- Paper Trading 用の分離DBと検証レポート生成ツール
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算、セクター上限等）
- 研究用ファクター計算（Momentum/Volatility/Value 等）と特徴量探索ツール
- AI（OpenAI）を用いたニュースセンチメント評価 / レジーム判定
- Streamlit ベースの監視ダッシュボード

設計方針として、DB（SQLite / DuckDB）へ状態を永続化し、テストしやすい純粋関数分離と外部API呼び出しのフェイルセーフを重視しています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い `data/paper_trading.db` に記録し、本番DBと分離。
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（デフォルト60秒間隔、環境変数で上書き可）。
  - 監視ログは常に本番の sqlite_path を使用して永続化。
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch / MonitoringDB 等
  - system_status / trade_logs / positions / risk_logs / dashboard の永続スキーマを提供
- tools/paper_verification_report.py
  - Paper Trading DB から検証レポート（稼働率・注文成功率・レイテンシ等）を出力
- portfolio
  - 候補選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数等
- research
  - ファクター計算（momentum, volatility, value）、将来リターン計算、IC（Information Coefficient）等
- ai
  - news_nlp: raw_news をまとめて OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector: マクロ記事＋ETF ma200 乖離から市場レジームを判定
- utils
  - process_priority: プロセス優先度 / CPU affinity のユーティリティ
- streamlit_dashboard.py
  - 監視DB を読み取る簡易ダッシュボード（streamlit）

---

## 必要な環境・依存ライブラリ

最低限必要な Python パッケージ（代表例）：

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit

インストール例:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai requests streamlit

（実際の requirements.txt がある場合はそちらを使用してください。）

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（未設定時は起動でエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（デフォルト値あり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (default: "")
- LINE_USER_ID (default: "")
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視DB
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) (default: instant)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: "0")
- CPU_THRESHOLD_PCT (default: 90.0)
- MEMORY_THRESHOLD_PCT (default: 85.0)
- DISK_THRESHOLD_PCT (default: 90.0)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

AI を使う機能:
- OPENAI_API_KEY を設定（ai.news_nlp, ai.regime_detector が使用）

run_monitoring 固有:
- MONITOR_POLL_INTERVAL（秒、デフォルト60。1未満の値は無視されデフォルトにフォールバック）

tools/paper_verification_report:
- PAPER_TRADING_SQLITE_PATH（DBパスを上書き可能）

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト。

2. Python 仮想環境を作成・有効化。

3. 依存パッケージをインストール（上記参照）。

4. 必要なディレクトリ作成:

       mkdir -p data

5. 環境変数の準備:
   - プロジェクトルートに `.env` を用意するか、OS 環境変数を設定してください。
   - 必須のキー（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY 等）を設定。

6. 初回 DB 初期化:
   - run_monitoring や run_execution 起動時に `init_monitoring_db` が呼ばれてテーブルが作られます。手動で作る必要は基本的にありません。

---

## 使い方

- ExecutionEngine（実際に注文を送る実行部）を起動:

      python -m kabusys.run_execution

  - 起動時に Settings.env（KABUSYS_ENV）が `paper_trading` の場合、paper_db（PAPER_TRADING_SQLITE_PATH）を使用し本番DBと分離されます。
  - プロセス優先度は自動的に High に設定されます（権限が必要な場合は警告を出してスキップ）。

- Monitoring（システム監視ループ）を起動:

      python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視DB（SQLITE_PATH）に system_status / risk_logs / trade_logs / positions / dashboard が保存されます。

- Streamlit ダッシュボード（ブラウザで監視）:

      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - `--db` オプションでデータベースパスを指定できます（デフォルト: data/monitoring.db）。
  - 読み取り専用URIで開くため、DBが存在しないとエラー表示されます。

- Paper Trading 検証レポート出力:

      python -m kabusys.tools.paper_verification_report \
          --from 2026-04-01 --to 2026-04-11 \
          --db data/paper_trading.db

  - `--db` が省略されると環境変数 `PAPER_TRADING_SQLITE_PATH` → `data/paper_trading.db` の順で解決されます。

- AI モジュール（プログラムから呼ぶ例）:

  - ニューススコアリング:

        from datetime import date
        import duckdb
        from kabusys.ai.news_nlp import score_news

        conn = duckdb.connect("data/kabusys.duckdb")
        count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

  - レジーム判定:

        from datetime import date
        import duckdb
        from kabusys.ai.regime_detector import score_regime

        conn = duckdb.connect("data/kabusys.duckdb")
        score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

  - どちらも API キーが引数に渡されなければ環境変数 `OPENAI_API_KEY` を参照します。API 呼び出しは冪等性・フェイルセーフを考慮しています（失敗時は部分的にスキップまたは安全なデフォールト）。

---

## 監視・キルスイッチの挙動（概要）

- RiskMonitor は dashboard の portfolio_value をもとにハイウォーターマークを維持し、ドローダウン閾値超（デフォルト10%）やポジション上限超で risk_log に記録・アラートを出します。
- KillSwitch はリスクアラート（ドローダウン／ポジション上限）に該当した場合 `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine は起動時/定期でこのファイルをチェックして停止できます（実装側で利用）。
- AlertManager は LINE Push を用いた通知を行う（Token/UserID が設定されていない場合は送信を行わずログのみ）。

---

## 主要ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - monitoring/
    - monitoring_db.py — SQLite 用永続層（スキーマ初期化・CRUDユーティリティ）
    - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / プロセス監視
    - trade_monitor.py — 注文滞留 / 約定価格異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ...（注文・リコンシリエーション・リスク管理等）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算 / 特徴量解析
  - ai/
    - news_nlp.py — ニュースセンチメントの取得・保存
    - regime_detector.py — 市場レジーム判定
  - utils/
    - process_priority.py — OS横断のプロセス優先度設定

---

## 開発・運用上の注意

- .env の扱い
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を検索して `.env` / `.env.local` を自動ロードします。OS環境変数よりも上書きされないよう配慮されています。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB の分離
  - 監視用 DB（SQLITE_PATH）と Paper Trading DB（PAPER_TRADING_SQLITE_PATH）は明確に分離されます。Paper Trading 時に本番DBに影響を出さない運用ができます。
  - init_monitoring_db は冪等であり、既存DBにカラムが欠ける場合はマイグレーション（ALTER TABLE）も行います。

- AI 呼び出し
  - OpenAI API 呼び出しはレート制限/ネットワーク断/一時エラー等を考慮して指数バックオフでリトライします。最終的に失敗しても例外を投げずに安全に継続する設計箇所が多いです（ログは出ます）。

- 権限
  - プロセス優先度設定には OS 側の権限が必要な場合があります。失敗すると警告出力のうえスキップされます。

---

## よく使うコマンド例

- Execution 起動（本番設定が整っている場合）:

      KABUSYS_ENV=live python -m kabusys.run_execution

- Paper Trading 実行:

      KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（デフォルト 60 秒）:

      MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート（期間指定）:

      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:

      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README にさらに具体的な起動例、DB スキーマの詳細、ExecutionEngine や Broker の設定方法、単体テスト・CI の説明などを追加できます。追加してほしい項目があれば教えてください。