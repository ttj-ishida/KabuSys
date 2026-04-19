# KabuSys

日本株向け自動売買システムのコア部分（ライブラリ・起動スクリプト・ユーティリティ群）。

このリポジトリは戦略構築・バックテスト用のリサーチ機能、ExecutionEngine（発注エンジン）、
監視 (Monitoring) 周りのユーティリティ、AI を使ったニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化した Python コードベースです。

- データ取得／分析（DuckDB を使ったファクター計算・将来リターン）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- ExecutionEngine（発注ロジック、ブローカ API 抽象化、Risk 管理）
- 監視（SystemMonitor, TradeMonitor, RiskMonitor と Kill Switch）
- AI モジュール（OpenAI を利用したニュースのセンチメント評価 / レジーム検出）
- 運用ユーティリティ（設定ウィザード、設定検証、レポート生成、ロギング設定）

設計上のポイント:
- 環境依存設定は .env / 環境変数で管理（自動読み込みあり、無効化可）
- Paper Trading（ペーパー取引）モードは本番 DB と分離（data/paper_trading.db）
- ロギングは共通ユーティリティで統一（stdout + 日次ローテーション）
- AI 呼び出しは冗長性（リトライ）・バリデーション実装あり。失敗時は安全側にフォールバック

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（.env / .env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config

- 起動スクリプト
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB を利用
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）

- 監視 / Kill Switch
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine
  - KillSwitch により data/kill.flag を書き込むと ExecutionEngine を停止可能

- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重配分、リスクベースの発注株数計算
  - セクターキャップやレジーム乗数の適用

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でスコア化して ai_scores に保存
  - regime_detector: ETF + マクロニュースから日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提・依存関係

最低限必要な Python パッケージ（抜粋）:
- duckdb
- psutil
- openai

（追加で PyYAML があれば validate_config が config/*.yaml の中身まで検証します）

pip の requirements ファイルがある場合はそれを使用してください。なければ以下の例を参考にインストールしてください:

pip install duckdb psutil openai

推奨 Python バージョン: 3.10 以上（型ヒントと | 型合併を使用）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading モード時)
- LOG_LEVEL: INFO（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

注意:
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウトして src にパッケージがあることを確認

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - optional: pip install pyyaml  （validate_config の YAML 検査用）

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参考にする）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトの DB / ログ保存先（例: data/, logs/）が存在しない場合は作成されます。起動時に自動作成を試みますが、権限等で失敗する場合は事前に作成してください。

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- 実行エンジンを起動（本番 / ペーパー両対応）
  - KABUSYS_ENV によって挙動が変わります
  - 実行:
    - python -m kabusys.run_execution
  - Paper trading の場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - ※ Paper 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=120  # 120 秒ごとにポーリング

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。別 DB を指定する場合は --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション・30日保持

- Kill / Stop
  - 実行エンジン・監視はフラグファイルで停止を制御します:
    - data/kill.flag: Kill Switch（監視やリスク発生時に生成）
    - data/stop_requested.flag: 起動スクリプトが監視する停止要求フラグ（run_monitoring / run_execution が検出して終了）
  - Kill flag の自動クリア設定:
    - KILL_FLAG_CLEAR_ON_START 環境変数を 1 にすると起動時に kill.flag を自動クリア（本番では推奨しない）

---

## よく使うコマンド例

- .env を対話的に作成:
  - python -m kabusys.config_setup

- 設定検証（通常）:
  - python -m kabusys.validate_config

- 設定検証（警告も FAIL）:
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（バックグラウンド例）:
  - nohup python -m kabusys.run_execution > logs/execution.out 2>&1 &

- 監視ループ起動（間隔 30 秒）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper 検証レポート（DB 指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

## トラブルシューティング

- 必須環境変数未設定
  - validate_config でエラーになります。JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD などを .env に設定してください。

- OpenAI を使う機能でのエラー
  - OPENAI_API_KEY が必要です。未設定時は関数が ValueError を投げます。テストやローカルで OpenAI を使わない場合は機能を呼び出さないでください。

- ログや DB のディレクトリ作成に失敗する
  - 起動スクリプトはログディレクトリ作成に失敗した場合、ファイル出力をスキップして stdout のみで継続します。パーミッションを確認して事前にディレクトリを作成してください。

- MONITOR_POLL_INTERVAL の設定ミス
  - 0 や負数を設定するとデフォルト（60 秒）にフォールバックします。無効な値は警告で通知されます。

---

## ディレクトリ構成（抜粋）

プロジェクトルート配下の主要なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - ...（trade_monitor, alert_manager 等が存在）
  - execution/                — ExecutionEngine/OrderManager/Repository 等（実装ファイル群）
  - utils/
    - logging_setup.py
    - process_priority.py

データ / 実行関連（ランタイムに作成されることが多い）:
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading モード用)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - ...

---

## 開発者向けメモ

- .env 自動読み込みはプロジェクトルート判定（.git もしくは pyproject.toml）に基づくため、パッケージ配布後でも安定して動作します。テスト環境で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続（research / ai / regime）は SQL を多用しており、テーブル名（prices_daily / raw_financials / raw_news 等）に依存します。テーブルスキーマはコード内のクエリ参照を参照してください。
- Logging は setup_logging により stdout と日次ローテーション（30 日分）を自動で設定します。起動スクリプトは最初に setup_logging を呼び出してから処理を進めます。
- Process priority 設定は psutil を用いて OS 間の差を吸収します。権限不足等の理由で設定できない場合は警告ログを出してスキップします。

---

必要があれば、README に含める具体的な .env のテンプレート、systemd ユニットファイル例、あるいはより詳しいディレクトリツリー（すべてのモジュール一覧）を追加で作成します。どの情報を詳しく載せたいか教えてください。