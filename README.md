# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポーティング・研究ツールを含む自動売買基盤の一部実装です。OpenAI を使ったニュース NLP / レジーム判定機能や、Paper Trading 用モック、監視／Kill Switch 等の運用機能を備えます。

---

## 主な特徴（機能一覧）

- 環境管理
  - .env / .env.local 自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）
  - 設定ウィザード（`config_setup`）と事前検証ツール（`validate_config`）
- 実行エンジン
  - 発注処理の実行（ExecutionEngine 起動スクリプト）
  - Paper Trading モード（`KABUSYS_ENV=paper_trading`）では MockBrokerClient を使用し、本番 DB と分離された `data/paper_trading.db` に記録
  - PID ファイル管理（`data/execution.pid`）
- 監視（Monitoring）
  - システム状態（CPU/MEM/DISK）、データ鮮度、発注ログなどを定期ポーリングして SQLite に記録
  - Kill Switch（条件により `data/kill.flag` を作成して ExecutionEngine を安全に停止）
  - 監視ループ起動スクリプト（`run_monitoring.py`）。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- ポートフォリオ構築（純関数群）
  - 候補選別、均等／スコア加重配分、ポジションサイズ計算（ロット丸め、aggregate cap）
  - セクター上限・レジーム乗数適用
- 研究ツール（DuckDB ベース）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、統計サマリー
- AI 関連
  - ニュースを OpenAI (gpt-4o-mini) でセンチメント評価して `ai_scores` に書き込む（`ai.news_nlp`）
  - マクロセンチメントと ETF MA200 を組み合わせた市場レジーム判定（`ai.regime_detector`）
  - API 呼び出しはリトライ/バックオフ・JSON バリデーション・スコアクリップ等を実装
- ツール
  - Paper Trading 検証レポート生成（`tools.paper_verification_report`）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（型注釈に `X | Y` を使っているため）
- Git クローン済み（プロジェクトルートに `.git` または `pyproject.toml` があると自動で .env を読み込みます）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須ライブラリの例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config の YAML 検証に必要。なくても動くが検証がスキップされます）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば `pip install -r requirements.txt`）

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に `.env` を作成してください（`.env` は Git にコミットしないこと）。

4. 設定検証（必須項目の確認）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで以下のファイル/ディレクトリを使用します（必要に応じて .env で上書き）
     - data/kabusys.duckdb （DuckDB、環境変数: DUCKDB_PATH）
     - data/monitoring.db （監視用 SQLite、環境変数: SQLITE_PATH）
     - data/paper_trading.db （Paper Trading 用、環境変数: PAPER_TRADING_SQLITE_PATH）
     - data/execution.pid （ExecutionEngine の PID）
     - data/kill.flag （Kill Switch）
     - data/stop_requested.flag （run scripts が停止検知で参照）

6. ログ
   - デフォルトログディレクトリ: logs/
   - ログファイル: logs/<app_name>.log（ex: logs/execution.log）
   - 環境変数 LOG_DIR / LOG_LEVEL で変更可能

---

## 使い方（起動コマンド例）

- 環境変数読み込み（.env がある場合は自動で読み込まれます）
  - 自動ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 実行エンジン起動（Execution）
  - 本番 / 開発 / paper_trading は `KABUSYS_ENV` による
  - 起動:
    - python -m kabusys.run_execution
  - Paper Trading の場合:
    - export KABUSYS_ENV=paper_trading
    - 実行すると paper 用 DB に記録され、本番 DB と分離されます
  - 起動時に stop フラグが存在すると起動を行いません（data/stop_requested.flag）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き:
    - export MONITOR_POLL_INTERVAL=30  (秒)
  - 監視は環境に関係なく本番用 sqlite_path（Settings.sqlite_path）を使って監視データを永続化します
  - 停止フラグ（data/stop_requested.flag）を配置するとループは終了します

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn=duckdb_conn, target_date=date(YYYY, M, D), api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn=duckdb_conn, target_date=date(YYYY, M, D), api_key="...")

  OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。

---

## 主な環境変数（概要・デフォルト）

- 認証系
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使用する場合)

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（デフォルト 0）

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

---

## 運用上のファイルとフラグ

- data/kill.flag
  - Kill Switch が発動したときに書き込まれるファイル。ExecutionEngine はこのフラグを見て停止します。
  - 起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（本番では推奨しません）

- data/stop_requested.flag
  - run scripts（実行スクリプト）が外部から停止要求を受けたかどうかを判定するために参照するフラグファイル

- data/execution.pid
  - 実行エンジンが PID を書き込むファイル

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading の分離）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py — 共通ログ設定（コンソール + 日次ローテーションファイル）
    - process_priority.py — プラットフォーム差を吸収してプロセス優先度 / CPU affinity を設定

  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化と読み書きラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留・異常判定）  （実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — LINE 等への通知管理（実装ファイルがある場合の想定）

  - execution/
    - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー切替）
    - execution_engine.py — 発注実行エンジン（セッション管理）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注・リスク管理関連

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap、ロット丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC / 統計サマリー
    - （zscore_normalize 等の補助は data.stats から提供）

  - ai/
    - news_nlp.py — ニュース → OpenAI でセンチメント → ai_scores へ書き込み
    - regime_detector.py — ETF MA200 + マクロセンチメントで市場レジームを判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力

---

## 開発・デバッグのヒント

- ロギング
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を呼び出して統一されたログ出力を行います。`LOG_LEVEL` / `LOG_DIR` を調整してデバッグログを確認してください。

- テスト用モック
  - Paper Trading モードや `BrokerClientFactory` の Mock を活用すると実ブローカーに接続せずに発注ロジックの動作確認ができます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。既存 DB の後方互換処理が含まれます。

---

## ライセンス / 注意事項

- `.env` や API キーなどの秘密情報は絶対にリポジトリにコミットしないでください。
- 本システムは実際の資金を扱う設計を含みます。`KABUSYS_ENV=live` の設定や本番稼働時は十分なレビューとセーフガード（Kill Switch、監視、通知）を行ってください。

---

必要なら、README にサンプル .env のテンプレートや起動例の詳細（systemd / cron 用のユニット例、Dockerfile など）を追記します。どの情報を追加しましょうか？