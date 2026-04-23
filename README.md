# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む自動売買基盤の一部実装です。OpenAI（ニュース NLP）を用いたアシストや、DuckDB / SQLite を利用したデータ処理・ログ永続化機能を備えています。

---

## プロジェクト概要

- 目的: 日本株向けの自動売買パイプラインを構築するためのモジュール群（戦略研究、ポートフォリオ構築、発注実行、監視、検証ツールなど）。
- アーキテクチャ:
  - research: ファクター計算・特徴量探索
  - portfolio: 候補選定・ウェイト計算・ポジションサイズ調整・リスク調整
  - execution: 発注エンジン（実取引 / ペーパートレード判別）
  - monitoring: システム稼働・注文・リスク監視、Kill Switch（停止フラグ）
  - ai: OpenAI を使ったニュースセンチメント / レジーム判定
  - utils: ロギング・プロセス優先度などのユーティリティ
  - tools: ペーパートレード検証レポート等のスクリプト

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
  - `kabusys.config_setup` — 対話式ウィザードで .env を作成
- 設定検証 CLI
  - `kabusys.validate_config` — .env および config/*.yaml の簡易検証（--strict オプションあり）
- 発注エンジン起動スクリプト
  - `kabusys.run_execution` — ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB を使う
- 監視ループ起動スクリプト
  - `kabusys.run_monitoring` — SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL で間隔を変更可能
- 監視永続層（SQLite）
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard の管理・マイグレーション
- Kill Switch（停止フラグ）管理
  - monitoring.kill_switch: ドローダウンやポジション上限で `data/kill.flag` を書き込む
- リスク監視 / アラートのトリガー
  - risk_monitor, monitoring_engine 等
- ポートフォリオ構築の純粋関数群
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ調整、セクターキャップ、レジーム乗数
- 研究用ユーティリティ
  - DuckDB 経由のファクター計算（モメンタム・ボラティリティ・バリュー等）、IC 計算、前方リターン計算
- AI ベースの処理
  - news_nlp: ニュースを OpenAI に投げて銘柄ごとにセンチメントを算出して ai_scores に保存
  - regime_detector: ETF（1321）MA 乖離 + マクロニュースで市場レジーム判定
- ペーパートレード検証レポート
  - tools.paper_verification_report: ペーパートレード DB から成功率・稼働率・レイテンシ等の指標を出力

---

## 必要環境 / 依存パッケージ

- Python 3.10+
  - （コード中に | 型注釈や match を使わないため Python 3.10 以上があれば動作）
- 推奨パッケージ（pip インストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証の詳細チェックに必要、任意）
- 標準ライブラリ: sqlite3, logging, pathlib, os, time, datetime 等

インストール例:
```
pip install duckdb psutil openai PyYAML
```
（requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
2. Python と依存パッケージをインストール
3. 環境変数をセット（.env を作成）
   - 対話式で作る場合:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合は設定
4. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```
5. 必要なディレクトリを作成（通常は起動時に自動的に作成されますが手動で準備しても可）
   - data/ （DB・PID・フラグファイル）
   - logs/（ログ出力先）

注意:
- monitoring はコード上では「環境に関わらず本番 sqlite_path を使用する」実装があります（監視ログは本番 DB に書く設計）。
- KABUSYS_ENV=paper_trading の場合、発注は MockBroker に切替わり paper_trading DB（data/paper_trading.db）を使用します。本番 DB とは完全分離されます。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env を作る）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません（停止フラグ）。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）

- Monitoring を起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数でオーバーライド可:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）へ書き込みます（環境に依らず本番パスを利用する実装）。
  - 停止は data/stop_requested.flag ファイルの作成で行います（スクリプトはこのフラグを検知してループを終了します）。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は引数 --db、環境変数 PAPER_TRADING_SQLITE_PATH、デフォルトのいずれかで指定

- AI スコアリング / レジーム判定（プログラム的に利用）
  - news NLP:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - regime detector:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して使用します。OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定。

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い（instant / partial / never / reject）

注意点:
- 本番 (KABUSYS_ENV=live) では LINE 通知の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください（validate_config で注意喚起があります）。

---

## ログ / ファイル / フラグ

- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション）
  - コンソールは stdout に出力
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（手動停止用フラグ; run_execution/run_monitoring が監視）
  - data/kill.flag（Kill Switch が書き込む停止理由）
- DB:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（paper_trading 環境）

---

## テスト / 開発時のヒント

- 自動的に .env を読み込む仕組みがあるため（プロジェクトルートに .env/.env.local がある場合）、テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- validate_config は PyYAML がない場合は YAML の内容検証をスキップします（警告）。
- OpenAI API 呼び出しはリトライ・フェイルセーフ設計がされており、失敗時はスコアを採らず継続するようになっています。テストでは API 呼び出し部分をモックしてください（モジュール内の _call_openai_api を patch する想定）。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイルを抜粋しています）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照実装があれば)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/                — 発注エンジン周り（BrokerFactory 等）

（上記は主要なモジュールを示した抜粋です。実際のファイル構成はリポジトリ内を参照してください。）

---

## 注意事項 / 運用上の警告

- KABUSYS_ENV=live（本番）での起動は細心の注意を払ってください。validate_config は本番向けのチェック（LINE 通知未設定や kill_flag の自動クリア等）を警告します。
- Kill Switch（data/kill.flag）は本番停止の最終手段です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動でクリアされますが、本番では 0 を推奨します。
- Monitoring は監視ログを本番 sqlite_path に書き込みます。監視ログの扱いに注意してください。
- OpenAI API を使う機能は API 使用量と応答の正確性に注意してください。実運用では API キーの管理・利用制限・レスポンス検証を厳密に行ってください。

---

README は上記を基本とします。詳細（関数仕様・DB スキーマ・アルゴリズム設計）は各モジュールの docstring / ソースコメントを参照してください。必要であれば、導入手順の補足や各 CLI の出力例、config/*.yaml の説明、さらに詳細なディレクトリツリーを追加で作成します。どの情報を優先して追加しますか？