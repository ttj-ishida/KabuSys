# KabuSys

日本株自動売買システムのサブセット実装。ポートフォリオ構築、発注管理、監視、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定を含むユーティリティ群を提供します。

以下はこのリポジトリに含まれる主要な機能と使い方の概要です。

---

## プロジェクト概要

KabuSys は国内株の自動売買を想定したモジュール群です。主な設計方針は以下のとおりです。

- モジュール単位で純粋関数や副作用（DB / API 呼び出し）を分離
- 本番環境と紙上（paper trading）を明確に分離（SQLite DB を分ける）
- DuckDB を使ったファクター計算・リサーチ
- OpenAI を用いたニュースセンチメント / レジーム判定機能（API キー必須）
- 監視・アラート機能（LINE Push）と kill-flag による実行エンジン停止信号

---

## 主な機能一覧

- Execution
  - 発注管理（OrderManager）
  - 再起動時のリコンシリエーション（Reconciler）
  - ブローカークライアントの抽象化（BrokerClientFactory）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常チェック
  - RiskMonitor：ドローダウン／ポジション上限の監視とダッシュボード更新
  - MonitoringDB：監視ログ（SQLite）永続化
  - AlertManager：LINE Push による通知（トークン未設定時はログのみ）
  - KillSwitch：条件により kill.flag を書き込んで ExecutionEngine を停止
  - streamlit ベースの監視ダッシュボード
- Portfolio construction
  - 候補選定、等配分/スコア加重配分、リスク調整（セクター制限）、ポジションサイジング
- Research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でのファクター計算
  - feature_exploration：将来リターン計算、IC（Information Coefficient）など
- AI
  - news_nlp.score_news：OpenAI でニュースをセンチメントスコア化して ai_scores に保存
  - regime_detector.score_regime：ETF とマクロニュースを合成して市場レジーム判定
- Tools
  - tools.paper_verification_report：Paper Trading の検証レポート生成（SQLite を参照）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型（`X | Y`）等を使用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- 外部 API を使う場合は OpenAI API キー

例: 仮想環境の作成と必要パッケージのインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。）

環境変数（主なもの）
- KABUSYS_ENV: 起動環境（`development` / `paper_trading` / `live`）。デフォルトは `development`。
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト: `data/paper_trading.db`）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須項目の例）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須項目の例）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine 用の PID ファイルパス（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: `data/kill.flag`）
- PAPER_FILL_MODE: paper_trading のモック約定モード（`instant` / `partial` / `never` / `reject`）

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方 / 実行例

監視ループを起動（production 監視プロセス）
```bash
python -m kabusys.run_monitoring
# または環境変数でポーリング間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して監視ログを記録します。
- 起動時にプロセス優先度を High に試みます（set_process_priority）。

ExecutionEngine を起動（実際の発注処理 or paper trading）
```bash
# 本番（KABUSYS_ENV=live 等で実行）
KABUSYS_ENV=live python -m kabusys.run_execution

# 紙上検証（paper_trading）: モックブローカーを使用し、data/paper_trading.db に記録
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- paper_trading の場合、paper 用 SQLite を使用して本番 DB と完全分離します。
- 起動時に Monitoring テーブルの初期化（冪等）を行います。

Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- レポートは稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

Streamlit ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開き、ポートフォリオ、注文履歴、システム指標、リスクログを可視化します。

AI 機能（ニュースセンチメント / レジーム判定）
- OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数）。
- プログラムから使用する例:
  - news_nlp.score_news(conn, target_date)
  - regime_detector.score_regime(conn, target_date)
- 失敗時はフォールバック（0.0 等）して例外を投げず継続する設計です（フェイルセーフ）。

Kill flag（ExecutionEngine 停止）
- KillSwitch は条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine は起動時・定期的にこのフラグを確認して停止できます。
- フラグの手動クリア:
```bash
rm data/kill.flag
```
- Settings.kill_flag_clear_on_start を 1 にすると ExecutionEngine 起動時に自動クリアできます。

---

## 主要モジュール / 役割（抜粋）

- kabusys.config: 環境変数の読み込み・Settings クラス
- kabusys.monitoring.*
  - monitoring_db: SQLite テーブル定義と永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor: システム状態・データ鮮度チェック
  - trade_monitor: 滞留注文・約定異常チェック
  - risk_monitor: ドローダウン・ポジション上限監視
  - alert_manager: LINE への通知
  - kill_switch: kill.flag の管理
  - monitoring_engine: 各 Monitor を束ねるループ
- kabusys.execution.*
  - order_manager, order_repository, reconciler, execution_engine など（発注と再同期）
- kabusys.portfolio.*
  - portfolio_builder, risk_adjustment, position_sizing（候補選定・重み・サイジング）
- kabusys.research.*
  - factor_research（momentum/volatility/value）および feature_exploration（IC 等）
- kabusys.ai.*
  - news_nlp, regime_detector（OpenAI を利用する NLP ロジック）
- kabusys.tools.paper_verification_report: Paper Trading の品質検証レポート生成

---

## ディレクトリ構成

（src/kabusys 以下を中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他発注関連モジュール)
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - monitoring/ (上記)
    - data/ (期待されるデータファイルの保存先: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など)

---

## 注意事項 / 運用メモ

- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を未設定で実行すると Settings で ValueError が発生します。
- AI 機能は OpenAI API の課金対象となるため、テスト時にはモック化（unittest.mock.patch など）を推奨します。モジュール内に _call_openai_api を差し替えるための注記があります。
- Monitoring や Execution の起動時にプロセス優先度や PID ファイル管理を行います。OS によっては権限不足で設定に失敗することがあります（警告ログになるだけで致命エラーとはなりません）。
- Paper Trading は本番 DB と完全に分離されます。`KABUSYS_ENV=paper_trading` を設定して利用してください。
- DuckDB 接続は prices_daily / raw_financials / raw_news / ai_scores 等のテーブルに依存します。データ投入がないとリサーチ／AI 機能は有意な結果を返しません。

---

README は以上です。必要があれば、環境変数の完全な一覧やサンプル .env.example、docker-compose／systemd ユニットの例なども追加できます。どの情報を拡張するか教えてください。