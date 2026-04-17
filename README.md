# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 実行スクリプト群）。  
この README はリポジトリ内の主要コンポーネントと実行手順（セットアップ、使い方、ディレクトリ構成）を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究ワークフローを提供する Python ベースのシステムです。主要な機能群は以下を含みます：

- 実取引（kabuステーション）／ペーパートレード用の ExecutionEngine
- 実行・取引状況の監視（MonitoringEngine）
- ポートフォリオ構築、ポジションサイジング、リスク調整ロジック（純粋関数群）
- DuckDB を使ったファクター計算・リサーチ機能
- ニュースの LLM（OpenAI）を使ったセンチメント分析と市場レジーム判定
- 簡易 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計上の特徴：
- Paper trading は本番データベースと明確に分離（PAPER_TRADING_SQLITE_PATH）
- .env 自動ロード機能（プロジェクトルートの .env / .env.local）
- look-ahead バイアスを避ける実装方針（外部に時刻を依存しない設計）
- フェイルセーフ（API 失敗時のフォールバック、監視による Kill Switch 等）

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine（発注・リスク管理・注文管理・再整合）
  - BrokerClientFactory（KABUSYS_ENV に応じた Broker の切替：本番 / Mock）
- Monitoring
  - SystemMonitor：プロセス存在・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン／ポジション数監視
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB：SQLite での監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio（純粋関数）
  - 候補選定、等重・スコア重み、セクターキャップ、レジーム乗数、株数計算（単元丸め含む）
- Research
  - ファクター（Momentum / Volatility / Value）計算（DuckDB）
  - 将来リターン・IC・統計サマリ
- AI 系（OpenAI）
  - news_nlp.score_news：ニュースを集約して銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime：ETF とマクロニュースを組み合わせて market_regime を判定
- Tools
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します（推奨）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な依存パッケージをインストールします（requirements.txt / pyproject.toml がある想定）。
   - 例（最低限）:
     - pip install duckdb psutil openai
   - 追加（任意）:
     - PyYAML（config の YAML 検証に使用）
     - テストや開発用のパッケージは別途追加

3. .env ファイルを用意する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに `.env` を置き、必要な環境変数を設定してください。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   - OPENAI_API_KEY（AI 機能を使う場合は必須）
   - その他はデフォルト値があるか任意

5. .env 自動読み込み
   - デフォルトではプロジェクトルート（.git または pyproject.toml に依存）を検出して自動的に `.env` / `.env.local` を読み込みます。
   - 自動読み込みを抑止する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. DB ファイル位置（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH または環境変数で変更可）

注意:
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。

---

## 設定検証

作成した .env や config/*.yaml の検証を行うには:

- 設定検証 CLI（警告 / エラーを表示）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

validate_config は必須環境変数や DB パス・YAML の構文などをチェックします。PyYAML がインストールされていない場合、YAML の検証はスキップされ、警告が出ます。

---

## 使い方（主要コマンド）

1. ExecutionEngine を起動する
   - 本番 / ペーパートレードは KABUSYS_ENV で切替
   - 実行:
     - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading.db に記録します（本番 DB と完全分離）。
     - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
     - 実行中は data/execution.pid に PID を書きます（SystemMonitor がプロセス存在を確認します）。
     - 止めたい場合は data/stop_requested.flag を作成するか、Monitoring の Kill Switch で data/kill.flag を書き込ませる。

2. Monitoring を起動する
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを保存します。
     - 停止フラグ（data/stop_requested.flag）を基にループを抜けます。

3. Paper Trading 検証レポートの生成
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション例:
       - --from YYYY-MM-DD --to YYYY-MM-DD
       - --db PATH で SQLite DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
   - 出力: 稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定

4. AI 機能（ニュース NLP・レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡し、OpenAI API を使って銘柄別センチメントを ai_scores に書き込みます。
     - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します（未設定だと例外）。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF (1321) の MA200 とマクロニュースを組み合わせて market_regime テーブルに書き込みます。
   - OpenAI のエラー（レート制限、ネットワークなど）はリトライや安全側フォールバックがありますが、API キーの管理に注意してください。

5. .env 設定ウィザード（初期セットアップ）
   - python -m kabusys.config_setup
   - 対話形式で .env を生成または更新できます。

---

## 主要な環境変数（要点）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用、DB は paper_trading.db
  - live: 本番モード（通知・Kill Switch 設定を十分確認すること）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB。デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1。本番では 0 推奨）

---

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 書込ロジック
    - regime_detector.py     — レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 & 永続化層
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 滞留注文・約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 監視コンポーネント束ねるエンジン
    - kill_switch.py         — Kill Switch 管理（データファイルによる停止）
    - alert_manager.py       — 通知送信（LINE 等のラッパー、未掲示の実装）
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory 等) — 発注関連（詳細は該当モジュール）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — IC/将来リターン/統計サマリ
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity のユーティリティ

データ・PID・フラグ用ディレクトリ（プロジェクトルート）
- data/
  - execution.pid            — ExecutionEngine が書き込む PID（存在でプロセス判定）
  - kill.flag                — Monitoring や KillSwitch が書き込む停止フラグ（Execution 停止）
  - stop_requested.flag      — 手動でループ停止を要求するためのフラグ
  - monitoring.db / paper_trading.db / kabusys.duckdb など（DB ファイル）

---

## 運用上の注意点・トラブルシュート

- データベース・ファイルパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、事前に data ディレクトリを作成しておくと安全です。
- Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を参照します（監視ログは本番 DB に残すため）。
- Paper trading は本番 DB と完全分離されるよう設計されています（settings.is_paper 経由で paper_sqlite_path を使用）。
- OpenAI API を使う機能は API キー必須。API コールはレート制限やネットワークエラーに対するリトライ処理を実装していますが、クォータに注意してください。
- validate_config で警告が出た場合、特に KABUSYS_ENV=live のときは設定を厳格に見直してください。
- process_priority の設定は権限や OS に依存して失敗する可能性があり、その場合は警告でスキップされます（エラーにはならない）。

---

## 開発・拡張のヒント

- 各モジュールは可能な限り副作用を排しており、純粋関数（portfolio 等）と I/O 層（DB / Broker クライアント）を分離しています。ユニットテスト作成が容易です。
- OpenAI を叩く箇所は内部的に API 呼び出しラッパー（_call_openai_api）を用意してあり、テスト時は unittest.mock.patch で差し替え可能です。
- MonitoringDB はスキーママイグレーションを簡易に行う処理を含んでいます（列追加の自動化など）。

---

必要に応じて、特定のモジュール（ExecutionEngine の起動オプションや Broker の設定、AlertManager の詳細、OrderRepository の API 等）についての README 追記・サンプルコマンドや環境変数説明を追加できます。どの部分を詳しく書けばよいか教えてください。