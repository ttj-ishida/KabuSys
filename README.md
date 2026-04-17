# KabuSys

KabuSys は日本株向けの自動売買・研究・監視フレームワークです。  
このリポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、調査（Research）、AI ベースのニュース NLP など複数のコンポーネントを含みます。コードは主に純粋関数と小さなクラスで構成され、SQLite / DuckDB をストレージに使用します。

---

## プロジェクト概要

- 目的
  - 日本株の自動売買システムの基盤ライブラリ／実行バイナリ群を提供します。
  - ExecutionEngine による注文処理、Monitoring によるシステム状態監視、Research によるファクター計算、AI モジュールによるニュースセンチメント評価などを扱います。
- 設計方針（抜粋）
  - 本番と Paper Trading（検証）を明確に分離（Paper 用 DB を別ファイルで保持）。
  - 可能な限り外部 API 呼び出しは明示的に扱い、API 不具合時はフェイルセーフ（例: LLM エラー時はゼロにフォールバック）を採用。
  - DuckDB を分析向けに、SQLite を監視 / 取引ログ用に使用。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler による注文作成・同期・自動復旧。
  - Paper Trading モード：MockBrokerClient を利用し、本番 DB と完全に分離して `data/paper_trading.db` に記録。

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、実行プロセスの生存チェック、データ鮮度チェック。
  - TradeMonitor：滞留注文（stale）や約定価格異常の検出。
  - RiskMonitor：ドローダウンやポジション数上限の監視とリスクイベント記録。
  - KillSwitch：条件に応じて `data/kill.flag` を作成し ExecutionEngine に停止信号を送信。
  - AlertManager：LINE Messaging API による通知（クールダウンあり）。
  - Streamlit ダッシュボード（監視向け）。

- Research（リサーチ）
  - Factor 計算（Momentum / Volatility / Value など）。
  - Forward return / IC / 統計サマリーなどのユーティリティ。

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア加重の重み計算、ポジションサイジング（単元丸め・リスク制約）、セクターキャップ・レジーム乗数。

- AI
  - news_nlp：OpenAI（gpt-4o-mini 等）を用いた銘柄別ニュースセンチメント計算→ai_scores へ書き込み。
  - regime_detector：ETF（1321）MA200 とマクロニュースの LLM 評価を合成して市場レジーム（bull/neutral/bear）を判定。

---

## セットアップ手順

1. リポジトリをクローンして依存をインストール
   - Python 3.9+ を推奨
   - 依存ライブラリ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - pip 例:
     ```
     pip install -r requirements.txt
     ```
     （requirements.txt がない場合は上記ライブラリを個別インストールしてください）

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（デフォルトでは OS 環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

3. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI を使用する機能（news_nlp / regime_detector）の場合に必要
   - 省略可能な環境変数一覧は下記「環境変数（主要）」参照

4. data ディレクトリ作成（省略可）
   - デフォルトで DB パスは `data/` 配下を想定します。必要に応じて作成してください。
   ```
   mkdir -p data
   ```

5. 監視 DB の初期化
   - run_monitoring または run_execution が起動時に `init_monitoring_db` を呼び出してくれるため、手動初期化は不要です。

---

## 環境変数（主要・デフォルト）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

Settings モジュールは `.env` / `.env.local` を自動読み込みします（OS 環境変数が保護されます）。不適切な値があると Settings が ValueError を投げます。

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
```

---

## 使い方（主要コマンド）

- 監視ループを起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔をオーバーライド可能。
  - 停止：プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し Paper DB (`PAPER_TRADING_SQLITE_PATH`) に記録します（本番 DB と分離）。
  - 実行中の停止：`data/stop_requested.flag` を作成すると ExecutionEngine を停止します。
  - KillSwitch により `data/kill.flag` が書き込まれると、ExecutionEngine に停止信号として動作します（kill.flag は Settings.kill_flag_path を参照）。

- Paper Trading 検証レポート（Console）
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  - オプション:
    - `--from YYYY-MM-DD` レポート範囲開始
    - `--to YYYY-MM-DD` レポート範囲終了
    - `--db PATH` SQLite DB パス（`PAPER_TRADING_SQLITE_PATH` 環境変数でも可）
  - 指標：稼働率、注文成功率、送信率、P95 レイテンシ などを表示し PASS/FAIL 判定を行います。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視用 SQLite を読み取り専用で参照し、Dashboard / Positions / Orders / System を表示します。

- AI 系（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要。関数を直接呼び出すか、スクリプトを作成して実行します。
  - 例: Python スクリプト内で `kabusys.ai.score_news(conn, target_date, api_key=...)` を呼ぶ。

---

## 停止・制御フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution の「早期終了」トリガーとして参照されます（存在するとループを終了）。
- data/kill.flag
  - KillSwitch が条件を満たした場合に作成されます（ExecutionEngine を外部から確実に停止させたい場合に利用可能）。
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル。SystemMonitor はこのファイルを確認して実行プロセスの生存を判定します。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・モジュール構成（src/kabusys 以下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings
    - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (broker_factory 等、ブローカ関連)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - data/                          — （実行時に使用されるファイル、git 管理外想定）
      - monitoring.db (デフォルトの SQLITE_PATH)
      - kabusys.duckdb (デフォルトの DUCKDB_PATH)
      - paper_trading.db

（上記は抜粋です。実際のファイル一覧はリポジトリルートを参照してください）

---

## 開発者向けメモ / 実装のポイント

- Settings はプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` / `.env.local` を自動読み込みします。テスト等でこれを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- run_monitoring / run_execution は最初にプロセス優先度を High に設定（可能な場合）。この処理は psutil に依存します。
- MonitoringDB（monitoring_db.init_monitoring_db）は冪等でテーブルを作成し、既存 DB のマイグレーション（カラム追加）も行います。
- AI 関連（news_nlp, regime_detector）は外部 API（OpenAI）とやりとりします。API 呼び出しはリトライ・バックオフ・レスポンス検証を行い、失敗時はフェイルセーフで処理継続する設計です。
- Paper Trading は本番 DB と完全分離されるため、検証時に本番データを汚す心配がありません。

---

## よくある質問 / トラブルシューティング

- DB ファイルが見つからない・開けない
  - default path は `data/monitoring.db` / `data/kabusys.duckdb` / `data/paper_trading.db` です。必要に応じて `.env` でパスを変更してください。
  - Streamlit は読み取り専用 URI（sqlite URI + mode=ro）で開くため、監視プロセスが DB をロックしていると読み取り可能な状態でもエラーになる場合があります。Monitoring を停止して再試行してください。

- OpenAI API 呼び出しでスコアが取得できない（空結果）
  - OPENAI_API_KEY が設定されているか確認してください。
  - API レスポンスの JSON 形式が期待と異なる場合はロギングが出ます。ログを確認してコンテンツを調査してください。

- ExecutionEngine が停止しない / PID が stale になる
  - `data/execution.pid` を直接編集・削除しないでください。PID ファイルの整合性が崩れた場合、SystemMonitor が検出してリスクイベントを記録し、古い PID ファイルを削除します。

---

必要な追加ドキュメント（推奨）
- Deployment 手順（systemd / supervisor 等での自動起動設定）
- Broker クライアント実装ドキュメント（kabuステーション接続）
- Strategy / PortfolioConstruction / StrategyModel の設計ドキュメント（参照メモがコード内にあります）

---

作業や導入で不明点があれば、どのコンポーネント（Execution / Monitoring / AI / Research / DB）について知りたいか教えてください。具体的な実行例や .env 設定例を用意します。