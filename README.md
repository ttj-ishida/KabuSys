# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ README。  
この README はコードベース（src/kabusys 以下）を元に作成しています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト／コマンド）
- 主要環境変数 (.env)
- 停止・Kill スイッチについて
- ディレクトリ構成（概要）

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けライブラリ／運用スクリプト群です。  
主な責務は以下です。

- データ格納（DuckDB / SQLite）を用いたリサーチ・監視・発注履歴の永続化
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- リスク管理（ドローダウン・ポジション上限監視）
- 実行エンジン（ブローカークライアントを通した発注ループ）
- 監視エンジン（System / Trade / Risk の定期チェック、アラート・Kill Switch）
- Paper Trading 用の分離された環境と検証レポート生成ツール
- AI モジュール（ニュース NLP / レジーム判定）によるセンチメント分析（OpenAI 利用）

設計方針として、データベース分離（本番監視 DB と paper_trading DB の分離）、ルックアヘッドバイアス回避（日時参照の扱い）、およびフェイルセーフな API 呼び出し / リトライロジックを重視しています。

---

## 主な機能一覧

- 設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検査）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録
- 監視ループ起動スクリプト: run_monitoring.py
  - 定期的に System / Trade / Risk をチェックし、kill.flag を作成する可能性あり
- 監視 DB 層（SQLite）: monitoring_db.py（ログ・ダッシュボード・risk_logs 等）
- Risk Monitor / System Monitor / Trade Monitor / KillSwitch / MonitoringEngine
- ポートフォリオ構築モジュール（純粋関数）:
  - 選定: select_candidates
  - 重み計算: calc_equal_weights / calc_score_weights
  - ポジションサイズ: calc_position_sizes
  - セクター制限・レジーム乗数: apply_sector_cap / calc_regime_multiplier
- Research（DuckDB を利用したファクター計算）:
  - calc_momentum / calc_volatility / calc_value
  - 将来リターン・IC 計算など
- AI モジュール:
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores へ書き込み
  - regime_detector: マクロ + ETF MA200 を合成した日次レジーム判定
- Tools:
  - paper_verification_report: Paper Trading 結果から検証レポートを生成

---

## セットアップ手順（開発環境）

1. Python バージョンを用意（3.9+ を推奨。コード中の型注釈から 3.10+ が望ましい）  
2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表例。プロジェクトに requirements.txt があればそちらを使用）：
   - pip install duckdb psutil openai
   - （任意）PyYAML（config YAML のパース検証用）: pip install pyyaml
4. プロジェクトルートに .env を用意する：
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に作成
5. データディレクトリとログディレクトリが自動作成されますが、権限等に注意してください。
6. OpenAI を利用する場合は OPENAI_API_KEY を設定してください（AI モジュールで使用）。

---

## 使い方（主要スクリプト／コマンド）

- 設定ウィザード（.env を対話式で作成）
  - python -m kabusys.config_setup
  - 引数: --env-file で保存先を指定可能

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止: data/stop_requested.flag を作成するとループは終了する（run_execution で監視）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は Settings.sqlite_path（監視用 DB）を常に使用（環境に依らず本番 sqlite_path を参照）

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で DB パス指定可能。デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - AI モジュールは OpenAI API（gpt-4o-mini 等）を使用します。環境変数 OPENAI_API_KEY を設定してください。
  - score_news / score_regime 等の関数は DuckDB コネクションと target_date を与えて呼び出します。

ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（TimedRotatingFileHandler）。ログディレクトリは環境変数 LOG_DIR で変更可能。

---

## 主要環境変数（.env に設定する項目の例）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（代表的なもの）:
- KABUSYS_ENV = development | paper_trading | live
- DUCKDB_PATH = data/kabusys.duckdb
- SQLITE_PATH = data/monitoring.db
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR
- LOG_DIR = logs
- PID_FILE_PATH = data/execution.pid
- KILL_FLAG_PATH = data/kill.flag
- KILL_FLAG_CLEAR_ON_START = 0 | 1
- MONITOR_POLL_INTERVAL = (監視ポーリング間隔 秒、デフォルト 60)
- PAPER_FILL_MODE = instant | partial | never | reject (paper_trading の約定モード)
- OPENAI_API_KEY =（AI モジュール利用時に必須）

注:
- .env 自動ロード: プロジェクトルートに .env / .env.local があれば自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 機密値（トークン・パスワード等）は .env に保存し、絶対に Git にコミットしないでください。

---

## 停止・Kill スイッチについて

- 停止フラグ（実行中の run_execution / run_monitoring を外部から停止するためのファイル）
  - data/stop_requested.flag : run_execution / run_monitoring が監視している停止フラグ（存在するとループを終了）
  - 手動停止例: touch data/stop_requested.flag

- Kill Switch（自動的に ExecutionEngine を停止させる安全機構）
  - KillSwitch は監視結果（ドローダウン過大、ポジション上限超過 等）を評価して data/kill.flag を書き込みます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動で消去します（本番では 0 推奨）。
  - kill.flag が存在すると起動時にエンジンの開始を拒否する設計（安全確保）。

---

## 開発者向けメモ

- プロセス優先度:
  - run_execution / run_monitoring 起動時に set_process_priority("high") を試行します（psutil 経由）。権限により失敗しても警告を出して継続します。
- Logging:
  - setup_logging(app_name=...) を各起動スクリプトで呼び出し、統一的なログ出力を実現しています。
- DB 初期化:
  - Monitoring DB のスキーマ初期化は init_monitoring_db(sqlite_conn) で安全に行います（冪等）。
- Paper Trading:
  - paper_trading モードでは MockBroker を使い、本番 DB と分離して data/paper_trading.db に記録するため実環境への影響がありません。

---

## ディレクトリ構成（src/kabusys の主要ファイル/モジュール）

以下はコードベース（今回提供されているファイル）に基づく簡易ツリーと説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）→ ai_scores 書込
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB レイヤ（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （未展示ファイルだが存在する想定）取引監視ロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（ポーリング）
    - kill_switch.py — 実行停止フラグの管理
    - alert_manager.py — （未展示）アラート送信管理（LINE 等）
  - execution/
    - execution_engine.py — 実行エンジン本体（run_session 等）
    - broker_factory.py — Broker クライアント生成（Mock / 実 API 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの実装群
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割付
    - risk_adjustment.py — セクター制限・レジーム乗数
    - __init__.py — 主要関数の再エクスポート
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py — ルートロガー設定（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py

（上記はコードベースの抜粋に基づいてまとめたものです。実際のリポジトリにはさらにファイル・フォルダが存在する可能性があります。）

---

## 付録：よく使うコマンドサンプル

- .env を対話的に作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視エンジン起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

必要に応じて README の内容をプロジェクト固有の README.md 形式に合わせて調整できます（インストール要件の明示、CI / デプロイ手順、詳細な設定例など）。追加で記載したい項目があれば教えてください。