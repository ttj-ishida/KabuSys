# KabuSys

日本株向け自動売買システムのリポジトリ（部分抜粋）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて、ローカルでのセットアップ・実行方法、主要機能、ディレクトリ構成などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究を目的としたシステム群です。  
主な役割は次のとおりです。

- 市場データや財務データを使ったファクター計算・特徴量探索（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 実行エンジン（ExecutionEngine）による発注管理（execution／本番・ペーパー両対応）
- 監視（monitoring）・アラート・Kill Switch（運用安全機構）
- ニュースを用いた LLM（OpenAI）ベースの NLP スコアリング（ai）
- ペーパートレード検証レポート生成ツール（tools）

設計上のポイント：
- 環境は .env または環境変数で設定（config モジュール）
- Paper Trading（分離された SQLite DB）と Live（本番）を区別
- DuckDB を分析用 DB、SQLite を監視／履歴用に使用
- ロギングは統一的に設定（logs/<app>.log、日次ローテーション）

---

## 主な機能一覧

- 設定ウィザードで .env を対話的に生成: `kabusys.config_setup`
- 設定検証 CLI: `kabusys.validate_config`
- ExecutionEngine 実行スクリプト（本番 / ペーパー切替対応）: `run_execution.py`
- Monitoring ポーリングループ: `run_monitoring.py`
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
- 監視用 DB（SQLite）操作ラッパー: monitoring.monitoring_db
- リスク監視（ドローダウン・ポジション上限）: monitoring.risk_monitor
- Kill Switch（data/kill.flag の作成で Execution 停止）: monitoring.kill_switch
- ニュース NLP スコアリング（OpenAI）: ai.news_nlp
- 市場レジーム判定（LLM + MA200 組合せ）: ai.regime_detector
- ポートフォリオ構築、ウェイト算出、ポジションサイズ決定: portfolio/*
- 研究用ファクター計算・IC 計算等: research/*
- ペーパートレード検証レポート生成ツール: tools/paper_verification_report.py
- プロセス優先度・CPU affinity 設定ユーティリティ: utils/process_priority.py
- ロギングセットアップ: utils/logging_setup.py

---

## 必要要件

- Python 3.10+（typing に | 型注釈が使われているため）
- 推奨ライブラリ（抜粋）:
  - duckdb
  - psutil
  - openai（ai 機能を使う場合）
  - PyYAML（config 検証で YAML を検証したい場合）
- （任意）仮想環境：venv / poetry 等

requirements.txt がプロジェクトにある場合はそちらを使用してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / 配置
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - または必要なパッケージを個別に：`pip install duckdb psutil openai pyyaml`
4. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワードなど必須項目を入力
5. 設定検証（必須項目やファイル配置を確認）
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正
6. ディレクトリ確認
   - data/ （SQLite 等を置く。scripts が自動作成することもある）
   - logs/ （ログファイル出力先）

---

## 環境変数（主な一覧）

以下は重要な環境変数とデフォルト値の抜粋です（.env に設定してください）。

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB。デフォルト: data/paper_trading.db
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — デフォルト INFO
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 任意（通知用）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

注意: .env は絶対にソース管理にコミットしないでください（秘密情報を含むため）。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで終了コード 1

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能（デフォルト 60 秒）
  - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することでループを抜けます

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（--db で上書き可）

- ai/news_nlp, ai/regime_detector などはプログラム内 API（関数）として呼び出します。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...) など

---

## 運用上の注意 / 停止方法

- 停止フラグ（run_execution / run_monitoring）
  - プロセス停止要求: プロジェクトルートの data/stop_requested.flag を作成すると、起動スクリプトが検知して終了します。
- Kill Switch（強制停止）
  - monitoring.kill_switch が条件を満たすと data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、ExecutionEngine 起動時に kill.flag を自動でクリアする設定になるため、本番では 0 を推奨します。
- PID ファイル
  - ExecutionEngine は data/execution.pid を使用 / 作成します（プロセス管理に利用）。
- ログ
  - logs/<app_name>.log に日次ローテーションで出力（utils.logging_setup 設定）。コンソールは stdout に出力。

---

## ディレクトリ構成（主要ファイル抜粋）

リポジトリの src/kabusys 配下に主要モジュールが配置されています。以下は抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings 管理（自動 .env ロード含む）
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - execution/                   — 実行エンジン関連（発注、注文管理、risk 等）
    - monitoring/
      - monitoring_db.py           — SQLite 監視 DB 用ユーティリティ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に使用されるディレクトリ: DB, フラグ, PID 等)
    - config/ (YAML 設定ファイル群、生成スクリプトが存在する想定)

（注）上記は本リポジトリ内のモジュール実装に基づく抜粋です。実際のファイル数・構成は完全なリポジトリに依存します。

---

## 開発・デバッグのヒント

- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で変更できます。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で調整（60 秒がデフォルト）。
- Paper Trading と Live は DB を分離しているため、実運用時は環境変数 KABUSYS_ENV を適切に設定してください。
- AI 関連（OpenAI）を使う場合は OPENAI_API_KEY を必ず設定してください。API 呼び出しはリトライやフェイルセーフが入っていますが、API 費用・レートに注意してください。
- settings 取得例（コード内）:
  - from kabusys.config import settings
  - settings.sqlite_path, settings.duckdb_path, settings.is_paper などが利用可能

---

## 参考コマンドまとめ

- 仮想環境作成・有効化（例）
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール
  - pip install -r requirements.txt
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README を実際のリポジトリ構成に合わせて拡張します（依存ファイル一覧、より詳しい設定例、運用手順、Docker-compose 定義など）。どの情報を追加したいか教えてください。