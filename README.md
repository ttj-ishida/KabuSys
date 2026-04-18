# KabuSys

日本株自動売買システム（KabuSys）README

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うシステム群です。  
主な機能は銘柄選定（ポートフォリオ構築）、ポジションサイズ算出、発注エンジン、各種監視（システム状態、注文・リスク監視）、機械学習／LLM を用いたニュースセンチメント評価、研究用のファクター計算／探索ツールなどを含みます。

設計上のポイント：
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）の環境切替対応
- SQLite（監視用）・DuckDB（データ分析用）を利用したローカルDB構成
- OpenAI API を利用したニュース NLP / レジーム検出（APIキー必要）
- ログは stdout と日次ローテーションファイルに出力（logs/）
- フラグファイルによる停止指示（data/kill.flag, data/stop_requested.flag）や PID 管理

---

## 機能一覧

- 環境設定ウィザード（.env の生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の検査）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト（発注エンジン）: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper DB を分離
- Monitoring（System / Trade / Risk）起動スクリプト: `run_monitoring.py`
  - 監視ループのポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- Kill Switch: ドローダウンやポジション上限を検知して `data/kill.flag` を書き込み、発注エンジンを停止
- Paper Trading 検証レポート生成ツール: `kabusys.tools.paper_verification_report`
- ポートフォリオ構築ユーティリティ（候補選定・重み・位置サイズ算出）
- 研究モジュール（ファクター計算、前方リターン、IC 計算、統計サマリ）
- AI モジュール（ニュース NLP による銘柄スコアリング、レジーム判定）
- ログ設定・プロセス優先度設定ユーティリティ

---

## 必要条件（概略）

- Python 3.9+
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- OS: Linux / macOS / Windows（各 OS のプロセス優先度設定は psutil の権限に依存）

※ 実際の requirements.txt がある場合はそれに従ってください。  
（本リポジトリのコードから依存を推測しています）

---

## セットアップ手順

1. リポジトリをクローンし、ソースルートに移動
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば `pip install -r requirements.txt`）
4. 環境変数ファイルの作成（対話式推奨）
   - python -m kabusys.config_setup
   - 対話ウィザードに従って .env を作成します
5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正してください
6. データディレクトリの確認
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env で上書きしてください

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム検出 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）。本番では 0 推奨

参考: `kabusys.config.Settings` クラスにその他のデフォルトや検証ロジックがあります。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録されます
  - 停止方法:
    - data/stop_requested.flag を作成するとエンジンは安全に停止します
    - kill.flag が書き込まれると発注停止の仕組みが作動します

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム経由）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を直接呼び出して使用します（OpenAI API キー必要）

---

## 運用メモ / 注意点

- ロギング
  - ログは stdout に出力されると同時に `logs/<app_name>.log` に日次ローテーションで保存されます（デフォルト 30 日保持）。
  - `kabusys.utils.logging_setup.setup_logging(app_name="execution")` で一貫した設定を行います。

- DB と環境分離
  - ペーパートレード実行時は paper 用 SQLite を使用して本番 DB と分離します（Settings.is_paper を参照）。
  - Monitoring は環境に関係なく本番 sqlite_path を使用する設計（run_monitoring の実装上の注意）。

- Kill Switch / Stop フラグ
  - KillSwitch は `data/kill.flag` を作成して発注エンジンを停止させます（冪等）。
  - 管理用の `KILL_FLAG_CLEAR_ON_START` により起動時に既存の kill.flag を自動クリアすることが可能ですが、本番環境では推奨されません（デフォルト 0）。

- 権限とプロセス優先度
  - `set_process_priority("high")` を使用してプロセス優先度を上げますが、OS と権限に依存して失敗する場合があります（psutil の AccessDenied 等）。失敗時は警告を出して継続します。

- OpenAI / API 利用
  - ニュース NLP やレジーム検出は外部 API（OpenAI）を利用します。API 呼び出し失敗時はフェイルセーフ（多くは 0.0 等で継続）になっていますが、API キーは必須です。
  - API 呼び出しはリトライ・バックオフを実装していますが、利用量に応じたレート制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 & 永続化ユーティリティ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文関連監視（滞留注文・約定異常 等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込み・評価ロジック
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — （アラート送信管理、LINE 等）※実装を参照
  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py      — BrokerClient の生成（Mock / 実ブローカ）
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
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                    — デフォルトの DB / PID / flag を置く想定ディレクトリ（git 管理しない）

---

## 開発 / 貢献メモ

- 自動テストや CI を導入する際は、環境変数の自動ロードを抑止するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます（`kabusys.config` 内で参照）。
- OpenAI の呼び出しは外部に依存するため、ユニットテストでは `_call_openai_api` をモックすることが想定されています（各モジュールにコメントあり）。
- DB スキーマのマイグレーションは `monitoring_db.init_monitoring_db` 内で簡易的に行います。より複雑なマイグレーションが必要な場合は専用ツールを検討してください。

---

必要であれば README にサンプル .env テンプレートや、より詳細なデプロイ手順（systemd / supervisor / Docker 想定）を追加できます。どの部分を拡張しますか？