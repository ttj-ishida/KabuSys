# KabuSys

日本株向け自動売買システムの一部コンポーネント群（設定管理、監視、実行エンジン、ポートフォリオ構築、リサーチ、AI ユーティリティ等）。

この README はリポジトリに含まれる主要スクリプト／モジュールの使い方、設定、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する複数のモジュールを持つコードベースです。主な役割は次のとおりです。

- 環境変数 / .env 管理（対話式ウィザード、読み込み、検証）
- ExecutionEngine（実際の発注ロジック / リスク管理 / 注文管理）
- Monitoring（システム状態、注文・リスクの監視、Kill Switch）
- Portfolio コンポーネント（候補選定、配分、ポジションサイズ計算、リスク調整）
- Research（ファクター計算・特徴量解析）
- AI ユーティリティ（OpenAI を使ったニュース感情スコア、レジーム判定）
- ユーティリティ（ロギング設定、プロセス優先度など）
- ツール（ペーパートレード検証レポート等）

設計上の特徴：
- .env ファイルから環境変数を自動読み込み（必要に応じて無効化可能）
- Paper Trading 時は実際のブローカーとは切り離して専用の SQLite を使用
- DuckDB を分析用途に使用
- OpenAI を利用する機能は API キーが必要。失敗時はフェイルセーフの振る舞いをする

---

## 機能一覧（主要機能）

- 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式で作成）
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- Portfolio 建設: 候補選定・等重/スコア重み・ポジションサイズ計算・セクター上限・レジーム乗数
- Research: ファクター計算（モメンタム／バリュー／ボラティリティ等）、将来リターン、IC 計算、統計サマリ
- AI 機能:
  - kabusys.ai.score_news — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - kabusys.ai.regime_detector — ETF + マクロニュースで市場レジーム ('bull'/'neutral'/'bear') を算出し保存
- ユーティリティ:
  - 統一ログ設定（console + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity の設定

---

## セットアップ手順

下記は導入のための基本手順です。実行環境（Linux/Windows/Mac）に合わせて適宜調整してください。

1. Python と仮想環境の準備
   - Python 3.9+ 推奨
   - 仮想環境を作成・有効化（例: python -m venv .venv; source .venv/bin/activate）

2. 依存パッケージのインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査を有効にする場合）
   - 具体的には requirements.txt があればそれを使います。ない場合は手動で:
     - pip install duckdb psutil openai pyyaml
   - sqlite3 は Python 標準に含まれます。

3. ディレクトリ準備
   - data/ と logs/ は自動作成されますが、必要に応じて手動で作成可能:
     - mkdir -p data logs

4. .env の用意
   - 対話式ウィザードで作る（推奨）:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に `JQUANTS_REFRESH_TOKEN`、`KABU_API_PASSWORD` 等の必須値を設定してください。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 本番前に --strict を付けて警告を FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

6. OpenAI 機能を使う場合
   - 環境変数 `OPENAI_API_KEY` に API キーを設定
   - AI 機能は外部 API に依存するため、ネットワーク・課金に注意

---

## 主要な環境変数

（重要なもの／デフォルトを抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 default: data/paper_trading.db)
- ログ
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- 監視 / 実行関連
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1, default: 0)
  - MONITOR_POLL_INTERVAL (run_monitoring でポーリング間隔を秒で上書き)
- Paper Trading の挙動
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- OpenAI
  - OPENAI_API_KEY (AI 機能を利用する場合に必須)
- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）

補足: .env および .env.local はプロジェクトルート（.git または pyproject.toml を基準）から自動ロードされます。OS 環境変数は優先されます。

---

## 使い方（起動・コマンド一覧）

基本的なエントリポイントはモジュールとして実行します（パッケージとしてインストールしていない場合はプロジェクトルートから実行）。

1. 環境ファイルの作成（推奨）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 本番前に: python -m kabusys.validate_config --strict

3. ExecutionEngine（注文実行）を起動
   - 実行:
     - python -m kabusys.run_execution
   - Paper Trading の場合は環境変数を設定:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - この場合、Paper Trading 用に MockBroker を使い、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録します。
   - 停止シグナル:
     - 実行中にプロセスを止めるには data/stop_requested.flag を作成するか、ExecutionEngine の PID ファイルを参照してプロセスにシグナルを送る等が可能。
     - KillSwitch が発動すると data/kill.flag が作成され、次回の起動や監視で検出されます。

4. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔変更:
     - export MONITOR_POLL_INTERVAL=30  （秒）
   - 監視は monitoring DB（settings.sqlite_path）へログを書き込みます（monitoring は環境に関係なく本番 sqlite_path を使用する仕様）。
   - run_monitoring はプロセス優先度を high に設定してから開始します（set_process_priority）。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - 引数 --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH かデフォルトを使う）

6. AI 機能（プログラム API）
   - ニューススコアリング: kabusys.ai.score_news（DuckDB 接続と日付を渡して実行）
   - レジーム判定: kabusys.ai.regime_detector.score_regime（同上）
   - これらはプログラムから呼び出す関数です。OPENAI_API_KEY が必要（関数引数からも渡せます）。

---

## 停止 / Kill Switch / フラグファイル

- 停止要求（run_monitoring / run_execution など）は stop_requested.flag（data/stop_requested.flag） を監視して停止します。
- 安全停止のための Kill Switch:
  - KillSwitch は監視結果を評価して data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START に応じて kill.flag の自動クリアを制御できます（本番では 0 推奨）。
- PID ファイル:
  - 実行プロセスは data/execution.pid を書きます（run_execution の EngineConfig 等で使用）。

---

## 実装上の注意 / 運用メモ

- Monitoring は常に本番 sqlite_path を参照してログを書きます（環境に依存しない）。
- run_execution は paper_trading の場合に paper_sqlite_path を使用して DB を分離します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力され、コンソール出力は stdout に出ます。
- DB スキーマの互換性:
  - monitoring_db.init は必要に応じてテーブル追加・マイグレーション（例: latency_ms、peak_value の追加）を行うよう実装されています。
- OpenAI API 呼び出しは外部依存（ネットワーク、課金）です。失敗時にはフェイルセーフとしてスコアをデフォルト値にフォールバックしたり、部分的にスキップします。

---

## ディレクトリ構成（抜粋）

リポジトリの主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py      — 統一ログ設定
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite による監視ログ永続化
    - system_monitor.py     — システム状態 / データ鮮度監視
    - trade_monitor.py      — （注文関連の監視ロジック）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （アラート送信管理：LINE 等）
  - execution/
    - execution_engine.py   — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

（上記は主要ファイルの抜粋です。細かいユーティリティや追加モジュールも含まれます。）

---

## 参考コマンドまとめ

- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視エンジン起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（プログラム呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)

---

## 最後に / 運用上の推奨

- production（KABUSYS_ENV=live）では .env を厳重に管理し、KILL_FLAG_CLEAR_ON_START を 0 にするなど安全策を取ること。
- validate_config を導入前・起動前に必ず実行して設定不備を検出すること。
- OpenAI を運用で使う場合は API 利用料とレート制限に注意し、監視を行うこと。
- logs/ と data/ のバックアップやパーミッション管理を適切に行ってください。

---

この README はリポジトリ内のコード（主要スクリプト）を元にした概要です。実際の運用や拡張については各モジュールの docstring（ソース内の説明）を参照してください。質問や追加のドキュメント化が必要であれば教えてください。