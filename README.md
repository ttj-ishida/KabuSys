# KabuSys

KabuSys は日本株自動売買のためのモジュール群（ポートフォリオ構築・リサーチ・実行エンジン・監視・AI 補助など）をまとめたプロジェクトです。  
このリポジトリには本番／ペーパートレード両対応の実行ロジック、監視・アラート機能、DuckDB/SQLite を用いたデータ処理・永続化、OpenAI を使ったニュース NLP／レジーム判定などが含まれます。

---

## 主な機能

- 実行エンジン（ExecutionEngine）起動スクリプト
  - KABUSYS_ENV により paper_trading / live / development モードを切替
  - paper_trading 時は MockBroker を使用し DB を分離（data/paper_trading.db）
  - 起動時にプロセス優先度を設定、停止フラグ（data/stop_requested.flag / data/kill.flag）対応
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしログを SQLite に保存
  - KillSwitch（ドローダウンやポジション超過時に kill.flag を書いて Execution を停止）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定、等重／スコア重み配分、リスク調整（セクター上限、レジーム乗数）、発注株数算出（position sizing）
- リサーチ
  - DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリーなど
- AI（OpenAI）によるニュースセンチメント
  - ニュース集合を LLM に投げて銘柄別スコアを ai_scores に保存
  - 市場レジーム判定（ETF MA と LLM マクロセンチメントの合成）
- ユーティリティ
  - process priority & CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール

---

## 前提 / 必要要件

- Python 3.9+（実装上の typing やモジュール互換性に基づく想定）
- pip install で次の主要ライブラリが必要:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
- システムは SQLite（標準ライブラリ）を使用
- OpenAI を利用する機能は OPENAI_API_KEY が必要
- 実行環境は Unix/Windows 両対応だが process priority の一部機能は OS に依存

推奨: 仮想環境（venv / poetry / pipenv）を使って依存を分離してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai psutil requests streamlit
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. data ディレクトリを作る（スクリプトが自動で作成する場合もありますが事前作成推奨）
   - mkdir -p data
5. 環境変数を設定
   - .env または OS 環境変数で設定。自動ロードはプロジェクトルートに .env / .env.local を置くと有効になります。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（代表例）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション（デフォルト値は括弧内）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- SQLITE_PATH (data/monitoring.db)
- DUCKDB_PATH (data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

注意: Settings モジュールは .git または pyproject.toml を基準にプロジェクトルートを探索して .env を自動読み込みします。テストや特殊設定では KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

## 使い方（主要コマンド）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン（Execution Engine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用しデータは PAPER_TRADING_SQLITE_PATH に記録されます

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止フラグ / キルフラグ:
- run_execution / run_monitoring は data/stop_requested.flag の存在を監視します（存在すると安全に終了）。
- KillSwitch は data/kill.flag を書き込み ExecutionEngine を停止させるトリガーとして使います（冪等）。

---

## 簡単な運用フロー（例）

1. 環境変数・.env を準備して OpenAI/ブローカー系トークンを設定
2. DuckDB / SQLite の初期データをロード（prices_daily など）
3. 監視プロセスを起動（run_monitoring）
4. 実行エンジンを起動（run_execution）
5. Streamlit ダッシュボードで状態を監視、問題発生時は LINE 通知を受け取る
6. ペーパートレード検証は paper_trading モードで行い、tools/paper_verification_report で評価

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理
  - run_monitoring.py — SystemMonitor をポーリングする起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割当
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・読み書き層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - kill_switch.py, alert_manager.py, monitoring_engine.py
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ...（発注／リコンシリエーション周り）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — 実行時に使用する DB / pid / flag ファイル群（SQLITE_PATH / DUCKDB_PATH の既定位置）

---

## 注意事項 / 補足

- production（live）モードでは本番 DB パスが使用されます。paper_trading モードは専用 DB に切り替えるよう意図されています。設定ミスには注意してください。
- OpenAI 呼び出しには API レート制限やネットワークエラーが発生するため、内部でリトライ・フォールバック処理を実装していますが、キーの管理やコストには注意してください。
- process priority / CPU affinity の設定は psutil のアクセス権に依存します。権限不足だと設定がスキップされます。
- この README はコードベースの概要をまとめたものです。詳細実装は各モジュールの docstring とソースを参照してください。

必要であれば、環境変数のサンプル .env.example（例）や運用手順の詳細化、デプロイ（systemd / supervisor）用のユニットファイル例も作成します。どの情報を優先して補足しますか？