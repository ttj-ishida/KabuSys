# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買プラットフォーム（分析・ポートフォリオ構築・発注・監視・AI支援）のコア部分をまとめた Python パッケージです。README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- 市場データ（DuckDB）を使ったファクター計算・研究（research）
- ポートフォリオ構築・配分・サイズ決定（portfolio）
- 発注エンジン（ExecutionEngine）と発注周りの永続化（execution）
- 監視（MonitoringEngine）・リスク監視・アラート連携（monitoring）
- ニュースを LLM で解析する AI モジュール（ai）
- 環境設定ウィザード／検証ツールやユーティリティ（config, config_setup, validate_config, utils）
- ペーパートレード検証レポート生成ツール（tools）

設計での重要点：
- 本番・ペーパートレードの DB 分離（paper_trading モードでは data/paper_trading.db を使用）
- 監視は環境に関わらず本番の sqlite_path を参照（run_monitoring の仕様）
- OpenAI（gpt-4o-mini）を用いた記事センチメント・市場レジーム判定を実装（APIキー必要）
- ログはコンソール + 日次ローテートファイルへ出力（logs/<app>.log）

---

## 機能一覧

主な機能／モジュール

- config / config_setup
  - .env を対話式で生成・更新するウィザード
  - Settings クラスで環境変数を統一的に取得
- validate_config
  - .env / config/*.yaml の存在や値の簡易チェック
- execution
  - ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - Broker クライアントの分岐（KABUSYS_ENV=paper_trading は Mock）
  - 発注履歴・trade_logs 等の記録
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - Monitoring DB（SQLite）へのログ永続化（monitoring_db）
  - Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止を通知
  - run_monitoring.py：ポーリングループの起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
- portfolio
  - 候補選定、重み算出、ポジションサイズ計算、セクター制約、レジーム適応などの純粋関数群
- research
  - ファクター（momentum/value/volatility）計算、forward returns、IC 計算、統計サマリー
  - DuckDB 接続を受け取り SQL と Python で計算
- ai
  - news_nlp: raw_news を LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ma200 と LLM によるマクロセンチメントで日次レジーム判定
  - 失敗耐性（リトライ・フォールバック）設計
- tools
  - paper_verification_report: ペーパートレード DB から期間別の検証レポートを生成

ユーティリティ
- logging_setup: ルートロガーの統一設定（stdout + 日次ローテート）
- process_priority: Windows/Linux の差分を吸収したプロセス優先度設定

---

## セットアップ手順

前提
- Python 3.10+（型注釈に Union | 記法を使用）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai 等

1. リポジトリをクローン
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config 検証で YAML のパースチェックを行う場合）: pip install pyyaml
   - 他に Broker クライアント等の依存がある場合は個別に追加

4. ディレクトリ作成
   - data/ と logs/ を作成（logging_setup は自動作成を試みますが、権限等で失敗する可能性あり）
     - mkdir -p data logs

5. .env 作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（サンプルは下記）

例: 最小の .env（実際は必須トークン等を設定してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict オプションで警告を FAIL 扱いにできます

---

## 使い方

主要なエントリポイントと簡単な使用法を示します。

1. 環境確認
   - python -m kabusys.validate_config

2. ExecutionEngine（発注エンジン）の起動
   - 本番・ペーパーの切り替えは KABUSYS_ENV で指定
   - paper_trading の場合、MockBrokerClient を使用し DB は data/paper_trading.db に記録される
   - 起動:
     - python -m kabusys.run_execution
   - 実行中に停止させるには監視側が kill.flag を書き込むか、手動で stop フラグを作成:
     - data/stop_requested.flag を作成すると run_execution スレッドが検知して終了します
     - run_execution は実行中、data/execution.pid に PID を書き出します

3. Monitoring（監視）プロセスの起動
   - run_monitoring は Monitoring のポーリングループを起動します
   - 起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - デフォルトは 60 秒
   - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用して system_status や risk_logs を書き込みます（KABUSYS_ENV に依存しない）
   - 監視プロセスを停止したい場合: data/stop_requested.flag を作成すると監視ループが終了します

4. Paper Trading 検証レポート出力
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）

5. AI 関連
   - ニューススコアリング（news_nlp）やレジーム判定（regime_detector）は OpenAI API を利用します
   - 環境変数 OPENAI_API_KEY を設定するか、各関数へ api_key を渡してください
   - 例:
     - python スクリプト内で kabusys.ai.score_news(duckdb_conn, target_date, api_key="sk-...")

6. ログ
   - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
   - LOG_DIR 環境変数でログディレクトリを上書き可能
   - LOG_LEVEL 環境変数または .env の LOG_LEVEL でログレベルを指定

7. Kill Switch / Stop フラグ
   - KillSwitch は監視結果に基づいて data/kill.flag を作成し ExecutionEngine の停止をトリガーする仕組み
   - KillSwitch が書き込む条件の例: ドローダウン閾値超過、ポジション上限超過
   - 実行中に強制終了する場合は data/stop_requested.flag を作成（run_* スクリプトが検知してシャットダウン）

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ出力先）
- OPENAI_API_KEY（AI モジュール利用時に必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の MockBroker fill の挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアを防ぐ推奨: 0）

---

## ディレクトリ構成

リポジトリ内の主要なファイル／ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースの LLM スコアリング
    - regime_detector.py          — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/ (参照)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (runtime)
    - execution.log
    - monitoring.log
    - その他アプリログ

Note: 上記はコードベースのモジュール名・ファイル名を整理したものです。実際のサブモジュール（trade_monitor、alert_manager 等）はコードベース内に存在します（抜粋・参照）。

---

## 開発・運用のメモ

- 監視（monitoring）は production の sqlite_path を参照する設計です。テストや開発で監視を分離したい場合は設定を見直してください。
- Paper Trading は発注の完全分離を目的に data/paper_trading.db を使用します（KABUSYS_ENV=paper_trading）。
- OpenAI を使うモジュールは API 呼び出しの失敗に対してリトライ/フォールバックを行うよう設計されていますが、API キーの漏洩に注意してください。.env は絶対に Git にコミットしないでください。
- ログディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります。起動ユーザーの権限設定を確認してください。
- process_priority の設定は OS に依存します（psutil 経由）。権限不足で設定できない場合は警告で続行します。

---

必要があれば、以下について README を拡張できます：
- 具体的な .env.example（全キーと説明）
- systemd / supervisord 用のサービス定義例（運用手順）
- CI 用のテスト実行手順とモック方法（OpenAI 呼び出しのテスト化）
- API（BrokerClient）の実装/モックの詳細

ご希望があれば追記します。