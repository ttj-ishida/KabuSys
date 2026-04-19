# KabuSys

日本株向けの自動売買システム（ライブラリ／起動スクリプト群）です。本リポジトリは戦略の研究・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・AI を使ったニュース解析等を含みます。

この README はコードベース（src/kabusys 以下）を参照して作成した概要・使い方ガイドです。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含みます。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由で注文を実行（本番 / ペーパートレード切替対応）
- 監視モジュール（Monitoring）：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックし、Kill Switch を発動
- ポートフォリオ構築（portfolio）：銘柄選定、重み計算、ポジションサイズ決定、セクター制約などの純粋関数群
- 研究用モジュール（research）：ファクター計算、将来リターン、IC 等の統計解析（DuckDB を使用）
- AI モジュール（ai）：ニュースの NLP スコアリング、マクロを用いたレジーム判定（OpenAI API 使用）
- ツール（tools）：ペーパートレード検証レポート生成など
- 設定ユーティリティ：.env ウィザード（config_setup）、設定検証 CLI（validate_config）
- 共通ユーティリティ：ログ設定、プロセス優先度設定等

設計の特徴：
- 環境変数／.env による設定
- DuckDB / SQLite を併用（分析 DB と 監視/履歴 DB を分離）
- 本番とペーパートレードの DB 分離、Mock Broker を用いた安全な検証
- AI 部分は API 失敗時にフェイルセーフ（スコア 0 等）で継続する設計

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV に応じて本番または paper_trading（MockBroker）で動作
  - 発注ログ・ポジション管理・リスク管理を統合
  - PID ファイル（data/execution.pid）を用いたプロセス管理
  - stop flag（data/stop_requested.flag）で外部から安全に停止

- 監視（run_monitoring.py + monitoring/*）
  - CPU / メモリ / ディスク / プロセス生存チェック
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 注文滞留 / 約定異常 / リスク（ドローダウン・ポジション上限）の検出
  - Kill Switch（data/kill.flag）への書き込み
  - アラート発火（LINE などを利用する AlertManager を接続可能）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き

- 設定関連
  - config_setup: 対話式に .env を作成・更新
  - validate_config: .env と config/*.yaml の存在・基本妥当性チェック（--strict あり）
  - 自動 .env ロードはデフォルト有効。無効化は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 研究・データ処理
  - research.calc_momentum / calc_volatility / calc_value 等（DuckDB 接続を受ける）
  - feature_exploration (forward returns, IC, summary)
  - ai.news_nlp, ai.regime_detector: OpenAI を使ったニュースセンチメント / レジーム判定

- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

---

## 前提・依存関係

最低限必要なライブラリ（抜粋）:
- Python 3.9+（コードは型ヒントで新しい構文を利用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config が YAML 内容検証を行う場合に必要）

推奨インストール（例）:
- requirements.txt がある場合は: pip install -r requirements.txt
- 個別:
  - pip install duckdb psutil openai pyyaml

標準ライブラリ（sqlite3, logging, threading, datetime など）を使用します。

---

## セットアップ手順（初期）

1. リポジトリをクローン／展開してプロジェクトルートへ移動。

2. Python 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml

4. data/logs ディレクトリ等の準備（通常は起動時に自動作成されますが、権限チェック）:
   - mkdir -p data logs

5. .env の作成（対話式推奨）:
   - python -m kabusys.config_setup
     - 対話式ウィザードで JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV などを設定します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - strict モードで警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

6. （オプション）OpenAI を使う機能を利用する場合:
   - 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime 呼び出し時に api_key 引数を渡す

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- OPENAI_API_KEY（AI 機能用）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒） — run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START（本番注意: 起動時に kill.flag を自動クリアするか）

注意: .env は秘密情報を含むため絶対にコミットしないでください。

---

## 使い方（起動方法）

基本的にモジュールはパッケージとして実行できます。

- ExecutionEngine 起動（発注エンジン）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に結果を記録します。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
  - 停止は data/stop_requested.flag を作成することで行います（監視側や運用者が書き込む）。

- Monitoring 起動（監視ポーリング）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用しログを残します。
  - run_monitoring は data/stop_requested.flag を見てループ終了します。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit(1) を返します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / 研究関数（プログラムから呼び出して使用）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.score_regime(conn, target_date, api_key=...)

ログ:
- デフォルトは logs/<app_name>.log（日次ローテーション、30日分保持）。setup_logging が設定します。

Kill / Stop フラグ:
- data/stop_requested.flag: run_execution / run_monitoring のメインループを静かに終了させるために使用
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 側で起動時に確認・クリアする設定があるため注意（KILL_FLAG_CLEAR_ON_START）

---

## Settings（設定）について

Settings クラス（kabusys.config.Settings）は環境変数を読み込んで便利なプロパティを提供します。主な挙動:

- 自動 .env 読み込み: プロジェクトルートに .env/.env.local があれば自動で読み込みます（OS 環境変数優先）。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- 設定値の検証（env 値の有限集合チェックなど）を行います（例: KABUSYS_ENV の許容値）。
- SQLite/DuckDB パス、paper_trading 用パス、各種閾値、PID/kill flag のパスなどをプロパティとして取得可能。

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）は慎重に扱ってください。validate_config は live の場合に追加警告を出します（LINE 設定など）。
- OpenAI 等の外部 API はレート制限や一時失敗に備えリトライロジックがありますが、API キーは安全に保管してください。
- ファイル出力（ログ・DB）については権限・ディスク容量に注意してください（monitoring はディスク使用率も監視します）。
- DuckDB / SQLite のパスがデフォルトで data/ 以下になっています。運用時は適切なパス・バックアップ方針を決めてください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイルと役割です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数読み込み・Settings 定義（.env 自動ロード含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数（単元丸め・リスク制約）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py — マクロ+MA200 を使った市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB ラッパー（テーブル作成・CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文／約定の監視（滞留／異常検出）※（コード断片に含まれる想定モジュール）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成と管理
    - monitoring_engine.py — 各 Monitor のまとめとポーリングループ
  - execution/  （発注関連コンポーネント: BrokerFactory 等。コードベースに依存）
  - utils/
    - logging_setup.py — 統一ログ設定（コンソール + 日毎ファイルローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は抜粋です。実際のリポジトリにはさらに多くのモジュール・補助ファイルが含まれます）

---

## よくある運用コマンド（例）

- 初期環境作成:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 起動（監視とエンジンを別プロセスで実行）:
  - # 監視プロセス
    - python -m kabusys.run_monitoring
  - # 発注プロセス
    - python -m kabusys.run_execution

- 一時停止（外部から）:
  - touch data/stop_requested.flag
  - 監視/発注の実行ループはこのファイルを検出して安全に終了します。

- Kill Switch の確認／クリア:
  - 存在確認: ls data/kill.flag
  - 削除: rm data/kill.flag  （本番では慎重に）

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 補足 / トラブルシューティング

- .env 自動読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging が警告）。

- DuckDB / SQLite のファイルが見つからない・読み書き権限がない場合:
  - パス設定（環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認し、書き込み権限を付与してください。

- OpenAI を利用する機能で API エラーが出る場合:
  - OPENAI_API_KEY の有効性、ネットワーク疎通、レート制限状況を確認してください。コードにはリトライロジックがありますが、キーの不足や未設定は ValueError を発生させます。

---

もし README に追加したい箇所（例: 詳細な設定例 .env.template、実運用時の systemd ユニットファイル例、CI 設定例、テストの実行方法など）があれば教えてください。必要に応じてサンプル .env や運用手順（rolling restart / backup 方針）も作成します。