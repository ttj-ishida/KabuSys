# KabuSys

日本株向け自動売買フレームワーク（KabuSys）のリポジトリ用 README。  
この README はローカル開発 / ペーパートレード / 本番運用のいずれにも適用できる主要な使い方とセットアップ手順をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な機能は次のとおりです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象化
- 監視（Monitoring）: システム状態、注文ログ、リスクチェック、Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、将来リターン計算、IC 計算）
- AI モジュール（ニュースセンチメント解析、レジーム判定） — OpenAI API 利用
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- 永続化: SQLite（監視・ペーパートレード） + DuckDB（分析）

設計方針として、本番用の DB とペーパートレード用 DB は分離され、外部 API 呼び出し／ランタイム時刻参照によるルックアヘッドの防止等に注意した実装が行われています。

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine の起動スクリプト
  - KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使い、`data/paper_trading.db` を利用（本番 DB と分離）
  - ストップは `data/stop_requested.flag` / `data/kill.flag` のフラグファイルで制御
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）
  - 監視ログは monitoring DB（デフォルト: `data/monitoring.db`）へ永続化
- monitoring:
  - system_monitor: CPU/メモリ/Disk/データ鮮度/プロセス生死チェック
  - trade_monitor: 注文滞留・約定異常などのチェック（コード内に存在）
  - risk_monitor: ドローダウンやポジション上限の監視、ダッシュボード更新
  - kill_switch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine 停止
  - monitoring_db: テーブル作成 / マイグレーション / CRUD
- portfolio:
  - 銘柄選定（score / rank ベース）、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research:
  - ファクター計算（momentum / volatility / value）、将来リターン、IC、統計要約
  - DuckDB を用いたデータ処理
- ai:
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores テーブルへ書き込み）
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成してレジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB を元に検証レポート出力
- utils:
  - logging_setup: コンソール + 日次ローテートファイル出力の統一設定
  - process_priority: OS を吸収したプロセス優先度設定（high/normal/low）

---

## セットアップ手順

前提:
- Python 3.10+（ソースは型注釈に Python 3.10+ 機能を使用）
- 任意環境（Linux / macOS / Windows）で動作するように設計されていますが、一部の機能（プロセス優先度、cpu_affinity）は OS に依存します。

1. リポジトリをクローン / 展開
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要となる主要パッケージ:
     - duckdb, psutil, openai, pyyaml など
     - 例: pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LOG_LEVEL: DEBUG/INFO/...
     - KILL_FLAG_CLEAR_ON_START: 0 or 1（本番では 0 推奨）
   - ウィザードで作成した .env を保存したら、設定検証を実行:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けると警告も FAIL 扱いになります

5. データディレクトリ / ログディレクトリの準備
   - 既定では `data/` と `logs/` を使用します。自動作成されますが、権限等に注意してください。

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で切り替わり、`paper_trading` の場合は本番 DB と分離して `PAPER_TRADING_SQLITE_PATH` を使用します。
  - 停止方法:
    - 実行中は `data/stop_requested.flag` を作成するとスレッドが検知して停止する設計です（run_execution 参照）
    - 外部から強制的に停止させる場合は `data/kill.flag` を書く（KillSwitch が評価すると ExecutionEngine を停止させます）
  - 起動時、`KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に kill.flag を自動クリアします（本番では 0 推奨）

- Monitoring を起動（システム監視）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=<秒数>（デフォルト 60 秒）
  - 監視ループも `data/stop_requested.flag` を見て終了します。

- .env を対話的に作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（指定がない場合は env の PAPER_TRADING_SQLITE_PATH、なければ data/paper_trading.db）

- AI 機能を利用する際:
  - OpenAI API を使用するため、OPENAI_API_KEY を設定してください。
  - news_nlp.score_news(conn, target_date, api_key=None) のような形でプログラムから利用できます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — execution 環境: development | paper_trading | live
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector）
- LOG_LEVEL — ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1: クリア / 0: クリアしない）

---

## 停止 / Kill Switch の挙動

- run_execution / run_monitoring は `data/stop_requested.flag` の存在を監視しています。管理者がこのファイルを作成すると安全にループを抜けます。
- KillSwitch はリスクアラート（ドローダウン超過など）を検知した場合に `data/kill.flag` を書き込み、これにより ExecutionEngine を停止させるトリガーとなります。`KILL_FLAG_CLEAR_ON_START=1` の場合、起動時に自動で削除します（本番では有効にしないことを推奨）。

---

## ディレクトリ構成（抜粋）

以下は主なファイル・パッケージと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージメタ情報（バージョンなど）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 / 永続化ユーティリティ
    - system_monitor.py — システム監視（CPU / メモリ / データ鮮度 / PID）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — 注文監視（滞留等）※実装ファイルあり
    - kill_switch.py — フラグ管理（kill.flag）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — 通知管理（LINE など）※実装ファイルあり
  - execution/
    - execution_engine.py — 注文実行エンジン（EngineConfig を含む）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
    - broker_factory.py — BrokerClient の生成（Mock を含む）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — ma200 と LLM を合成したレジーム判定
  - data/  — デフォルトの DB / フラグ / PID ファイルを置く想定ディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
  - logs/  — ログ出力先（デフォルト）

---

## 注意点 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を設定してください。validate_config は live 時に追加警告を出します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は開発では便利ですが、本番では重大なリスクになります（誤って Kill Switch を無効化する可能性）。
- AI（OpenAI）を使う機能は API 呼び出しを含むためコストが発生します。API キー管理に注意してください。
- DuckDB は分析向けに設計されており、大量の read-only 分析処理を高速にこなせます。prices_daily / raw_financials 等のテーブルを用いた集計関数が含まれます。
- ログは console と日次ローテートファイル（logs/<app_name>.log）に出力されます。不具合解析のため logs 配下を確認してください。

---

## サンプル .env（最低限）

以下は最小構成の例（絶対に Git にコミットしないでください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-xxxxxxx
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

この README はコードベースの主要な使い方と運用上のポイントをまとめたものです。実際の運用や拡張時は該当するモジュール（monitoring/*.py、execution/*.py、ai/*.py、research/*.py）を参照して詳細な振る舞いをご確認ください。質問や追加ドキュメントが必要であればお知らせください。