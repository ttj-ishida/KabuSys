# KabuSys — 日本株自動売買システム README

このリポジトリは日本株自動売買システム KabuSys のコアライブラリ群です。戦略、ポートフォリオ構築、監視、発注エンジン、レポート、AI ベースのニュース解析などの機能を含みます。本 README はプロジェクト概要、機能一覧、セットアップ、使い方（起動/停止/ツール）、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような目的で設計されたモジュール群です。

- 市場データ（DuckDB）を用いたファクター計算・調査（research）
- ポートフォリオ候補選定・重み計算・株数算出（portfolio）
- 発注ロジック・Execution Engine（execution）
  - 本番（live）とペーパートレード（paper_trading）を切り替え可能
- 監視・アラート・Kill Switch（monitoring）
- OpenAI（LLM）を用いたニュースセンチメント解析・レジーム判定（ai）
- 運用補助ツール（tools）
- 環境設定ウィザードや設定検証 CLI（config_setup / validate_config）

設計上、データベース（DuckDB/SQLite）や外部 API（kabuステーション、J-Quants、OpenAI）を明示的に分離し、ペーパートレード時は本番 DB と分離して動作します。

---

## 主な機能一覧

- 環境設定管理（.env 読み込み、自動ロード）
- .env 対話式ウィザード（kabusys.config_setup）
- 設定と config/*.yaml の検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV に応じて MockBroker を使用（paper_trading）または本番ブローカーを使用（live）
  - paper_trading では data/paper_trading.db に記録して本番 DB と分離
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とポーリングループ起動スクリプト（kabusys.run_monitoring）
  - システムリソース、データ鮮度、滞留注文、約定異常、ドローダウンなどを検出
  - Kill Switch による停止フラグ生成（data/kill.flag）
- 監視ログ永続化（SQLite）と DuckDB 連携
- ポートフォリオ構築ユーティリティ（候補選定、等配分/スコア配分、ポジションサイズ算出）
- リサーチ機能（モメンタム・バリュー・ボラティリティ等のファクター計算、IC 計算）
- AI ベースのニュース NLP（OpenAI）を使った銘柄センチメント評価（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 運用レポート：Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（タイプヒントで | を使っているため 3.10 以降を推奨）
- 必要パッケージ: psutil, duckdb, openai, （オプションで PyYAML）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存関係をインストール
   - requirements.txt や pyproject.toml がある場合はそちらを使用してください。
   - 例（最低限）:
     ```
     pip install psutil duckdb openai
     ```
   - config 検証で YAML を読みたい場合:
     ```
     pip install pyyaml
     ```

3. .env を作成
   - 簡易的には .env.example を参考に手動で作るか、対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードは `.env` を生成し、機密値はマスクして表示します。
   - 重要: `.env` は決して Git にコミットしないでください。

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの準備
   ```
   mkdir -p data
   ```
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

---

## 主要な環境変数（主なもの）

（左がキー、右は説明とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用、paper DB に記録
  - live: 本番ブローカーを使用
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch が書き込む flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で上書き可能。デフォルト: 60）

---

## 使い方（起動・停止・ツール）

### 環境ファイル作成（対話式）
```
python -m kabusys.config_setup
```

### 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

### 監視ポーリング（System/Trade/Risk Monitor）
- 監視ループを起動（システムのポーリングとアラート判定を実行）
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を環境変数で上書き:
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- run_monitoring は起動時にプロセス優先度を "high" に設定し、監視ログを SQLite（settings.sqlite_path）に永続化します。
- 停止:
  - run_monitoring のループは Ctrl+C（KeyboardInterrupt）で停止します。
  - またプロジェクトルートの `data/stop_requested.flag` を作成すると、監視ループが検知して終了します（run_monitoring ではこのフラグを監視）。

### Execution Engine（発注エンジン）起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、paper_trading の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番環境 (`live`) の場合は本番ブローカーを使用します。
- 起動前に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。
- エンジンは別スレッドで実行され、同ファイル `data/stop_requested.flag` を検知するとエンジン停止要求を行います。
- 停止（手動）:
  - `data/stop_requested.flag` を作成すると run_execution が検知してエンジンを停止します。
  - Kill Switch（監視が条件を満たした場合）は `data/kill.flag` を生成して ExecutionEngine に停止信号を送る仕組みになっています（ExecutionEngine 側が kill.flag を監視する設計）。

### Paper Trading 検証レポート（ツール）
- Paper Trading の DB から検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を直接指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数、なければ `data/paper_trading.db`。

### AI モジュール（ニュース NLP / レジーム判定）
- ai.news_nlp: ニュースセンチメントを計算して `ai_scores` テーブルへ書き込む関数 `score_news`（プログラム的に呼び出し）
- ai.regime_detector: 市場レジームを計算して `market_regime` テーブルへ書き込む関数 `score_regime`
- どちらも OpenAI API キー（OPENAI_API_KEY）が必要です。コマンドラインラッパーは含まれていませんが、モジュール関数をスクリプトから呼び出して定期実行できます。

---

## 停止フラグと Kill Switch の挙動

- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring/run_execution の起動スクリプトが監視するファイル。作成するとそれらのループを終了させるための手段です（手動停止や外部スクリプトからの停止に利用）。
- kill.flag (Settings.kill_flag_path, デフォルト data/kill.flag)
  - Monitoring の KillSwitch がリスク条件（大きなドローダウンやポジション上限超過など）を検出した際に書き込むファイル。
  - ExecutionEngine 側はこのフラグを見て安全に停止する設計（実装箇所に依存）になっています。
- 起動時の挙動:
  - Settings.KILL_FLAG_CLEAR_ON_START が `1` の場合、ExecutionEngine 起動時などに kill.flag を自動でクリアするオプションがあります（本番での誤設定は危険なのでデフォルトは `0`）。

---

## ログとプロセス優先度

- 起動スクリプト（run_monitoring, run_execution）は起動直後にプロセス優先度を "high" に設定しようとします（kabusys.utils.process_priority）。権限が無い場合は警告を出してスキップします。
- ログレベルは環境変数 `LOG_LEVEL` で制御します（デフォルト: INFO）。

---

## ディレクトリ構成（主要ファイル）

以下はこの README 作成時点での主要なファイル/ディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - (発注エンジン関連モジュール: Engine, OrderManager, BrokerFactory 等)
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/   (実行時に生成される、デフォルト DB / pid / flag 置き場)
      - kabusys.duckdb (デフォルト)
      - monitoring.db (デフォルト)
      - paper_trading.db (ペーパートレード用)
      - execution.pid
      - stop_requested.flag
      - kill.flag

（上の構成は実際の repo の内容に応じて差異がある場合があります。主要モジュールの場所は上記参照。）

---

## 開発時のヒント

- .env 自動ロードはプロジェクトルート（.git や pyproject.toml を基準）を検出して行われます。テスト中に自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使ったファクター計算・リサーチは副作用を持たない純粋関数群として設計されています。リサーチ機能は production データベースに書き込まない限り安全です。
- ai モジュールは OpenAI API 呼び出しを行います。テスト時は内部 API 呼び出しラッパー（_call_openai_api 等）をモックしてテストしてください。

---

## よく使うコマンドまとめ

- 環境ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- 発注エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、README にサンプル .env テンプレート、起動/運用フロー図、各モジュールの API 仕様（関数・クラスの public API）を追加できます。どの情報を優先的に追加したいか教えてください。