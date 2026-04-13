# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋運用用スクリプト群）。  
このリポジトリには、監視（Monitoring）、発注・実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュース NLP / レジーム判定等の機能が含まれます。

---

## プロジェクト概要

- 目的: 日本株の自動売買運用を支援するためのコンポーネント群を提供する。
  - 発注フロー（OrderManager / ExecutionEngine / BrokerClientFactory 等）
  - 監視・アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算等）
  - リサーチ（ファクター計算、将来リターン、IC 等）
  - AI 支援（ニュースセンチメント / 市場レジーム判定）
  - 運用ユーティリティ（ストリームリットダッシュボード、紙上検証レポート等）

- 設計方針（抜粋）:
  - DB は SQLite（監視用 / paper_trading 用）と DuckDB（時系列・マスター等分析用）を併用。
  - Paper Trading 環境は本番 DB と完全分離（`KABUSYS_ENV=paper_trading`）。
  - 環境変数はプロジェクトルートの `.env` / `.env.local` を自動ロード（必要に応じて無効化可）。

---

## 主な機能一覧

- 監視（Monitoring）:
  - システム状態（CPU/メモリ/ディスク）、プロセス生存確認、データ鮮度チェック（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン / ポジション上限監視とアラート（RiskMonitor）
  - Kill Switch（条件を満たしたらフラグファイルを書き ExecutionEngine 停止を促す）
  - LINE 通知によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 実行（Execution）:
  - ExecutionEngine 起動スクリプト（run_execution）: Broker クライアントの切替（Paper/Live）、リスク管理、再コンシリエーション等
  - 起動時の自動リコンシリエーション（Reconciler）

- ポートフォリオ / リスク:
  - 候補選定、等重・スコア重み付け（portfolio.portfolio_builder）
  - セクターキャップ、レジーム乗数（portfolio.risk_adjustment）
  - 株数計算・単元丸め・投下資金スケール（portfolio.position_sizing）

- リサーチ:
  - Momentum / Volatility / Value 等ファクター計算（research.factor_research）
  - 将来リターン・IC 計算・統計サマリ（research.feature_exploration）

- AI:
  - ニュースのセンチメントスコア付与（ai.news_nlp.score_news）
  - マクロ + ETF MA200 を用いたレジーム判定（ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を利用したスコアリング（API キー必須）

- ユーティリティ:
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - DB 初期化（monitoring_db.init_monitoring_db）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提: Python 3.10+（typing 機能を使用しています）を想定します。

1. 仮想環境を作成・有効化（任意だが推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 依存ライブラリをインストール  
   （requirements.txt が無い場合は主要な依存を手動インストール）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 実行・監視で psutil / duckdb / sqlite3（標準）を使用
   - AI 機能を使う場合は openai パッケージと API キーが必要

3. ディレクトリ作成（デフォルトの DB パス等に合わせておく）
   ```
   mkdir -p data
   ```

4. 環境変数の準備  
   プロジェクトルートに `.env` を置くと自動読み込みされます（デフォルトで OS 環境 > .env.local > .env の順）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
   - SQLITE_PATH (監視 DB, default: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper trading DB, default: data/paper_trading.db)
   - DUCKDB_PATH (分析 DB, default: data/kabusys.duckdb)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (LINE 通知有効化)
   - PAPER_FILL_MODE = instant | partial | never | reject (paper trading の約定挙動)
   - MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒。デフォルト 60)
   - PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid / data/kill.flag）

---

## 使い方（主要スクリプト・エントリポイント）

- 監視ループを起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は環境にかかわらず本番の sqlite_path を使用します（監視ログは単一の monitoring DB に保存されます）。

- 実行エンジンを起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、`data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に記録して本番 DB と分離します。
  - 起動時にプロセス優先度を high に設定します（set_process_priority）。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` で監視用 SQLite のパスを指定できます（デフォルト: data/monitoring.db）。
  - ダッシュボードは読み取り専用で接続します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - 引数 `--from` / `--to`（YYYY-MM-DD）で期間指定、`--db` で DB パスを指定（環境変数 `PAPER_TRADING_SQLITE_PATH` でも可）。
  - 主要な指標（稼働率・注文成功率・送信率・P95 レイテンシ）を出力し、基準値との PASS/FAIL を判定します。

- AI 関連（ニューススコア / レジーム判定）をプログラムから使う例
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を引数に取り、OpenAI API キーを環境変数 `OPENAI_API_KEY` または引数で指定します。
  - 例（簡易、実行環境に合わせて調整してください）:
    ```python
    import duckdb, sqlite3
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```
  - 実行時は OpenAI レートやエラー処理に注意（内部でリトライロジックを持ちます）。

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動。default: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。default: 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にするために設定
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化します

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境 > .env.local (override) > .env
- OS 環境は保護され、.env.local の override でも上書きされません。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env ロード・検証）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化（テーブル初期化・CRUD ユーティリティ）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル管理
    - alert_manager.py — LINE プッシュ通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
  - execution/
    - order_manager.py — 発注状態遷移の上位 API
    - reconciler.py — 起動時の自動復旧 / ポジション・注文照合
    - （その他 Broker / Engine / OrderRepository 等の実装ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算、aggregate cap、単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等ファクター
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI で解析して ai_scores に書き込み
    - regime_detector.py — ETF MA + マクロ記事でレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意 / ヒント

- Paper Trading は本番 DB と確実に分離されるよう設計されています。`KABUSYS_ENV=paper_trading` を忘れないようにしてください。
- run_execution 起動時は ExecutionEngine により `pid_file` が作成され、SystemMonitor はその PID ファイルを監視します。PID ファイルや kill.flag の管理に注意してください。
- set_process_priority は OS による制約（権限）で失敗する場合があります。警告ログが出力されますが処理は継続します。
- AI 機能を使う際は API コスト・レート制限に留意してください。内部で指数バックオフやリトライを行いますが、過度な呼び出しは避けてください。
- DuckDB / prices_daily 等のテーブルはリサーチ系関数で前提とされます。予め価格データ・財務データを格納しておいてください。

---

この README はリポジトリ内コードの仕様を元に作成しています。実運用前に必ず環境変数や DB のバックアップ、テスト環境での動作確認を行ってください。必要であれば README を拡張してサンプル .env、運用手順書（起動・停止・ロールバック手順）を追加することを推奨します。