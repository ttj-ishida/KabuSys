# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ + 実行スクリプト群）。

この README はリポジトリ内の主要モジュールの役割、セットアップ手順、使い方、ディレクトリ構成を簡潔にまとめたものです。

注意: 実運用（本番注文）を行う場合は設定・権限・リスク管理を十分に確認してください。本プロジェクトには発注ロジックが含まれており、誤設定で実際の売買が発生します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下のサブシステムを含むコードベースです。

- ExecutionEngine（発注エンジン） — ブローカークライアント経由で注文を実行。`KABUSYS_ENV=paper_trading` でペーパートレード（MockBroker）を利用して本番 DB と分離。
- Monitoring（監視） — システム稼働状況、データ鮮度、注文ログ、リスク（ドローダウンやポジション上限）をポーリングして記録・通知・Kill Switch を発動。
- Portfolio 建設ロジック — 候補選定、重み付け、ポジションサイズ計算、セクター制限など（純粋関数群）。
- Research / Feature modules — DuckDB を用いたファクター計算・特徴量探索。
- AI モジュール — ニュースの NLP スコアリング、マクロセンチメントを元に市場レジーム判定（OpenAI API を利用）。
- ユーティリティ — ロギング設定、プロセス優先度設定、設定ウィザード・検証ツールなど。
- ツールスクリプト — Paper Trading の検証レポート生成など。

---

## 主な機能一覧

- 設定管理（.env の対話式作成）
- 起動前チェック（設定・ファイル・YAML 構文検証）
- 実行エンジン（本番 / ペーパートレード対応）
- 監視エンジン（システム状態、注文ログ、リスク監視、Kill Switch）
- DuckDB ベースのリサーチ（ファクター計算、将来リターン、IC 計算等）
- OpenAI を使ったニュースセンチメント評価（ai.score_news / regime 判定）
- Paper Trading の検証レポート生成（期間指定可能）
- ロギング（コンソール + 日次ローテートファイル）、プロセス優先度設定

---

## 動作要件（推奨）

- Python 3.10+
- 必須 Python パッケージ（少なくとも次をインストールしてください）:
  - duckdb
  - psutil
  - openai  （AI 機能を使う場合）
- 任意 / 推奨:
  - PyYAML（config/*.yaml の構文チェックに使用されます）
- OS: Linux / macOS / Windows（process priority / cpu affinity は OS により挙動が異なります）

インストール例（仮想環境推奨）:
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt は含まれていないため、必要に応じて上記を調整してください）

---

## 環境変数（代表的なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルトを含む）:
- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading: MockBroker を使い、ペーパートレード DB に記録（設定: PAPER_TRADING_SQLITE_PATH）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring の上書き）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- LOG_DIR: ログファイルを出力するディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

注意:
- .env の自動読み込み機構があり（プロジェクトルートの .env / .env.local）、テスト時などに自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順

1. Python 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（リポジトリルートに配置）。.env.example がある場合はそれを参考にしてください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー／警告に従って修正。`--strict` を付けると警告も失敗扱いになります。

5. データディレクトリ作成（必要に応じて）
   - data/ ディレクトリや logs/ は自動作成されますが、権限などの確認は行ってください。

---

## 使い方（実行例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 環境変数 `MONITOR_POLL_INTERVAL` を設定するとポーリング間隔を上書きできます（秒、デフォルト 60）。
    - 監視ループを停止するにはプロジェクトルートの `data/stop_requested.flag` を作成（監視ループはこのファイルを検出すると終了します）。

- 実行エンジン（Execution）起動
  - python -m kabusys.run_execution
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
    - 実行中に停止させたい場合は `data/stop_requested.flag` を作成するか、Kill Switch により `data/kill.flag` が書かれるとエンジンが停止します。
    - Execution は起動時に PID ファイル（デフォルト data/execution.pid）を書きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で別の SQLite パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も使用可。

- AI / リサーチのライブラリ関数利用例（Python スクリプト内で）
  - ニューススコア付与（ai の duckdb 接続を渡す）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  - リサーチ関数（例: モメンタム計算）
    - from kabusys.research import calc_momentum
    - results = calc_momentum(duckdb_conn, date(2026, 4, 1))

---

## 停止・Kill Flag の取り扱い

- 監視・実行ループ停止：
  - 共通の停止フラグ: data/stop_requested.flag（存在を検出すると run_monitoring / run_execution は終了します）
- Kill Switch:
  - KillSwitch は条件（ドローダウン超過やポジション上限超過など）で `data/kill.flag` を書き込み、Execution を停止させるための外部信号となります。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアします（本番では推奨されません）。

---

## ログ・監視 DB

- ログ:
  - デフォルトは `logs/` ディレクトリに日次ローテートログを出力します（ファイル名はアプリ名例: execution.log, monitoring.log）。
  - 権限やディスク容量に注意してください。
- 監視 DB:
  - 監視用 SQLite: data/monitoring.db（デフォルト）。Monitoring 系テーブル（system_status, trade_logs, positions, risk_logs, dashboard）を保持します。
  - DuckDB: 分析用 DB（data/kabusys.duckdb）。prices_daily, raw_financials, raw_news などのテーブルを想定。

---

## 主要モジュール / ディレクトリ構成（抜粋）

リポジトリの主な Python パッケージは `src/kabusys` に配置されています。主要なファイル・ディレクトリは下記の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム監視
    - trade_monitor.py       — 注文監視（ファイル内に実装あり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック
    - monitoring_engine.py   — 複数 Monitor をまとめる
    - alert_manager.py       — 通知管理（LINE 等、実装に依存）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注フロー）
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

（上記は抜粋です。詳細はソースを参照してください。）

---

## 開発・デバッグのヒント

- .env が自動ロードされるため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑止できます。
- Logging はすべての主要スクリプトで `kabusys.utils.logging_setup.setup_logging` を使って統一しているため、ログ出力先やレベルは環境変数 `LOG_DIR` / `LOG_LEVEL` で調整可能です。
- 実際のブローカー接続（kabuステーション 等）を有効にする前に `validate_config` で必須変数が設定されているか確認してください。
- AI 機能を使う場合は OpenAI の API 使用料とレート制限に注意してください。失敗時は多数の処理がスキップされる設計になっています（フェイルセーフ）。

---

## ライセンス・注意事項

- 本リポジトリは自動売買の学習・開発目的を想定しています。実際の資金を運用する際は十分なテスト・監査を行ってください。
- .env ファイルにはシークレット（トークン・パスワード）が含まれるため、絶対に Git 等にコミットしないでください（config_setup.py でも注意喚起あり）。

---

README は以上です。リポジトリ内の各モジュールについてさらに詳しい利用例や API 仕様が必要であれば、どの箇所を優先してドキュメント化するか教えてください。