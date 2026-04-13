# KabuSys

日本株向け自動売買システムの一部実装（ライブラリ／運用スクリプト群）。  
本リポジトリは戦略・実行・監視・リサーチ・AIユーティリティ等を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群から構成されます。

- Execution（発注エンジン）: ブローカーとの発注・状態管理、リスク管理、再起動時リコンシリエーション
- Monitoring（監視）: システム稼働状況、注文滞留・約定異常、ドローダウンやポジション数の監視、LINE通知、kill-flag
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、リスク調整、株数算出
- Research（リサーチ）: ファクター計算（モメンタム／ボラティリティ／バリュー）、特徴量解析
- AI（LLM連携）: ニュースのセンチメント、マクロセンチメントによるレジーム判定
- Tools（運用補助）: Paper Trading 検証レポート生成、監視用 Streamlit ダッシュボードなど

設計上のポイント:
- DB: DuckDB（履歴・ファクター計算など）と SQLite（監視・注文ログなど）を併用
- テスト・運用で環境分離: `KABUSYS_ENV` による `development` / `paper_trading` / `live`
- OpenAI（LLM）を利用する機能は API キーを要求し、フォールバックやリトライを含む堅牢設計
- .env 自動読み込み（プロジェクトルートに .env / .env.local があれば環境変数へ適用）

---

## 機能一覧

主要な機能（抜粋）:

- Execution
  - 発注フロー管理（OrderManager / OrderRepository）
  - Broker 抽象化（BrokerClientFactory）→ paper_trading では MockBroker 使用
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン検出・ポジション上限監視
  - KillSwitch: 条件に応じた flag ファイル書き込みによる Execution 停止シグナル
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring DB レイヤ（MonitoringDB）: テーブル作成・マイグレーション・ログ書き込み

- Portfolio
  - 候補選定（select_candidates）
  - 等金額／スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ決定（calc_position_sizes）
  - セクターキャップ適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- Research
  - ファクター集計（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー

- AI
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）

- Tools
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## 必要環境 / 依存

- Python 3.10 以上（型アノテーションで `|` を使用）
- 主な外部ライブラリ:
  - duckdb
  - psutil
  - requests
  - streamlit（ダッシュボード利用時）
  - openai（AI 関連機能）
- SQLite（標準ライブラリで対応）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```
（実運用では requirements.txt を用意して管理してください）

---

## セットアップ手順

1. リポジトリをクローン / 配置し、仮想環境を作成して依存をインストールする（上記参照）。

2. 環境変数の設定:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. 主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能利用時に必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading の約定挙動、instant|partial|never|reject、デフォルト: instant）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用、未設定なら送信はスキップ）
   - PID_FILE_PATH（Execution の PID 管理、デフォルト: data/execution.pid）
   - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）
   - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

4. ディレクトリ・ファイルの作成:
   - 必要に応じて `data/` ディレクトリを作成してください（SQLite / DuckDB のデフォルトパス）。
   - `PID_FILE_PATH`/`KILL_FLAG_PATH` の親ディレクトリも作成されますが、事前に準備しておくと運用上安心です。

---

## 使い方（主なスクリプト）

- Monitoring（常駐監視プロセス）を起動:
  - デフォルト（モジュールとして実行）:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を上書き:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 概要:
    - プロセス優先度を high に設定（可能であれば）
    - SQLite（monitoring DB）へ接続しテーブル作成（冪等）
    - DuckDB に接続（データ鮮度チェック等に利用）
    - SystemMonitor.check_once をループで実行

- ExecutionEngine（発注エンジン）を起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のとき、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ完全分離された記録を行います。
  - 起動時に PID ファイルを書き込み、Execution 側の動作を監視プロセスが確認します。

- Streamlit ダッシュボード（監視）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 引数 `--db` で監視 DB のパス（読み取り専用で開かれます）を指定可能。

- Paper Trading 検証レポート（ツール）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # or 指定 DB:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 出力: 稼働率、注文成功率・送信率、P95 レイテンシなどのサマリと Pass/Fail 判定

- AI 機能（プログラムから呼び出す）:
  - ニュースセンチメント: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - どちらも `OPENAI_API_KEY`（引数または環境変数）を参照します。

---

## 運用上の注意

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を自動で読み込みます。OS の環境変数は上書きされません（`.env.local` は上書き可能）。
  - テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB マイグレーション:
  - monitoring DB は init_monitoring_db() が冪等にテーブル・インデックス・カラム追加（簡易マイグレーション）を行います。

- Kill Switch:
  - RiskMonitor 等が kill 条件を満たすと `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を書き込みます。Execution エンジンは起動時 / 定期確認でこのファイルを見て安全に停止します。

- 権限・優先度:
  - set_process_priority() は OS により権限不足で失敗する場合があります（警告を出してスキップ）。

- OpenAI API:
  - レート制限・一時的エラーに対してはリトライ実装がありますが、API キーの管理・コストに注意してください。
  - レスポンスの JSON バリデーションを行い、失敗時は該当処理をスキップして安全に継続します。

---

## ディレクトリ構成（抜粋）

（コードベースは `src/kabusys` 以下に配置される想定）

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数・設定管理（.env 自動読み込み）
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py — ニュースの LLM センチメント取得
      - regime_detector.py — 市場レジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py — SQLite 用永続化レイヤ
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
      - (※ broker_api / order_repository 等を含む)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py

詳細は各ファイルの docstring／コメントをご参照ください。

---

## 参考コマンドまとめ

- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 発注エンジン起動:
  - python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載のない詳細（API 定義・OrderRepository スキーマ等）は各モジュールの docstring を参照してください。運用前に .env の値・DB のバックアップ方針・LINE や OpenAI のキー取り扱い（機密管理）を必ず確立してください。