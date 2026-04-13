# KabuSys

日本株自動売買システムのコアモジュール群のリポジトリ（ライブラリ）。  
この README はソースコード（src/kabusys）を基にした概要、機能、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

注意: 実行には Python 3.10+ が必要です（型ヒントに | を使用しているため）。

---

## プロジェクト概要

KabuSys は下記の主要機能を持つ自動売買プラットフォームのコンポーネント群です。

- 発注エンジン（ExecutionEngine、OrderManager、Reconciler 等）
- 監視基盤（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- 監視ログ永続化（SQLite ベースの monitoring DB）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 研究モジュール（ファクター計算、将来リターン、IC 計算 等）
- AI 関連（ニュースの NLP スコアリング、レジーム判定。OpenAI API 経由）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）
- プロセス優先度・CPU affinity のユーティリティ

設計方針の特徴:
- DuckDB / SQLite によるデータアクセス（prices_daily / raw_financials / raw_news / ai_scores 等）
- 本番と Paper Trading の分離（環境変数 KABUSYS_ENV に依存）
- LLM 呼び出しはフェイルセーフ（失敗時はフォールバックで継続）
- 監視ループは定周期で動作し、kill.flag による外部停止をサポート

---

## 機能一覧

主な機能（抜粋）:

- Execution
  - 注文生成・送信・状態同期（OrderManager, Reconciler）
  - RiskManager による発注前リスクチェック
  - BrokerClientFactory を通した本番/モックブローカー切替（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - AlertManager: LINE push 通知（cooldown 管理）
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（簡易 GUI）
- Portfolio
  - 候補選定（select_candidates）
  - 等金額 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - リスク調整（セクター制限、レジーム乗数）
  - 株数決定（risk_based / equal / score の allocation）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Spearman）、統計サマリ
- AI
  - ニュースのセンチメントスコアリング（OpenAI GPT 系を利用）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート出力
  - monitoring streamlit dashboard

---

## 必要要件（ライブラリ例）

最低限必要になりうるパッケージ（実際の requirements はプロジェクトに応じて調整してください）:

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit

例: requirements.txt（参考）
- duckdb
- psutil
- requests
- openai
- streamlit

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記パッケージを個別インストール）

4. 環境変数設定（.env 推奨）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存の OS 環境変数は上書きされません）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 必須（利用する機能により必要になる変数）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意／推奨
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定振る舞い: instant|partial|never|reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を有効にする際）
     - PID_FILE_PATH / KILL_FLAG_PATH 等
   - .env のフォーマットはシンプルな KEY=VALUE で、'または"で囲った値や export キーワードも扱えます（config._parse_env_line の仕様参照）。

5. データベース初期化
   - 実行スクリプト（run_monitoring/run_execution）が起動時に monitoring DB のテーブルを冪等で作成します（init_monitoring_db を自動実行）。

---

## 使い方（実行例）

基本的なエントリポイント:

- ExecutionEngine 起動（本番 or paper_trading）
  - 環境設定例: KABUSYS_ENV=paper_trading
  - コマンド:
    - python -m kabusys.run_execution
  - 挙動:
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時にプロセス優先度を "high" に設定し、DB を開いて ExecutionEngine.run_session() を実行します。

- Monitoring（ポーリングループ）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視ループを回し、監視結果は monitoring SQLite DB（設定に依存）へ永続化されます。
    - 監視は常に本番の sqlite_path を参照（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（監視用）
  - 起動コマンド例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用 URI で開き、ポジション / 最近の注文 / システム状態 / 最近のリスクログを表示します。

- Paper Trading 検証レポート
  - コマンド例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で PAPER_TRADING_SQLITE_PATH を指定可能
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などの要約と PASS/FAIL 判定

- AI 関連（プログラム経由）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  — DuckDB 接続と target_date を渡して実行
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意:
- OpenAI API を使う機能は OPENAI_API_KEY が必要です。キー未設定時は ValueError を投げます（モジュール内部でチェック）。
- LINE 通知はトークン / ユーザ ID が未設定なら送信をスキップしてログ出力されます。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の fill 挙動）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 運用上の注意

- 自動環境読み込み:
  - config モジュールはリポジトリのルート（.git または pyproject.toml を検出）を基に `.env` / `.env.local` を自動ロードします。OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Process 優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限不足等で設定できない場合は警告ログが出ますが続行します。
- 監視と実行は kill.flag を介して連携できます。KillSwitch がフラグを書き込むと ExecutionEngine 側が検知して安全に停止できます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動ロード含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, broker_factory など（発注ロジック・復旧処理）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py — 各モニタを束ねるループ
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 管理
  - streamlit_dashboard.py — Streamlit 用ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構成ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター算出 / 解析
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）
  - regime_detector.py — マーケットレジーム判定（OpenAI 結合）
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- monitoring/monitoring_db.py といった永続化/ユーティリティ群

（上記は主要ファイルを抜粋した概観です。各サブパッケージにさらに実装が含まれます）

---

## 参考コマンドまとめ

- ExecutionEngine 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 処理（スクリプト / インポート利用）:
  - Python から直接 score_news / score_regime を呼び出す（DuckDB 接続と target_date を渡す）

---

必要であれば、次の内容も作成できます:
- requirements.txt の自動生成（使っているパッケージのバージョン推奨）
- .env.example（推奨される環境変数一覧テンプレート）
- デプロイ・運用手順（systemd ユニットファイル例など）
- さらに詳しい API リファレンス（各モジュールの公開関数一覧）

ご希望があれば上記のいずれかを作成します。