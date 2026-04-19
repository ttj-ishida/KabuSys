# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・運用ツール群）。  
この README はコードベースの主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／モニタリングを目的とした Python 製システムです。  
主な機能群は次の通りです。

- 実行エンジン（ExecutionEngine）: ブローカーと連携して発注・約定管理を行う（本番／ペーパートレード対応）
- 監視（Monitoring）: システム稼働状況、データ鮮度、注文状態、リスク指標を定期ポーリングで監視しログ／アラートを出す
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ等
- リサーチ: DuckDB 上の時系列データを用いたファクター計算（モメンタム・バリュー・ボラティリティ等）
- AI モジュール: ニュースの NLP スコアリングや市場レジーム判定（OpenAI API 利用、フェイルセーフ設計）
- 運用ツール: Paper Trading 検証レポート生成、.env 作成ウィザード、設定検証 CLI など
- 共通ユーティリティ: ロギング設定、プロセス優先度制御、設定読み込み等

設計方針として、DuckDB/SQLite をデータ層に使用し、外部 API 呼び出しは明示的に管理（OpenAI、kabu API、J-Quants 等）。運用時の安全策（Kill Switch、停止フラグ、リスク監視、ログローテーション等）を備えています。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine 起動（KABUSYS_ENV に応じて paper/live/development 動作）
  - python -m kabusys.run_monitoring : SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可）
- 設定関連
  - config_setup.py : 対話式 `.env` ウィザード（python -m kabusys.config_setup）
  - validate_config.py : 起動前設定検証 CLI（python -m kabusys.validate_config）
  - Settings クラスで環境変数を集中管理（自動 .env ロード機能あり）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - 監視ログ永続化（SQLite）: monitoring_db.py（system_status / trade_logs / risk_logs / positions / dashboard）
  - kill.flag / stop_requested.flag を用いる安全停止
- ポートフォリオ構築
  - 候補選定、等重／スコア加重、リスクベース等のポジションサイズ計算、セクターキャップ適用
- リサーチ
  - calc_momentum / calc_volatility / calc_value 等（DuckDB 上で動作）
  - forward_returns / IC 計算 / 統計サマリ
- AI（OpenAI）
  - ニュースセンチメントのスコア化（gpt-4o-mini 等、JSON Mode を利用）
  - 市場レジーム判定（ETF MA とマクロニュースを合成）
  - API 呼出しはリトライ・バックオフ・バリデーションを備えフェイルセーフ化
- ツール
  - Paper Trading 検証レポート（期間指定可）: kabusys.tools.paper_verification_report

---

## 前提・依存関係

- Python 3.10+（型アノテーションなどを利用）
- 推奨パッケージ（requirements.txt がない場合は手動インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証の YAML 検査を行う場合に必要）
- 組み込み: sqlite3（標準ライブラリ）
- 実運用では kabuステーション／J-Quants 等の資格情報が必要

---

## 環境変数（主なもの）

必須（運用により変動）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト値あり／推奨設定）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI 呼び出し用（AI モジュールで必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60） — run_monitoring で参照
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant|partial|never|reject）

設定ファイル: プロジェクトルートの `.env` / `.env.local`（config_setup で生成可能）。自動ロードは Settings モジュールが行います（環境変数優先）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd repository

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを利用）

4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を作成して必要なキーを設定。
   - 重要: `.env` は絶対に Git にコミットしないでください（config_setup も同旨の警告を出します）。

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB/ログ保存先は `data/` と `logs/` です。起動時に自動作成されますが権限を確認してください。

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（主なコマンド・例）

- ExecutionEngine（エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され記録は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に行われ、本番 DB と分離されます。
    - 起動時に STOP フラグ（data/stop_requested.flag）が存在すると起動をスキップします。
    - 実行中は data/execution.pid が使用されます（PID ファイル）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
  - 実行中、data/stop_requested.flag を作成すると安全にループを終了します。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI モジュール（プログラムから利用）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数か引数で渡す）

停止・強制停止の仕組み:
- stop_requested.flag: run_* スクリプトループを優雅に終了させるために使われます（data/stop_requested.flag）。
- kill.flag: KillSwitch が書き込むフラグで ExecutionEngine に停止シグナルを送る（Settings.kill_flag_path、デフォルト data/kill.flag）。KillSwitch はリスク条件（ドローダウン、ポジション上限等）で発動します。

ログ:
- ログは stdout とファイル（logs/<app_name>.log）へ出力され、日次ローテーション（30 日分保持）されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。

---

## Directory 構成（主要ファイル・モジュール）

ルート: src/kabusys 以下

- __init__.py
- config.py
  - Settings クラス、.env 自動読み込みロジック
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ初期化（stdout + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度 / CPU affinity 操作（psutil ベース）
- monitoring/
  - monitoring_db.py — SQLite 監視ログテーブル初期化 + MonitoringDB 操作
  - system_monitor.py — システム稼働・データ鮮度チェック
  - trade_monitor.py — 注文滞留や約定異常の検出（コード参照）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の書き込み・管理
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py —（アラート送信などの実装がある想定）
- execution/
  - execution_engine.py, order_manager.py, broker_factory.py, order_repository.py, reconciler.py, risk_manager.py など（実際の発注ロジック・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 発注株数計算・集約 cap ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュース NLP スコア（OpenAI API）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース + LLM）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（上記は主要ファイルを抜粋した構成です。詳細は src/kabusys 以下のモジュール実装を参照してください。）

---

## 運用上の注意・ベストプラクティス

- .env の管理
  - 機密情報は .env に保存し、絶対に Git にコミットしないでください。
  - `.env.local` はローカル上書き用に使えます（自動ロード順: OS 環境 > .env.local > .env）。
- 本番設定
  - KABUSYS_ENV=live を設定すると本番モードになります。LINE 通知や Kill Switch 設定を確認してください。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にしないこと（デフォルト 0 が推奨）。
- OpenAI / API 使用
  - AI モジュールは OpenAI を利用します。API レスポンスのバリデーション・リトライ処理が実装されていますが、API キーの漏洩やコストに注意してください。
- DB 分離
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH に記録し、本番 DB と分離されます。
- ログ・監視
  - ログディレクトリの書き込み権限を確認してください。logs/ の作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。
- 停止方法
  - 運用停止は data/stop_requested.flag を作成するか、エンジン側に用意した停止 API を利用してください。KillSwitch は致命的リスク判定時に data/kill.flag を書き込みます。

---

## 開発者向けヒント

- 単体関数設計:
  - portfolio/*.py、research/*.py 等の多くは純粋関数（副作用なし）で書かれておりユニットテストが書きやすい設計です。
- テスト:
  - OpenAI 呼び出し部分はラップされているため、unit test では _call_openai_api を patch することで外部依存を遮断できます。
- DuckDB:
  - research / ai モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて計算します。ローカルでのデータ準備（prices_daily / raw_financials / raw_news 等テーブル）を用意して動作確認してください。

---

必要であれば、以下のテンプレート .env（例）を提供します。実運用では値を適切に差し替えてください。

例 (.env.template)
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_key_here
KILL_FLAG_CLEAR_ON_START=0
```

---

他に README に含めたい内容（例: デプロイ方法、systemd ユニット例、詳細な DB スキーマ、API 扱い方の例）があれば教えてください。必要に応じて追加で追記します。