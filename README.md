# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、取引エンジン（ExecutionEngine）、監視系コンポーネント（Monitoring）、ポートフォリオ構築／リスク管理ロジック、リサーチ用ユーティリティ、LLM ベースのニュース NLP / レジーム判定モジュールなどを含む小規模な自動売買フレームワークです。

以下の README はローカル開発・運用を想定した簡易ガイドです。

---

## 概要

- ExecutionEngine: ブローカークライアント経由で発注を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム状態、注文ログ、リスク指標をポーリングして記録・アラート／Kill Switch を管理
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制約などの純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI モジュール: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価、マクロセンチメントからのレジーム判定
- CLI ツール:
  - .env 対話生成ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

主要な永続化:
- SQLite: 監視ログ / 発注ログ（`data/monitoring.db`、ペーパー検証用は `data/paper_trading.db`）
- DuckDB: 分析用（`data/kabusys.duckdb`）
- ログ: `logs/<app_name>.log`（日次ローテート）

---

## 機能一覧

- 環境設定ウィザード（.env の対話式作成 / 更新）
- 起動前設定検証（必須環境変数、DB パス、YAML ファイル等）
- ExecutionEngine（本番/ペーパートレード切替、MockBroker サポート）
- 監視ループ（CPU/メモリ/ディスク/プロセス状態・データ鮮度の記録）
- リスク監視（ドローダウン、ポジション上限の検出・ログ化・Kill Switch）
- Kill Switch（条件を満たしたら `data/kill.flag` を書き込み ExecutionEngine を停止）
- Paper Trading 検証レポート（稼働率、約定率、レイテンシ等の集計）
- ニュース NLP（OpenAI でセンチメントを算出し ai_scores に保存）
- レジーム判定（ETF MA と LLM による合成で市場レジーム判定）
- ポートフォリオ構築関数群（候補選定、重み付け、ポジションサイズ計算、セクター制約）

---

## 前提（依存関係）

推奨 Python 環境: Python 3.9+

主な依存パッケージ（一例）
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML 検証を有効にする場合）
- その他（標準ライブラリでカバーしている機能が多い）

インストール例:
- 仮想環境を作成してから必要パッケージを pip で追加してください。
  - 例:
    - python -m venv .venv
    - source .venv/bin/activate
    - pip install duckdb psutil openai pyyaml

（requirements.txt は含まれていないため、プロジェクトに応じて必要パッケージを追加してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 生成後、`python -m kabusys.validate_config` で設定検証
   - 自動ロード:
     - パッケージの `config` モジュールはプロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データディレクトリ（`data/`）とログディレクトリ（`logs/`）は起動時に作成されます。必要に応じて手動で作成して権限を確認してください。

---

## 環境変数（主要項目）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨・重要:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBroker を使用し、専用 SQLite (`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`) に記録
  - live: 本番挙動（実際に発注）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）

その他:
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60、1 以上）
- KILL_FLAG_CLEAR_ON_START: 起動時に `data/kill.flag` を自動クリアするか（0/1、本番では 0 推奨）
- PID/FLAG パスは Settings から変更可能（環境変数で上書き可）

---

## 使い方（主要コマンド）

※ すべてプロジェクトルートで実行してください（パッケージとして読み込む前提）。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` が既にあると起動しません
    - プロセス優先度を "high" に設定（可能な場合）
    - PID ファイルを書き込み（`data/execution.pid`）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用
    - Stop フラグ: `data/stop_requested.flag` を作成するとループを終了
    - ログや監視データは `data/monitoring.db` に格納

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ、PASS/FAIL 判定

- AI モジュール（ライブラリ関数）
  - ニューススコアリング（ai.news_nlp.score_news）
    - 使用例（Python 内から）:
      - import duckdb
      - conn = duckdb.connect("data/kabusys.duckdb")
      - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    - OpenAI API キーが引数で与えられない場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定（ai.regime_detector.score_regime）
    - 同様に DuckDB 接続と API キーを渡して実行

---

## ログ / フラグ / PID

- ログ:
  - デフォルト保存先: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション（30 日保持）

- PID / Stop / Kill フラグ:
  - 実行 PID: data/execution.pid（Execution 起動時に設定）
  - 停止要求（外部から実行を中止するためのフラグ）: data/stop_requested.flag
    - run_execution / run_monitoring はこのファイルを検出すると安全に終了
  - Kill Switch（自動停止トリガ）: data/kill.flag
    - Monitoring の評価により作成されると ExecutionEngine を停止させるためのシグナル

---

## ディレクトリ構成（主なファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数／Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py            — .env 対話式ウィザード（CLI）
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - logging_setup.py         — 統一的なログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 & 永続層
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （注文関連監視。コードベースに実装あり）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — Kill Switch 実装（flag ファイル書き込み）
    - monitoring_engine.py     — モニタ群のオーケストレーション
    - alert_manager.py         — （アラート送信実装）
  - execution/
    - execution_engine.py      — ExecutionEngine 実装（発注フロー等）
    - broker_factory.py        — BrokerClient 作成（Mock / 実ブローカー切替）
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
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py       — 市場レジーム判定（MA200 + LLM）
  - data/                      — 実行時生成されるデータディレクトリ（例: monitoring.db, paper_trading.db, kabusys.duckdb）

注: 上記に含まれる一部モジュール（例: alert_manager, trade_monitor, execution の詳細実装）はこの README の範囲では簡略化しています。実運用前にコードを確認してください。

---

## 実運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を 0 にすることを推奨します（誤って自動クリアされないように）。
- .env は絶対にバージョン管理にコミットしないでください（機密情報が含まれます）。
- OpenAI 等の外部 API を使う機能はネットワーク失敗時にフォールバックするよう設計されていますが、実行前に API キー／レート制限等を確認してください。
- ペーパートレードは本番 DB と分離されるよう設計されていますが、環境変数の設定ミスで混在しないよう注意してください。
- ログ・DB ファイルのディスク使用量やバックアップ方針を事前に決めておくと良いです。
- 監視ループ（MONITOR）や ExecutionEngine は stop flag / kill flag を通じて外部から安全に停止できます。運用手順を文書化しておくことを推奨します。

---

## よく使うコマンドまとめ

- .env の対話作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

問題・追加のドキュメント化が必要な箇所や、CI／デプロイ手順、要求される exact requirements.txt を作成したい場合は教えてください。README の補足（例: 詳細な ExecutionEngine 起動オプションや mock broker の仕様、alert_manager の設定方法）も作成できます。