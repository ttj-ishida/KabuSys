# KabuSys

日本株自動売買システムの軽量ライブラリ群および実行用スクリプト群。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジンの補助、監視、及びリサーチ用ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

- 主な目的は日本株向けの自動売買フレームワークのユーティリティ群を提供することです（戦略の実装・ポートフォリオ構築・発注管理・監視・リサーチ・AI を用いたニュース分析など）。
- 実行スクリプトは本番／ペーパートレードで分離された DB を用いるなど、安全に配慮した設計になっています。
- DuckDB を分析用に用い、SQLite を監視・トレードログ保存用に用います。
- OpenAI（LLM）連携機能はニュースのセンチメント付与や市場レジーム判定に利用します（任意）。

---

## 主な機能一覧

- 環境設定・管理
  - .env の自動読み込み（プロジェクトルート検出）と対話式ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper DB に記録（本番 DB と分離）
    - 停止フラグ（data/stop_requested.flag / data/kill.flag）により安全に停止
  - Monitoring ポーリング（run_monitoring.py）
    - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し kill switch を判定
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）

- 監視永続化（monitoring）
  - SQLite ベースの monitoring DB 初期化・アクセス層（monitoring_db.py）
  - ドローダウン監視・ポジション上限チェック（risk_monitor.py）
  - Kill Switch（kill_switch.py）

- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア重み付け（portfolio_builder.py）
  - セクター制限・レジーム乗数（risk_adjustment.py）
  - 発注株数算出（position_sizing.py）

- リサーチ（research）
  - ファクター計算（momentum / volatility / value 等、DuckDB を使用）
  - 将来リターン・IC 計算・統計サマリー（feature_exploration.py）

- AI（任意）
  - ニュース NLP による銘柄別センチメント付与（ai/news_nlp.py）
  - 市場レジーム判定（ai/regime_detector.py）
  - OpenAI API（gpt-4o-mini を想定）を利用（API キー必須）

- ツール
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）

- ロギング / プロセス制御
  - 統一的ログ設定（utils/logging_setup.py） → console + 日次ローテートファイル（logs/）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

---

## セットアップ手順（開発 / 実行前）

1. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 必須（概ね）: duckdb, psutil, openai
   - 任意: PyYAML（config 検証で YAML を検査する場合）
   例:
   - pip install duckdb psutil openai PyYAML

   （本リポジトリに requirements.txt がない場合は用途に応じて必要パッケージを追加してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動でファイルを作成（プロジェクトルートに `.env`）。
   - .env の自動ロードは、デフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 重要な環境変数（抜粋）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境切替:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading: MockBroker を利用し `data/paper_trading.db` 等を使用
       - live: 実際の発注を行います（注意）
   - ログ / DB:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
   - OpenAI（AI 機能を使う場合）
     - OPENAI_API_KEY

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

---

## 使い方（代表的コマンド）

- 設定ウィザード（.env を対話的に作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 必要なら厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します
    - 実行中は data/execution.pid に PID を書く想定
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に完全分離して記録

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセスは常に本番 sqlite_path（SQLITE_PATH）を参照します（監視データは本番 DB に残る設計）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY 環境変数を設定して利用
  - ai.score_news / ai.regime_detector は DuckDB 接続を受け取る関数 API のため、スクリプトやジョブ内から呼び出してください（例: スケジューラで日次実行）。

---

## 動作上の注意 / 運用メモ

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を読み込みます。
  - OS 環境変数は保護され、.env.local の override でも上書きされません（protected 機構）。

- ログ
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler: 日次ローテーション、30世代保持）と stdout の併用。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

- 停止・Kill Switch
  - 監視モジュールはドローダウンやポジション上限超過を検出すると data/kill.flag を書き込むことで ExecutionEngine 停止指示を出します。
  - ExecutionEngine は起動時やランタイムで stop フラグを監視し、安全にシャットダウンします。
  - KILL_FLAG_CLEAR_ON_START=1 を本番（live）で設定すると危険です（自動クリアされるため）。デフォルトは 0。

- DB マイグレーション / 互換性
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・必要カラム追加を行います（シンプルなマイグレーション対応あり）。

- 実行優先度 / リソース制御
  - 起動スクリプトは最初にプロセス優先度を `high` に設定しようとします（psutil を使用）。権限不足時は警告を出してスキップします。

- テスト / 開発
  - many 関数は外部副作用を持たない純粋関数（portfolio, research 等）として設計されておりユニットテストが容易です。
  - AI 呼び出し部分は単体テスト用に _call_openai_api を patch することを想定しています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor 等の実装ファイル)
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
  - (その他: execution/*, data/* などのモジュールやスクリプトが存在)

- data/
  - デフォルトの DB（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
  - stop_requested.flag / kill.flag / execution.pid などの制御ファイル

- logs/
  - ログファイルが出力される（設定により変更可能）

---

## よくある質問（FAQ）

Q: paper_trading と live の違いは？
- paper_trading: MockBrokerClient を使い、発注は仮想的に処理。データは paper_trading 専用 DB に記録され本番 DB とは分離されます。
- live: 実際のブローカー API を叩いて発注します。設定ミスで実売買が発生する可能性があるため注意が必要です。

Q: デフォルトの DB パスは？
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db

Q: OpenAI を利用するには？
- 環境変数 OPENAI_API_KEY を設定してください。AI 関連処理は失敗時フォールバックやリトライを実装していますが、API キー未設定の場合は該当関数が ValueError を投げます。

---

以上が README の要点です。運用やデプロイに関して詳しい手順（systemd/cron/コンテナ化など）が必要であれば、実行環境（Linux distro / コンテナの有無 / CI/CD）に合わせた起動例・ユニットファイルの雛形を追加で作成します。必要なら教えてください。