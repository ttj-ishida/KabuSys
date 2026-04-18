# KabuSys — README

日本株自動売買システムの一部（ライブラリ & 起動スクリプト群）。  
本リポジトリには設定管理、監視エンジン、Execution エンジン起動スクリプト、ポートフォリオ構築ロジック、リサーチ・AI ユーティリティなどが含まれます。

注意: この README は src/kabusys 以下のコードベースに基づく概要・セットアップ・実行手順をまとめたものです。

## 目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 環境変数 (.env) とサンプル
- 使い方（主要コマンド）
- 停止 / Kill Switch / フラグファイルについて
- ディレクトリ構成（主要ファイルの説明）
- 開発メモ / 補足

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコード群で、以下の主要機能を提供します。

- 発注実行エンジン（ExecutionEngine）の起動スクリプト（本番/ペーパートレード切替）
- システム監視（SystemMonitor / MonitoringEngine）とアラート / Kill Switch
- ポートフォリオ構築ロジック（候補選定・重み計算・ポジションサイズ）
- ファクター計算・リサーチユーティリティ（DuckDB を利用）
- ニュースに基づく NLP スコアリング（OpenAI API を利用）
- 監視ログ永続化（SQLite）と検証ツール（設定検証、レポート生成）

設計方針の一部:
- DuckDB/SQLite によるローカルデータ参照（外部 API 呼び出しは限定）
- 環境変数ベースの設定管理（.env 自動ロード / 対話式ウィザードあり）
- 起動スクリプトはプロセス優先度を上げる等の運用配慮を実装

---

## 主な機能一覧
- 設定管理:
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む（無効化オプションあり）
  - 対話式ウィザードで `.env` を生成・更新（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）

- 実行系:
  - ExecutionEngine 起動（`kabusys.run_execution`）:
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離（`data/paper_trading.db`）
    - プロセス優先度を High に設定して起動
  - Monitoring 起動（`kabusys.run_monitoring`）:
    - 定期ポーリングで SystemMonitor を実行。ポーリング間隔は環境変数で上書き可能

- 監視:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせた MonitoringEngine

- ポートフォリオ:
  - 候補選定（スコア順・上位 N 抽出）
  - 等金額 / スコア加重重み計算
  - リスク制御（セクター上限適用）
  - ポジションサイズ算出（単元株丸め、利用可能資金でスケール）

- リサーチ:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）等の統計ユーティリティ

- AI:
  - ニュースNLP（OpenAI を使った銘柄毎センチメント算出）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 統合）

- ツール:
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## 前提条件 / 依存パッケージ
推奨 Python バージョン: 3.10+

主な依存（抜粋）:
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（config 検証で YAML のパースを行う場合、任意）

インストール例:
```bash
python -m pip install duckdb psutil openai pyyaml
```
（プロジェクトに requirements.txt があればそれを使ってください）

SQLite は標準ライブラリに含まれます。

---

## セットアップ手順

1. リポジトリをクローンしてソースルートに移動
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式で作る: `python -m kabusys.config_setup`
   - 手動で作る: プロジェクトルートに `.env` を配置（下記サンプル参照）
5. 設定検証（任意）
   - `python -m kabusys.validate_config`
   - `--strict` を付けると警告も失敗扱い（exit 1）になります
6. 必要なディレクトリを作成（デフォルトで `data/`, `logs/` を使用）
   - 多くは起動時に自動的に作成されますが、権限等に注意してください

---

## 環境変数 (.env) — サンプル

最低限必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（一部）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 実行時）
- LOG_LEVEL — ログレベル（例: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
MONITOR_POLL_INTERVAL=60
```

注: `.env` は絶対にコミットしないでください（秘密情報を含むため）。

---

## 使い方（主要コマンド）

プロジェクトルートで実行（Python パスが src を含む、またはパッケージをインストールしていること）。

- 設定ウィザード（対話式 .env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デフォルト env の動作に応じて本番/ペーパー切替）
  ```
  python -m kabusys.run_execution
  ```
  実行時の挙動:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します。
  - 起動時に `data/stop_requested.flag` が既にある場合は起動を中止します。
  - 終了は Stop フラグの作成、または Ctrl+C（KeyboardInterrupt）で行えます。

- Monitoring を起動（常駐ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数:
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関係なく本番用の sqlite_path（`SQLITE_PATH`）を使用します
  - 起動直後にプロセス優先度を "high" に設定します

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite ファイルパスを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）

- AI / リサーチ関数はライブラリ関数として提供（スクリプト化されていないものも多い）
  - 例: ニュース NLP スコア付けは関数 `kabusys.ai.news_nlp.score_news(conn, target_date, api_key)` を呼び出して利用
  - レジーム判定は `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)` を使用

---

## 停止 / Kill Switch / フラグファイル

- Stop フラグ（プロセス管理用）
  - 実行スクリプト（run_monitoring / run_execution）は `data/stop_requested.flag` を監視します。
  - このファイルが存在すると起動を停止する、または動作中に検知すればエンジンを停止します。

- Kill Switch（自動停止トリガー）
  - `KillSwitch` は監視結果により `data/kill.flag` を書き込み、ExecutionEngine に停止指示を与えます。
  - `KILL_FLAG_CLEAR_ON_START`（.env）が `1` の場合、起動時に自動で kill.flag をクリアする挙動があります（本番では推奨しません）。

- ログ:
  - ログは `logs/<app_name>.log` に日次ローテーションで保存（デフォルト 30 日保持）。
  - `kabusys.utils.logging_setup.setup_logging()` で標準出力とファイル出力を統一的に設定します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定管理。自動で .env を読み込むロジックを含む。Settings クラス提供。
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（本番/ペーパー切替・プロセス優先度設定）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 層（テーブル作成・永続化 API）
    - system_monitor.py — システム状態・データ鮮度チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py — （取引監視ロジック; リポジトリ参照）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（run / run_once）
    - kill_switch.py — Kill Switch 実装（flag ファイル書込み）
    - alert_manager.py — アラート送信管理（LINE 等） ※実装箇所あり
  - execution/
    - execution_engine.py — ExecutionEngine の本体（注文発行ループ等）
    - broker_factory.py — ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注管理・リポジトリ・リスク管理
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores テーブルに書き込む
    - regime_detector.py — マクロ + ETF MA を用いた市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（上記は抜粋です。リポジトリ全体はさらに詳細なモジュール群を含みます。）

---

## 開発メモ / 補足
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存 DB に対してカラム追加等の簡易マイグレーションを実行します。
- データ鮮度/ルックアヘッド対策: リサーチ・AI モジュールは日付参照でルックアヘッドバイアスを避ける実装になっています（date.today() などを直接参照しない等）。
- OpenAI 呼び出し: `openai` SDK を利用。API のリトライや JSON モードレスポンスのハンドリング等、実運用を意識した堅牢性が組み込まれています。
- ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続します。

---

もし README に追加してほしい点（たとえばデプロイ手順、systemd ユニットサンプル、監視・アラート連携手順、より詳しい設定項目の説明など）があれば教えてください。必要に応じてサンプル systemd サービスファイルや .env.example を作成します。