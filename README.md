# KabuSys

日本株自動売買システムのリポジトリ用 README（日本語）

この README はリポジトリ内の主要スクリプト・モジュールの使い方、設定方法、構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python ベースのシステムです。主な機能は以下のとおりです。

- 戦略・ポートフォリオ構築（候補選定、配分、ポジションサイズ決定、セクター制限）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）
- Paper Trading（モックブローカー）および実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）と Kill Switch による自動停止判断
- ニュース NLP（OpenAI を用いたセンチメント評価）
- レポート生成（Paper Trading 検証レポートなど）
- 環境設定ウィザード / 設定検証ツール

設計方針として、「本番 API への不要な呼び出しを避ける」、「ルックアヘッドバイアスを防ぐ」、「DB の冪等操作」を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config / config_setup.py / validate_config.py
  - .env の自動ロード / 対話式ウィザード / 設定検証
- kabusys.run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し paper_trading DB に分離
- kabusys.run_monitoring.py
  - SystemMonitor をポーリング実行する監視プロセス起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔指定可能
- kabusys.execution.*
  - ブローカークライアント生成、注文管理、リスク管理、照合など（実行ロジック）
- kabusys.monitoring.*
  - MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager
- kabusys.portfolio.*
  - 銘柄選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- kabusys.research.*
  - ファクター計算（momentum, volatility, value）、特徴量探索、IC 計算、統計サマリ
- kabusys.ai.*
  - news_nlp: OpenAI を用いたニュースセンチメント -> ai_scores へ書き込み
  - regime_detector: MA やマクロセンチメントから市場レジーム判定
- kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート生成スクリプト（期間指定可）
- kabusys.utils.*
  - logging_setup（統一ログ設定）, process_priority（優先度 / CPU affinity）

---

## セットアップ手順

前提
- Python 3.9+ を推奨（typing 機能やパッケージ互換を考慮）
- 仮想環境（venv / poetry / pipenv 等）を推奨

例（venv + pip）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下が必要です:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（validate_config の YAML 検証で使用）

3. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（例は下記参照）

4. 設定を検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

5. 必要なディレクトリ（data, logs など）は起動スクリプトが自動で作成することが多いですが、権限等で失敗する場合は手動で作成してください。

.env の例（最低限必須）
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password

# 環境
KABUSYS_ENV=development   # development|paper_trading|live

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI (AI 機能を使う場合)
OPENAI_API_KEY=sk-...

# ログ等
LOG_LEVEL=INFO
LOG_DIR=logs
```

環境変数の自動読み込み
- プロジェクトルートに `.env` / `.env.local` があれば自動的にロードされます（OS 環境変数を優先）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方

主要なコマンド／モジュール起動例を示します。

1. .env の生成（対話式ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 失敗（exit code 1）したら表示されるエラーを確認し修正してください。

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 挙動：
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録する
     - 起動前に data/stop_requested.flag が存在すると起動せずに終了する
     - 起動時に `data/execution.pid`（デフォルト）へ PID を書きます
     - 終了時に SQLite / DuckDB 接続をクローズします

4. 監視プロセス起動（SystemMonitor のポーリング）
   - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）
   - 特徴:
     - 監視は本番 `sqlite_path` を使用（環境にかかわらず）
     - stop_requested.flag を検知するとループを終了

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定:
     - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を利用

6. AI 系の実行
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - API 呼び出し失敗時はフェイルセーフ（多くのケースで 0.0 や中立値で継続）
     - OpenAI の利用はコストが発生します

7. ログ
   - ログはデフォルトで `logs/<app_name>.log` に日次ローテートで保存（30日保持）
   - `LOG_DIR` 環境変数で変更可
   - `LOG_LEVEL` でレベルを指定（例: DEBUG, INFO）

Kill Switch / 停止フラグ
- 監視モジュールは `KillSwitch` を使って条件を満たした場合 `data/kill.flag` を書き込みます。
- ExecutionEngine は `kill.flag` が存在すると安全停止や起動抑止を行います。
- 手動で停止をリクエストする場合は `data/stop_requested.flag` を作成してください（実行中の run_monitoring/run_execution が検知）。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（抜粋）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - config.py                       — 環境変数 / 設定読み込みロジック
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 設定検証 CLI
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - ai/
      - news_nlp.py                   — ニュース NLP（OpenAI）によるスコアリング
      - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層（schema 初期化含む）
      - system_monitor.py             — システム状態・データ鮮度監視
      - trade_monitor.py              — 注文ログ監視（滞留注文・異常約定等）※実装あり
      - risk_monitor.py               — ドローダウン・ポジション上限監視
      - kill_switch.py                — kill.flag の書き込み・判定
      - monitoring_engine.py          — 各 Monitor を束ねるランナー
      - alert_manager.py              — 通知（LINE など）管理（実装あり）
    - execution/
      - execution_engine.py           — ExecutionEngine 本体
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py               # 監視用 DB スキーマとラッパー
    - utils/
      - logging_setup.py               — ログ設定ユーティリティ
      - process_priority.py            — プロセス優先度 / CPU affinity
    - data/                             — 実行時に生成されることの多いディレクトリ（DB, flag 等）
  - （その他のサポートコード）

（上記は主要モジュールの概観です。実際の実装ファイルはリポジトリ内を参照してください。）

---

## 追加の注意点 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では特に以下を確認してください:
  - LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）
  - KILL_FLAG_CLEAR_ON_START は基本 0 を推奨（自動クリア禁止）
  - 設定検証（python -m kabusys.validate_config）を実行して警告・エラーを潰す
- Paper Trading と本番 DB は明確に分離されています（paper_trading 用 sqlite が利用可能）
- OpenAI API を用いる機能は API キーの管理とコストに注意してください
- ログや data/ 以下のファイルは機密情報を含む可能性があるため Git にコミットしないでください（config_setup でも注意書きあり）
- プロセス優先度 / CPU affinity は utils.process_priority を使ってプラットフォーム差分を吸収しますが、設定に失敗する権限状況も想定してフェイルセーフになっています

---

## 問い合わせ・貢献

バグ報告や改善提案は Issue を立ててください。プルリクは歓迎します。ドキュメントやテスト追加も助かります。

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring やソースを参照してください。