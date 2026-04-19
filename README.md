# KabuSys

日本株向け自動売買システムの一部実装（ライブラリ／起動スクリプト群）。  
このリポジトリは「Execution（発注）」「Monitoring（監視）」「Research（ファクター計算）」「AI（ニュース NLP / レジーム判定）」などの主要機能をモジュール化しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を組み合わせ、自動売買運用を支援します。

- 注文発行ロジック（ExecutionEngine）
  - 本番・ペーパートレードを切り替え可能
  - リスク管理・注文管理・約定の照合などを備える
- 監視（Monitoring）
  - システム状態・データ鮮度・取引挙動・ドローダウン監視
  - Kill Switch による安全停止（フラグファイルで ExecutionEngine 停止）
  - アラート発行（LINE 等の通知は設定に依存）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC 計算などの統計ツール
- AI 補助
  - ニュース記事を LLM（OpenAI）でスコア化して ai_scores に保存
  - マクロ＋ETF 指標から市場レジームを推定して記録
- ペーパートレード検証ツール
  - paper_verification_report による期間集計と PASS/FAIL 判定

設計上の特徴:
- DuckDB を分析用 DB、SQLite を監視・ペーパートレードログ用 DB として利用
- OpenAI（gpt-4o-mini 等）を利用する処理は API キー依存でフェイルセーフ設計
- 設定は .env による管理。CLI ウィザード / 検証ツールあり

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを切替）
  - 停止フラグ / PID ファイル管理、プロセス優先度設定
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
  - 停止フラグ検出によるループ終了
- config_setup.py
  - 対話式に .env を作成・更新するウィザード
- validate_config.py
  - .env / config/*.yaml の妥当性チェック（--strict オプションあり）
- tools/paper_verification_report.py
  - ペーパートレード DB を集計し検証レポートを出力
- monitoring/*
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db 等
- ai/*
  - news_nlp（ニュースセンチメント → ai_scores）
  - regime_detector（マクロ + ETF 指標で market_regime を生成）
- research/*
  - factor_research（momentum/volatility/value 等）
  - feature_exploration（forward returns / IC / summary）
- portfolio/*
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター上限等の純粋関数群
- utils/*
  - logging_setup（統一ログ設定）、process_priority（優先度/CPU affinity 設定）等

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上（型ヒントの構文等を使用）
- SQLite（標準ライブラリ）、その他下記パッケージが必要

推奨手順（Unix 系の例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - optional: pip install pyyaml（validate_config の YAML 検証を有効にする場合）

   （requirements.txt がある場合は pip install -r requirements.txt）

3. .env を作成
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動作成（下記参照）

4. DB/ディレクトリ準備
   - デフォルトでは data/ 以下を使用（例: data/monitoring.db, data/kabusys.duckdb）
   - 必要なら手動でディレクトリを作成（実行時に自動作成されることも多い）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い

.env の主なキー（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（DEBUG/INFO/...）

例（.env の一部）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

注意:
- .env は機密情報を含むため絶対にコミットしないでください。

---

## 使い方（主要スクリプト）

プロジェクトルートで実行してください（.env 自動ロードが有効であれば環境変数が読み込まれます）。

- ExecutionEngine を起動（通常は systemd / supervisor 等で管理）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
    - 起動時に data/stop_requested.flag が存在すると起動をキャンセル
    - 実行中に stop_requested.flag が作成されると停止処理を開始

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に関わらず monitoring DB は共通）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH が優先

- 研究 / AI 機能（ライブラリ呼び出し）
  - AI ニューススコア化:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - api_key 未指定時は環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

ログ出力
- デフォルト logs/ ディレクトリに日次ローテーションでログファイルを出力（例: logs/execution.log, logs/monitoring.log）
- ログ設定は kabusys.utils.logging_setup.setup_logging を各スクリプトで使用

Kill Switch / 停止フラグ
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます
- run_execution.py / run_monitoring.py は data/stop_requested.flag を検知して終了します
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアさせるオプションあり（本番では 0 推奨）

---

## ディレクトリ構成（抜粋）

カレントの実装ファイル群に基づく主要構成:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定読み込みロジック（.env 自動読み込み）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/                    — ExecutionEngine 関連（broker, order_manager 等）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (ランタイムで作成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
  - logs/ (ログ出力先、起動時に作成)

（実際のツリーはリポジトリ全体を参照してください。ここでは主要ファイルのみ列挙しています）

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使う）:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 専用 DB)
- OPENAI_API_KEY (AI 機能を利用する場合)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (run_monitoring の秒間隔上書き)
- KILL_FLAG_CLEAR_ON_START (1/0、本番は 0 推奨)
- PID_FILE_PATH / KILL_FLAG_PATH（必要に応じてカスタマイズ）

validate_config.py で設定の過不足をチェックできます。

---

## 運用に関する注意点

- .env は機密情報を含むので絶対にコミットしないでください。
- KABUSYS_ENV=live の設定は本番発注を伴います。LINE 等の通知設定や Kill Switch の設定を慎重に行ってください。
- OpenAI を使う処理は API レートやコストに敏感です。API キー管理と呼び出し頻度に注意してください。
- run_execution/run_monitoring は長時間デーモンとして動作することを想定しています。systemd / supervisor 等で管理するのが望ましいです。
- DuckDB／SQLite のパスは共有／バックアップ方針に応じ適切に配置してください。

---

## 開発者向け情報 / テスト呼び出し例

- 簡易的に MonitoringEngine を 1 回だけ実行する（ユニットテスト用途）:
  - from kabusys.monitoring.monitoring_engine import MonitoringEngine
  - 組み立てた monitor オブジェクトに対して run_once() を呼ぶ

- AI モジュールのユニットテスト:
  - news_nlp._call_openai_api / regime_detector._call_openai_api をモックして外部 API 呼び出しを抑制できます

---

README はここまで。実際の運用前に python -m kabusys.validate_config で環境設定を確認し、.env の内容を必ず確認してください。必要があれば systemd ユニットや監視スクリプトのテンプレート作成もサポートします。必要であれば追記しますので、どの部分を詳しく書いてほしいか教えてください。