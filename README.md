# KabuSys

日本株自動売買システムのリポジトリ（README）。  
この README はソースツリー（src/kabusys）に基づき、導入・運用に必要な情報を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連の監視／研究ツール群を提供する Python パッケージです。  
主な目的は以下の通りです：

- 売買戦略に基づくポートフォリオ構築・発注管理
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）の分離
- Paper Trading（模擬発注）モードのサポート（実 DB と分離）
- DuckDB を用いたファクター・リサーチ機能
- OpenAI を利用したニュース NLP / レジーム判定（任意）
- 運用向けの設定ウィザード・検証ツール・レポート生成

バージョンはパッケージの `__version__` 参照（例: 0.1.0）。

---

## 機能一覧

主要コンポーネントと機能：

- Execution（発注実行）
  - ExecutionEngine（発注実行スレッド起動）
  - ブローカークライアントの切替（本番 / Mock：KABUSYS_ENV に依存）
  - リスク管理（RiskManager）、オーダー管理（OrderManager）、照合（Reconciler）
  - Paper Trading 時は専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB とは分離

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文の滞留・約定異常等の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 重大なリスクを検出した際に `data/kill.flag` を書き込み Execution を停止させる
  - MonitoringEngine: 上記モニタを束ねてポーリング（デフォルト 60 秒）

- Database / Persistence
  - DuckDB：分析・リサーチ用（`DUCKDB_PATH`）
  - SQLite：監視ログ・注文履歴用（`SQLITE_PATH` / Paper Trading 用 `PAPER_TRADING_SQLITE_PATH`）
  - 初期化・スキーママイグレーション：`monitoring_db.init_monitoring_db`

- Portfolio & Research
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索・IC 計算

- AI（任意）
  - ニュース NLP（OpenAI）による銘柄別スコアリング（`kabusys.ai.news_nlp`）
  - レジーム判定（ma200 とマクロニュースを合成して 'bull'/'neutral'/'bear' を判定）
  - OpenAI API の利用は任意だが API キーが必要

- ツール
  - 環境設定ウィザード: `python -m kabusys.config_setup`（.env の対話式生成）
  - 設定検証 CLI: `python -m kabusys.validate_config`
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`

---

## 前提条件

- Python 3.10 以上を推奨（型ヒント / 区切り構文の利用のため）
- 必須ライブラリ（例、代表）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の内容検証を有効にする場合）
- SQLite は標準ライブラリで利用可能

requirements.txt がある場合はそちらを利用してください。ない場合の最低限のインストール例：

pip install duckdb psutil openai PyYAML

（プロジェクトで提供される requirements.txt を使うことを推奨します）

---

## セットアップ手順

1. リポジトリをクローンして適当な Python 仮想環境を作成・有効化します。

2. 依存関係をインストール:

   pip install -r requirements.txt

   もしくは（簡易）:

   pip install duckdb psutil openai PyYAML

3. 初期設定（.env）の作成:

   - 対話式ウィザードを使用:

     python -m kabusys.config_setup

   - またはプロジェクトルートに `.env` を手動で配置。必要な環境変数（最小セット）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（任意: DEBUG/INFO/...）

   example (.env の一部):

   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_kabu_pw
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LOG_LEVEL=INFO

4. 設定検証（オプション）:

   python -m kabusys.validate_config
   # 警告もエラー扱いにする:
   python -m kabusys.validate_config --strict

5. ログディレクトリ:
   - デフォルトで `logs/` にアプリ別ログ（例: logs/monitoring.log, logs/execution.log）を日次ローテートで出力します。

---

## 使い方（実行方法）

基本的にモジュールを直接実行します。

- 監視ループ起動（Monitoring）:

  python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番の `SQLITE_PATH` を使用します（監視 DB は本番 DB 想定）。

- 実行エンジン起動（Execution）:

  python -m kabusys.run_execution

  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の SQLite（`PAPER_TRADING_SQLITE_PATH`）に記録します。本番 DB と完全に分離。
  - 起動時、プロセス優先度を "high" に設定し、`data/execution.pid` に PID を書きます。
  - 停止制御: `data/stop_requested.flag` を作成すると安全に終了します（run_execution / run_monitoring がこのフラグを検知して終了）。

- Paper Trading 検証レポート:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- 環境設定ウィザード（対話式 .env 作成）:

  python -m kabusys.config_setup

- 設定検証 CLI:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

AI 関連の実行（ニューススコア・レジーム判定など）はライブラリ関数から呼び出します。OpenAI を使う場合は `OPENAI_API_KEY` を環境変数に設定してください。

---

## 運用ノート（重要）

- Kill Switch / 停止フラグ:
  - `data/kill.flag` : Monitoring の KillSwitch が重大リスクを検出した際に書き込む（Execution を停止させる目的）。
  - `data/stop_requested.flag` : 管理者が作成すると run_monitoring / run_execution が検知してループを終了します。
  - `KILL_FLAG_CLEAR_ON_START` 環境変数が `1` の場合、Execution 起動時に kill.flag を自動クリアする設定があります（本番では 0 推奨）。

- Paper Trading:
  - Paper Trading（`KABUSYS_ENV=paper_trading`）では専用 SQLite を使用して実行ログを分離します。実 DB への影響はありません。

- ロギング:
  - `kabusys.utils.logging_setup.setup_logging` を通じてコンソール（stdout）＋日次ローテートファイル出力を統一しています。
  - デフォルトログディレクトリ: `logs/`。ログ出力失敗時はコンソールのみで継続します。

- データベース初期化 / マイグレーション:
  - `monitoring_db.init_monitoring_db(conn)` は必要なテーブル・インデックスを冪等で作成します。既存スキーマに対する軽微なマイグレーション（カラム追加）も行います。

- プロセス優先度 / CPU affinity:
  - 起動時に `psutil` を使ってプロセス優先度を設定します（Windows / POSIX を吸収）。権限不足などでは警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

プロジェクトルート（src/kabusys）を起点にした主要モジュール群の例：

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — Monitoring の起動スクリプト
  - run_execution.py        — Execution の起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - execution/
    - execution_engine.py
    - broker_factory.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

その他: `config/*.yaml`（設定テンプレート）、`data/`（DB、pid、flag など）、`logs/`（ログ） を使用します。

---

## よく使う環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- OPENAI_API_KEY (AI 機能利用時)
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時 kill.flag を自動クリアする場合 1)

---

## 開発者向けメモ

- 単体関数（portfolio / research / ai の多く）は DuckDB 接続や引数を受け取り副作用を持たない純粋関数として実装されています。ユニットテストが容易です。
- AI 系の外部 API 呼び出しは個別のラッパー関数へ抽象化されているため、テスト時はモック可能です。
- 設定検証・ウィザードを活用して起動前に環境不備を検出してください。

---

## サポート / 追加情報

- config/*.yaml のサンプルや生成スクリプトがある場合はそれを参照してください（validate_config がファイル存在・パースもチェックします）。
- 実運用時は KABUSYS_ENV=live 設定の確認と LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を忘れないでください（本番アラート用）。

---

以上。必要であれば README にインストール手順の詳細（requirements.txt の実体、systemd / Supervisor のサービス定義サンプル、データベース初期化手順）などを追加します。どの情報を追記したいか教えてください。