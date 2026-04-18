# KabuSys — README

本リポジトリは日本株向けの自動売買／リサーチ基盤（KabuSys）の一部コードです。  
ここでは、プロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意: README はソースコードから説明を要約したものであり、実際の運用・デプロイ時は各設定ファイル（.env / config/*.yaml）や運用手順に従ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチを行うための基盤モジュール群です。主な責務は以下の通りです。

- 市場データ（DuckDB）を用いたファクター計算・特徴量生成（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- Execution エンジン（発注ロジック、リスク管理、Order 管理）
- 監視（system / trade / risk のポーリング、Kill Switch、アラート）
- AI 支援（ニュース NLP による銘柄センチメント、レジーム判定）
- ペーパートレード検証レポート生成ツール

設計方針として、DuckDB／SQLite をデータ永続化に利用し、OpenAI など外部 API 呼び出しは責任を明示した上で実装されています。

---

## 機能一覧

- 環境設定ウィザード（.env の対話的作成）: `kabusys.config_setup`
- 設定検証 CLI（.env や config/*.yaml のチェック）: `kabusys.validate_config`
- Execution エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使い paper_trading.db に記録（本番 DB と分離）
- Monitoring（ポーリング）起動スクリプト: `kabusys.run_monitoring`
  - システム状態・データ鮮度・取引ログ等の監視、Kill Switch の評価
- 監視データ永続化（SQLite）: `kabusys.monitoring.monitoring_db`
- Risk/Trade/System 各種モニタ: `kabusys.monitoring.*`
- ポートフォリオ構築（候補選定・重み・サイズ計算）: `kabusys.portfolio.*`
- リサーチ（ファクター計算・IC / 特徴量解析）: `kabusys.research.*`
- AI モジュール（ニュース NLP / レジーム判定）: `kabusys.ai.*`
- ペーパートレード検証レポート: `kabusys.tools.paper_verification_report`

---

## 要件（主要依存ライブラリ）

最低限必要となるパッケージ（バージョンはプロジェクトの要件に合わせて調整してください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行う場合に推奨）

例（pip インストール）:
pip install duckdb psutil openai PyYAML

※ requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要ライブラリをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成（自動ロード機能あり）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に `.env` をプロジェクトルートに置く。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データ／ログディレクトリの準備（通常は自動作成されます）
   - デフォルト SQLite: data/monitoring.db
   - ペーパートレード DB: data/paper_trading.db
   - DuckDB: data/kabusys.duckdb
   - ログ: logs/（`kabusys.utils.logging_setup` が作成）

---

## 主な環境変数（重要なもの）

（例）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、発注はモックになりデータは分離されます
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う処理で必要（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

自動読み込みの順序: OS 環境 > .env.local > .env（プロジェクトルートは .git または pyproject.toml を基準に探索）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - (--strict を付けると警告も失敗扱い)

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既に存在する場合、実行をキャンセルする
    - 実行中は data/execution.pid を使用
    - 停止は data/stop_requested.flag を作成することで検知して安全に停止する

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 特徴:
    - 環境にかかわらず監視は production（設定される sqlite_path）に対して行います
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
    - data/stop_requested.flag を作るとループを抜けて終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- AI スコア／レジーム判定（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

ログ出力は `kabusys.utils.logging_setup.setup_logging` により統一管理され、stdout と logs/<app>.log（日次ローテート）に出力されます。

---

## 停止・Kill の仕組み

- 停止フラグ（グローバル）
  - data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルの存在を監視し、検知したら安全に停止します。
  - 例: touch data/stop_requested.flag

- Kill Switch（Execution 停止トリガ）
  - data/kill.flag
  - `kabusys.monitoring.kill_switch` が条件（ドローダウン・ポジション上限など）を満たすと reason を書き込みます。
  - Execution 側は kill.flag の有無を確認して停止できます。
  - Kill フラグを手動で削除するには: rm data/kill.flag
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされるので注意（本番では 0 推奨）

---

## 注意点 / 運用上のメモ

- Monitoring は「本番の監視 DB」（Settings.sqlite_path）を参照する設計です。テスト・開発時は設定を確認してください。
- Paper trading は本番 DB と全く分離するため、PAPER_TRADING_SQLITE_PATH を確認してください。
- process priority を high に上げる処理があり、psutil による優先度設定で権限不足の場合は警告が出ます（正常動作）。
- DuckDB に対する executemany の空リストバインド制約など、ライブラリのバージョン差分に注意（ソース内に互換性対策あり）。
- AI 機能を利用する場合、OpenAI の利用規約・コスト・レート制限を考慮してください。実装にはリトライ・バックオフが組み込まれていますが、APIキーの管理は慎重に行ってください。
- .env は絶対に Git にコミットしないこと（config_setup の出力ヘッダにも注意喚起あり）。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイル / ディレクトリ（src/kabusys）を抜粋したものです。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化・永続化 API
    - monitoring_engine.py       — 各 Monitor を束ねる実行ループ
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — （取引監視、コードベースに含まれる想定）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — Kill Switch 書き込みユーティリティ
    - alert_manager.py           — （アラート送信の管理、コードベースに含まれる想定）
  - execution/
    - execution_engine.py        — 実際の ExecutionEngine（エンジン本体）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数計算・丸め
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — モメンタム / ボラ / バリュー等
    - feature_exploration.py     — IC / 統計サマリ等
  - ai/
    - news_nlp.py                — ニュース NLU / OpenAI 呼び出し
    - regime_detector.py         — マクロ + ETF 指標のレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（注）上記は抜粋であり、リポジトリ全体にはさらに補助モジュールや実装ファイルが含まれます。

---

## 例: 典型的な実行フロー

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ投入 / DuckDB 準備（外部スクリプト・ETL 実行）
4. 監視プロセス起動（プロダクション監視）
   - nohup python -m kabusys.run_monitoring &
5. Execution 起動（当日のセッション）
   - nohup python -m kabusys.run_execution &

停止・緊急停止:
- 優雅な停止: touch data/stop_requested.flag
- Kill（自動）: monitoring が条件を満たした場合 data/kill.flag が作成される（Execution はこれを検知して停止）

---

必要であれば、この README をベースにさらに詳しい運用手順（デプロイ手順、systemd / Supervisor 用ユニットファイル例、CI/CD 設定、DB 初期ロード手順など）を追加できます。どの情報を補足したいか教えてください。