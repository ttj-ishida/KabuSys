# KabuSys

日本株自動売買システムの一部（ライブラリ & 起動スクリプト群）。  
このリポジトリはトレード実行・監視・ポートフォリオ構築・リサーチ・AI スコアリング等のユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズムトレード向けの内部コンポーネント群です。主な責務は以下の通りです。

- ExecutionEngine: 注文送信・管理・リスク管理（paper_trading モードで MockBroker 使用）
- Monitoring: システム稼働状況・注文状況・リスク監視、Kill Switch による緊急停止
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research: ファクター計算、将来リターン、IC 計算、統計サマリ
- AI: ニュースの NLP スコアリング、レジーム判定（OpenAI を使用）
- ユーティリティ: 設定読み込み・ウィザード、ログ設定、プロセス優先度設定、DB 初期化等
- Tools: Paper Trading の検証レポート生成スクリプト等

設計の特徴:
- 環境変数ベースの設定管理（.env の自動ロード機能あり。無効化可）
- DuckDB / SQLite をデータストアに利用
- 本番（live）とペーパートレード（paper_trading）を分離した DB を利用可能
- OpenAI（gpt-4o-mini 等）との連携機能（任意）

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により実運用 / ペーパートレード切替）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔設定）
- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: .env と config/*.yaml の基本検証 CLI
- monitoring/*.py: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート連携
- portfolio/*: 候補選定、重み計算、リスク調整、株数決定アルゴリズム
- research/*: ファクター計算（Momentum/Value/Volatility 等）、特徴量探索、IC・統計
- ai/news_nlp.py: raw_news を LLM に送りセンチメントを ai_scores テーブルへ書き込み
- ai/regime_detector.py: マクロ + ETF MA を組み合わせた市場レジーム判定
- tools/paper_verification_report.py: ペーパートレード検証レポート出力
- utils/*: ログ設定、プロセス優先度 / CPU affinity 設定 等

---

## 必須環境変数（最低限）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

これらが未設定だと多くの機能が動作しません。`.env.example` を参考に `.env` を準備してください。

その他（主要なもの）
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 本番で注意（0 推奨）。1 にすると起動時に kill.flag を自動クリア

自動 .env ロードはデフォルトで有効です。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール
   - 例（pip）:
     ```
     pip install duckdb psutil openai
     ```
   - 追加（開発 / 設定検証用）:
     ```
     pip install PyYAML
     ```
3. プロジェクトルートに `.env` を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（下記サンプル参照）
4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリの作成（.env のパス次第）
   ```
   mkdir -p data logs
   ```
   - log ディレクトリは自動作成されますが、パーミッション等で失敗する場合があります。

注意:
- Paper trading（`KABUSYS_ENV=paper_trading`）では MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録され、本番 DB と完全に分離されます。
- monitoring / execution スクリプトは起動時に必要テーブルを `init_monitoring_db()` で冪等に作成します。

.sample .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主なコマンド）

- ExecutionEngine 起動（起動環境により挙動が変わる）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使い `data/paper_trading.db` に記録します。
  - 実行中は PID ファイル（デフォルト: data/execution.pid）を作成します。
  - 停止は `data/stop_requested.flag` を作成するか、プロセスに SIGINT（Ctrl+C）を送ってください。Monitoring の KillSwitch は `data/kill.flag` を書き込み ExecutionEngine 側で検出して停止します。

- Monitoring 起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 停止フラグ: `data/stop_requested.flag` を作成するとループを終了します。

- 設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定

- AI スコアリング / レジーム判定（プログラムから呼ぶ）
  - ニュース NLP スコアリング: `kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)`
  - いずれも `OPENAI_API_KEY` または明示的な `api_key` が必要

ログ:
- デフォルトでコンソール出力と日次ローテートされたファイル出力（logs/<app_name>.log）を行います。`LOG_DIR` で出力先を変更可能。

停止 / Kill Switch:
- KillSwitch が条件を満たすと `data/kill.flag` を書き込みます（ExecutionEngine に停止を促す仕組み）。`KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動で `kill.flag` をクリアします（本番では危険なので `0` を推奨）。

---

## ディレクトリ構成

（ルートはプロジェクトの `src` 下を想定）

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - config.py                  — Settings（環境変数読み込み・検証）
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

その他:
- data/                    — デフォルトの DB ファイルやフラグファイル（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag）
- logs/                    — ログファイルが出力されるディレクトリ（デフォルト）

---

## 追加の注意点 / 運用上のヒント

- 本番環境 (KABUSYS_ENV=live) では、`KILL_FLAG_CLEAR_ON_START=0` を推奨します。誤って Kill Switch をクリアすると安全停止が行えない可能性があります。
- ペーパートレード用 DB と本番 DB は分離されています。`KABUSYS_ENV=paper_trading` を使用することで MockBroker と paper DB が使われます。
- ログディレクトリの作成に失敗した場合、コンソール出力のみで継続します。権限やディスク上の容量に注意してください。
- OpenAI を利用する機能は API 呼び出しの失敗に対してリトライやフォールバック（0.0 やスキップ）を行う設計ですが、API キー漏洩や利用料金には注意してください。
- DB スキーマの簡易マイグレーション（monitoring_db.init_monitoring_db）は存在しますが、重要な変更がある場合はバックアップを取りつつ適用してください。

---

必要であれば、README にさらに具体的な起動例、環境変数の完全一覧、API インターフェースの使い方、ExecutionEngine / Broker の実装詳細（MockBroker の振る舞い等）を追加できます。どの追加情報が欲しいか教えてください。