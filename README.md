# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ兼 CLI）です。  
このリポジトリは売買エンジンの起動スクリプト、監視・リスク管理、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュース評価などのユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存ライブラリ
- セットアップ手順
- 実行方法（使い方）
- 主要環境変数 / .env の例
- ディレクトリ構成（主要ファイルの説明）
- 運用時の注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの構成要素をモジュール化したコードベースです。  
主要な責務は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（run_execution.py）
- Monitoring：システム稼働状況、注文ログ、リスク監視を行う（run_monitoring.py、monitoring/*）
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定（portfolio/*）
- Research：DuckDB 上の時系列データを用いたファクター計算・解析（research/*）
- AI モジュール：ニュースを LLM（OpenAI）で評価しスコア化（ai/*）
- ツール：ペーパートレード向け検証レポート等（tools/*）
- 設定管理・ユーティリティ：.env 読み込み、ログ設定、プロセス優先度など（config.py, utils/*）

---

## 主な機能

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（ペーパートレードでは MockBroker を利用し DB を分離）
  - run_monitoring.py：SystemMonitor のポーリングループを起動
- 監視・リスク
  - system_monitor：CPU/メモリ/ディスクやデータ鮮度、プロセス PID の監視
  - trade_monitor / risk_monitor：滞留注文、ドローダウン・ポジション上限のチェック
  - kill_switch：条件により data/kill.flag を書いて実行エンジンを停止する
- ポートフォリオ構築
  - 銘柄候補選定、等分配・スコア加重配分、リスクベースのポジション決定、セクターキャップ、レジーム乗数
- 研究用ツール
  - ファクター（モメンタム・ボラティリティ・バリュー）計算、Forward Return / IC 計算
- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を銘柄ごとに集約して LLM でセンチメントを評価し ai_scores に書き込む
  - regime_detector.score_regime：ETF MA とマクロニュースの LLM 評価を合成して市場レジームを判定
- 補助 CLI
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数・config/*.yaml の検証
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成

---

## 前提・依存ライブラリ

（プロジェクトの実行に必要な主なパッケージ例）

- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）
- sqlite3（標準ライブラリ）
- （任意）その他、Execution 側のブローカークライアントなど

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```

リポジトリに requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. クローン / 展開
   - リポジトリをクローンし、プロジェクトルートに移動します（src 配下がパッケージ）。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール
   - pip install -r requirements.txt もしくは上記の主要パッケージを個別にインストール

4. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で .env を作る場合は README の「主要環境変数」例を参考にしてください。

5. DB ディレクトリ作成
   - デフォルトでは data/ 配下に SQLite / DuckDB を置きます。必要に応じてディレクトリを作成してください（実行時に自動作成も行われますが権限等に注意）。

---

## 実行方法（使い方）

コマンドはモジュール実行形式を推奨します（プロジェクトルートから）。

- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告も FAIL 扱いにする場合:
  python -m kabusys.validate_config --strict
  ```

- 環境設定ウィザード（.env）
  ```
  python -m kabusys.config_setup
  ```

- ExecutionEngine 起動（主に発注を行うプロセス）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用します。  
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。実行中は data/stop_requested.flag か data/kill.flag により停止できます。

- Monitoring 起動（監視プロセス）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず production 用の sqlite_path を使用します（監視 DB は本番 DB を参照）。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム内 API 呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ OpenAI を使用する機能は OPENAI_API_KEY が必要（api_key 引数でも可）。

---

## 主要な環境変数

自動ロード
- プロジェクトルートにある .env と .env.local を起動時に自動的に読み込みます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / デフォルト
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（default 60）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すか（0/1）

簡単な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成（主要ファイル説明）

（パスは src/kabusys/ 以下を想定）

- __init__.py
  - パッケージ初期化、__version__ を定義

- config.py
  - .env 読み込みロジック、自動ロードの実装、Settings クラス（環境変数の取得/検証）

- config_setup.py
  - 対話式ウィザードで .env を生成 / 更新

- validate_config.py
  - 起動前の構成検証ツール（必須変数チェック、DB パス存在チェック、YAML 検証（PyYAML がある場合）など）

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使う（実際のブローカーは Mock に差し替え）

- run_monitoring.py
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔調整）

- utils/
  - logging_setup.py: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py: プロセス優先度設定（Windows/Linux の抽象化）
  - など

- monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化、スキーマ初期化とマイグレーション
  - system_monitor.py: システム状態のチェック（CPU/メモリ/データ鮮度/プロセス）
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: 条件により kill.flag を書く
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - alert_manager.py 等（アラート送信の実装がある想定）

- portfolio/
  - portfolio_builder.py: 候補の選定、重みの計算
  - position_sizing.py: 株数決定（lot で丸め、aggregate cap の対応）
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py: ニュースを LLM でセンチメント化し ai_scores に書き込むロジック（バッチ、リトライ、検証）
  - regime_detector.py: MA200 とマクロニュースを合成して市場レジーム判定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成

---

## 運用時の注意点 / 備考

- kill.flag / stop_requested.flag
  - 実行制御はフラグファイルで行います。kill.flag は ExecutionEngine 停止用（kill_switch による書き込み）、stop_requested.flag は run_monitoring / run_execution のループを終了させるために使用されています（運用者が手動でフラグ作成・削除して制御できます）。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアを無効にする）。

- DB 分離
  - paper_trading 環境では paper_trading 用 SQLite に分離されます。Monitoring は常に sqlite_path（監視 DB）を使用しますので、意図しない DB 参照が発生しないよう確認してください。

- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- OpenAI / LLM 呼び出し
  - API レスポンスの不整合や一時エラーに対して指数バックオフとバリデーションを行っていますが、API キーや利用制限に注意してください。AI モジュールは API キー未設定で ValueError を送出します。

- スキーマ / マイグレーション
  - init_monitoring_db() は安全に既存 DB を初期化・マイグレーションします（列追加処理などを内蔵）。ただし本番 DB での運用前にバックアップを推奨します。

---

必要であれば、README に次の内容も追加できます：
- 具体的な requirements.txt（依存ロック）
- ExecutionEngine / Broker の実装詳細と設定例
- CI / テストの実行方法
- デプロイ / systemd / コンテナ化の例

追加で含めたい情報や、運用手順（systemd ユニットファイルや Dockerfile 等）があれば教えてください。README を追記して整備します。