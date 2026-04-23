# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
本リポジトリは自動売買エンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、OpenAI を用いたニュース NLP 等のコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主要機能は以下の通りです。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、Forward Return、IC 等）
- Paper Trading 用の分離された DB とモックブローカーサポート
- OpenAI を利用したニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定、レポート生成 等

設計方針として、本番 DB と Paper Trading DB を分離し、外部 API 呼び出し（発注・OpenAI 等）は必要に応じてプラグイン的に扱う構造になっています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB に記録
- 監視ループ（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視 DB（SQLite）への永続化（monitoring_db）
- Kill Switch（data/kill.flag）でエンジン停止シグナル送出
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ニュース NLP（OpenAI）による銘柄毎スコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用ファクター計算（momentum, volatility, value）および特徴量解析（IC 等）
- ポートフォリオ構築（候補選定、等配分／スコア配分、リスク調整、株数決定）

---

## 前提（推奨）環境

- Python 3.10+
- SQLite（標準ライブラリ）
- duckdb Python パッケージ
- psutil
- openai（news_nlp / regime_detector を使用する場合）
- PyYAML（config/*.yaml のパース検証を行う validate_config のために任意）

（requirements.txt がある場合はそれを使用してください。なければ下記のように手動インストール）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - 例（最低限）:
     - pip install duckdb psutil openai

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に直接作成する

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリの権限確認
   - デフォルト DB/ログパスは .env の値または以下:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/<app_name>.log

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: (デフォルト data/kabusys.duckdb)
- SQLITE_PATH: (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH: （Paper Trading 用 DB）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存先ディレクトリ
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- OPENAI_API_KEY: news_nlp / regime_detector が OpenAI を使う場合に必須
- PAPER_FILL_MODE: paper_trading 時の約定モード (instant/partial/never/reject)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

監視関連:
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消す（0/1）

ログ・プロセス:
- PID ファイル: data/execution.pid（ExecutionEngine が利用）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）

（詳細は kabusys.config.Settings を参照してください）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading（MockBroker）で起動し、データは PAPER_TRADING_SQLITE_PATH に保存されます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- OpenAI を使ったニューススコアリング / レジーム判定（プログラム API）
  - 例（Python REPL など）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ設定は各スクリプトが自動で呼ぶ logging_setup.setup_logging により統一されます（logs/<app>.log）

---

## Kill Switch / 停止制御

- 監視コンポーネントはリスク条件（ドローダウン超過、ポジション数上限等）を評価し、必要なら data/kill.flag を書き込んで ExecutionEngine に停止指示を出します。
- ExecutionEngine / run_execution は data/stop_requested.flag / data/execution.pid 等のフラグで起動/停止の連携を行います。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 を推奨します。

---

## 開発者向けノート

- 設定の自動ロード: .env, .env.local はプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- Paper Trading と本番 DB は分離されています（Settings.is_paper を利用）。
- ログは stdout と日次ローテートファイル（logs/<app>.log）へ出力します。
- process_priority.set_process_priority で起動時にプロセス優先度を設定します（Windows/Linux 両対応）。
- DuckDB を用いた分析／ファクター計算モジュールは SQL と Python を組み合わせた実装です（外部 API 呼び出しなしで再現可能）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの例です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理 (Settings)
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（監視テーブル）
    - system_monitor.py           — システム／データ鮮度監視
    - trade_monitor.py            — 注文監視（滞留注文・約定異常など）
    - risk_monitor.py             — ドローダウン/ポジション上限監視
    - monitoring_engine.py        — 複数モニタの統合とポーリング
    - kill_switch.py              — kill.flag の発行 / 管理
    - alert_manager.py            — （アラート送信の抽象）
  - execution/                     — ExecutionEngine と関連コンポーネント（OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）による銘柄スコア
    - regime_detector.py          — 市場レジーム判定（OpenAI と MA の合成）
  - tools/
    - paper_verification_report.py
  - data/                         — 実行時に用いる DB / フラグファイル 等（例: monitoring.db, kabusys.duckdb, kill.flag）

※ 実際のリポジトリ内はさらに細かなモジュールが含まれます。上記は主要コンポーネントの概要です。

---

## トラブルシューティング / よくある注意点

- .env を絶対に Git にコミットしないでください（API キー等を含むため）。
- OpenAI を使う処理は API キーが必要です。テスト時は呼び出し関数をモックすることを推奨します（コード内でモック差替えを想定）。
- DuckDB / SQLite ファイルのパスは .env で調整できます。複数環境にまたがる場合はパス設定に注意してください。
- run_monitoring は停止フラグ（stop_requested.flag）を検出するとループを終了します。停止フラグと kill.flag は用途に応じて使い分けてください。

---

必要であれば README に「デプロイ手順」「CI/CD 連携」「詳細な設定項目一覧（.env.example）」などを追加します。どの情報を優先的に追加したいか教えてください。