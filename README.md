# KabuSys

日本株向けの自動売買システム（ライブラリ形式）。  
このリポジトリは、戦略フェーズの研究・ファクター計算、ポートフォリオ構築、注文発行（ExecutionEngine）、監視（Monitoring）や補助ツール（レポート生成、設定ウィザード）を含むモジュール群で構成されています。

## 概要
- 戦略・リサーチ：DuckDB の時系列データからファクター（モメンタム・ボラティリティ・バリュー等）を計算する機能を提供します。
- ポートフォリオ構築：候補銘柄選定、重み付け、ポジションサイズ計算、セクター制約やレジーム乗数の適用を行います（純粋関数群）。
- 実行（Execution）：ブローカークライアントを通じて発注を行う ExecutionEngine を起動できます。`KABUSYS_ENV=paper_trading` ではモックのブローカーを使用し、本番 DB から分離して `data/paper_trading.db` に記録します。
- 監視（Monitoring）：システム状態、注文ログ、リスク指標（ドローダウン・ポジション上限など）を定期ポーリングでチェックし、Kill Switch（フラグファイル）や通知機能を通じて運用を支援します。
- AI ユーティリティ：OpenAI を使ったニュースのセンチメントスコアリングや市場レジーム判定の補助機能を備えます。
- ツール群：.env 作成ウィザード、設定検証 CLI、ペーパートレード検証レポートなど。

## 主な機能一覧
- 環境設定の自動ロード（.env / .env.local）
- 設定ウィザード: `python -m kabusys.config_setup`
- 設定検証: `python -m kabusys.validate_config [--strict]`
- ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用、データは `data/paper_trading.db` に保存
- Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- DuckDB を使ったファクター計算（research モジュール）
- ニュース NLP（OpenAI）を用いた銘柄単位のセンチメントスコアリング（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- ロギング統一化ユーティリティ（utils.logging_setup）
- プロセス優先度と CPU affinity 設定（utils.process_priority）
- 監視用 SQLite (monitoring_db) の初期化と永続化層

## 前提 / 依存パッケージ
最低限必要なパッケージ（例）:
- python 3.9+
- duckdb
- psutil
- openai
- (任意) PyYAML — `validate_config` の config/*.yaml 検証に使用

インストール例（pip）:
```
pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 仮想環境の作成と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # requirements.txt があれば
   # または必要なモジュールを個別に pip install
   ```

3. .env ファイルの作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードで入力するとプロジェクトルートの `.env` に保存されます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 実行環境の選択: `KABUSYS_ENV` (development / paper_trading / live)

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

5. DB 初期化
   - 起動スクリプト（monitoring / execution）が内部で必要なテーブルを作成します（冪等）。
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

## 環境変数（主なもの）
- KABUSYS_ENV: execution 環境 (development / paper_trading / live). デフォルトは development。
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイルを保存するディレクトリ（デフォルト logs/）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" または "0"）

例: .env の一部（ウィザードで生成されます）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

## 使い方 — 主要 CLI / スクリプト

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（バックグラウンドや systemd 等で実行）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で指定可能（デフォルト: 60）。
  - 停止: プロジェクトの `data/stop_requested.flag` を作成するとループが検知して終了します。
  - 監視は本番 sqlite_path を参照します（KABUSYS_ENV にかかわらず）。

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使い `data/paper_trading.db` に発注ログを記録します（本番 DB と完全分離）。
  - 停止: `data/stop_requested.flag` を作成するとエンジン停止指示を送れます。
  - 実行時に PID ファイル（デフォルト data/execution.pid）を作成します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db PATH` で DB を指定、環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）などを出力し PASS/FAIL を判定します。

- AI / リサーチ機能（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, target_date) など
  - これらは DuckDB 接続（duckdb.connect(...) の返り値）を受け取って動作します。OpenAI を利用する場合は `OPENAI_API_KEY` を設定してください。

## ログとファイル
- ログ設定は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で行います。デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）。
- 停止フラグ / キルフラグ:
  - `data/stop_requested.flag`: run_* スクリプトが監視している停止フラグ（存在すると正常終了トリガー）。
  - `data/kill.flag` : KillSwitch が書き込むフラグ。ExecutionEngine に停止を要求するために使用されます（設定に応じて起動時に自動クリア可能）。
- DB:
  - DuckDB: analysis 用（prices_daily, raw_financials, raw_news 等の読み取り）
  - SQLite: 監視・注文ログ用（monitoring.db、paper_trading.db）

## ディレクトリ構成（抜粋）
以下はパッケージルート `src/kabusys` 以下の主要ファイル・ディレクトリです（実際のリポジトリ全体はこれ以外のファイルも含む場合があります）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py                — .env 作成ウィザード（対話式）
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py          — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（テーブル初期化・CRUD）
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — （注文関連の監視ロジック）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の発行ロジック
    - alert_manager.py             — （通知管理）※実装ファイルがある想定
  - execution/
    - execution_engine.py          — 発注エンジン本体（EngineConfig 等）
    - broker_factory.py            — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 発注株数決定
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリー等
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                          — 実行時生成: DB, pid, flag など（git 管理対象外推奨）
  - logs/                          — ログ出力先（デフォルト）

※ 上記は主なモジュールの一覧です。実際のファイル構成はリポジトリの内容に合わせて確認してください。

## 運用上の注意 / ヒント
- KABUSYS_ENV を `live` に設定すると本番動作になります。設定やシークレット、 LINE 通知先などを慎重に確認してください。
- `.env` は絶対にリポジトリにコミットしないでください（ウィザード内にも注意書きがあります）。
- Monitoring は本番監視データベース（SQLITE_PATH）を使用します。paper_trading と監視 DB は分離されていないため運用時は注意が必要です（Execution は paper_trading の場合に DB を分離）。
- OpenAI 利用時は API の呼び出しエラーに対してリトライやフォールバック（ゼロスコア）を導入しており、完全失敗してもシステム全体が停止しない設計になっています。
- ロギングディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります。

## 開発・拡張
- research / portfolio モジュールは純粋関数として設計されており、ユニットテストが書きやすくなっています。
- AI 呼び出し箇所は OpenAI クライアント呼び出し部分を分離しているため、テストではモック差し替えが容易です（関数に対する patch が想定されています）。
- DuckDB に投入するデータや価格・財務データの整備は、本リポジトリ外のデータパイプライン（kabusys.data.pipeline 想定）で行う想定です。

---

何か特定のセクション（例: 実行例、.env のサンプル、systemd ユニットファイル例、より詳しい開発者向けガイド）を追記したい場合は教えてください。README をその内容に合わせて拡張します。