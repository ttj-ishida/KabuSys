# KabuSys

日本株向け自動売買システムの参照実装です。戦略の生成・ポジション構築・発注管理（ExecutionEngine）や、システム稼働監視（Monitoring）・リスク監視・アラート・AI を使ったニュース分析などを含みます。

この README はコードベース（src/kabusys 以下）に含まれる主要コンポーネントと起動／設定手順をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を主眼に設計された自動売買フレームワークです。

- 戦略からのシグナルを受けてポートフォリオ建て付け・発注を行う ExecutionEngine
- システム稼働状況・注文状況・リスク（ドローダウン・ポジション数等）を監視する Monitoring
- LLM を用いたニュースセンチメント解析（ai.news_nlp）や市場レジーム判定（ai.regime_detector）
- 研究用途のファクター計算・特徴量探索（research）
- ペーパートレードの検証用ユーティリティ（tools）
- 簡易 DB 永続化層（SQLite + DuckDB 参照）およびログ出力設定ユーティリティ

設計方針としては「本番と研究/検証を分離」「ルックアヘッドバイアス防止」「障害に対するフェイルセーフ」を重視しています。

---

## 主な機能一覧

- Execution
  - Broker クライアントの抽象化（実運用 / paper_trading 切替）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - PID ファイル管理、停止フラグ検知による安全停止
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存監視
  - TradeMonitor: 注文の滞留検知、約定異常検知（trade_logs を参照）
  - RiskMonitor: ドローダウン、ポジション上限監視と kill switch 発動
  - MonitoringEngine: 各 Monitor のポーリングとアラート発行
  - SQLite による監視ログ保存（monitoring_db）
- Portfolio（純粋関数群）
  - 銘柄選定、等金額／スコア加重配分、ポジションサイズ算出、セクター上限調整、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、基本統計
- AI
  - ニュースを LLM（OpenAI）に投げて銘柄別センチメントを算出して ai_scores に保存
  - マクロニュース＋ETF MA を用いた市場レジーム判定
- ツール
  - config_setup: .env の対話式生成・更新ウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB を用いた評価レポート出力

---

## セットアップ手順

### 前提

- Python 3.10+
- SQLite（標準ライブラリ）
- OS によっては psutil のインストールにビルドツールが必要（wheel が使える環境推奨）

### 推奨パッケージ（最低限）

以下をインストールしてください（pip または poetry 等）:

pip:
pip install duckdb psutil openai pyyaml

- duckdb: 研究用テーブル / 集計
- psutil: システム監視・プロセス優先度設定
- openai: ニュース NLP / レジーム判定（OpenAI API を使う場合）
- pyyaml: validate_config が YAML をパースする際に必要（任意だが推奨）

※ requirements.txt はリポジトリに含まれていない場合があるため、上記パッケージを個別にインストールしてください。

### 仮想環境の作成（例）

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml

### .env の作成

対話式ウィザードを使うと簡単です:

python -m kabusys.config_setup
（プロンプトに従って J-Quants トークンや kabu API パスワード等を入力）

対話を中断した場合は .env は保存されません。作成後は設定の検証を行います。

### 設定の検証

python -m kabusys.validate_config
--strict オプションを付けると警告もエラー扱いになります。

### ディレクトリ作成（必要に応じて）

通常はアプリ起動時に data/ や logs/ を自動作成しますが、手動で用意しておくと権限等で起動失敗を防げます:

mkdir -p data logs

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連:
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live"), デフォルト "development"
  - paper_trading: MockBroker を用い、paper DB（PAPER_TRADING_SQLITE_PATH）に記録
  - live: 本番発注
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR")
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要

DB / ファイルパス（デフォルト値）:
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- PID_FILE_PATH — data/execution.pid
- KILL_FLAG_PATH — data/kill.flag

その他:
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか ("1" で有効。live では注意)

---

## 使い方（起動例）

基本的な実行スクリプトはパッケージ内にモジュールとして用意されています。

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading SQLite DB に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動を中止します。
  - エンジンは _EXECUTION_PID（data/execution.pid）に PID を書きます。
  - 停止は kill.flag（KillSwitch）や stop_requested.flag によって行われます（kill.flag は KillSwitch が書き込み、ExecutionEngine 側で検出する）。

- Monitoring 起動（ポーリング）
  python -m kabusys.run_monitoring

  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL で間隔(秒)を上書き可能（デフォルト 60 秒）
  - run_monitoring は監視用の SQLite（settings.sqlite_path）を参照します（環境に関わらず本番 sqlite_path を使用）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能。デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数、無ければ data/paper_trading.db。

### 停止・Kill Switch

- 手動停止: プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring/run_execution 側が検知して安全停止を試みます。
- Kill Switch: KillSwitch（monitoring）により条件を満たした場合 data/kill.flag が書き込まれ、ExecutionEngine がそれを検知して停止します。KILL_FLAG_CLEAR_ON_START 設定により起動時に自動クリアするか制御できます（本番では 0 推奨）。

---

## ログ

- ログは kabusys.utils.logging_setup.setup_logging により統一的に設定され、コンソール（stdout）と日次ローテートされたファイル（logs/<app_name>.log）へ出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または関数引数で制御できます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／モジュール構成（与えられたコードベースに基づく抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照はあるが今回の抜粋では省略)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
    - execution/ (実行エンジン関連: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など)
      - （実装ファイル群はコードベースに依存）
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - research/
      - factor_research.py, feature_exploration.py
    - data/ （実行時に利用する DB / フラグ / pid 等）
      - monitoring.db（デフォルト）
      - paper_trading.db（paper_trading 用）
      - kabusys.duckdb（DuckDB）
      - execution.pid
      - kill.flag
      - stop_requested.flag
    - logs/
      - execution.log
      - monitoring.log
      - ...（日次ローテーション）

（注）一部のファイルやディレクトリは抜粋コードに基づく表記です。実際のリポジトリではファイル数・構成が多少異なる場合があります。

---

## 主要モジュールの役割（要約）

- config.py
  - .env の自動ロード（プロジェクトルート判定）
  - Settings クラス: 環境変数のラップと必須チェック
- config_setup.py
  - 対話式ウィザードで .env を生成する CLI
- validate_config.py
  - 起動前チェック（必須 env、パス、YAML パースなど）
- run_execution.py
  - ExecutionEngine を起動（paper_trading モードで MockBroker 使用）
- run_monitoring.py
  - SystemMonitor を定期実行する簡易スタンドアロン監視ループ
- monitoring/monitoring_db.py
  - SQLite を使った監視テーブル定義と読み書きユーティリティ
- monitoring/system_monitor.py
  - CPU/メモリ/ディスク、データ鮮度、プロセス PID ファイル監視
- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI を使ったニュースセンチメント算出や市況判定（API キー必須）
- portfolio/*
  - 銘柄選定・重み付け・ポジションサイズ算出・セクター制約などの純粋関数群
- research/*
  - DuckDB を用いたファクター計算・将来リターン・IC 解析

---

## 注意事項・運用上の留意点

- 本リポジトリには実際のブローカー接続（kabuステーション）に対する実行配慮が含まれます。live 環境での起動は十分に設定と検証を行ってから行ってください。
- .env は絶対にソース管理（Git 等）にコミットしないでください（config_setup でも警告あり）。
- OpenAI を使う機能は API コストとレート制限に注意が必要です。news_nlp ではバッチ化・バックオフ・リトライ等の対策を実装していますが、運用時は API キー管理とコスト管理を行ってください。
- Monitoring 側は監視データを SQLite に永続化します。disk や permissions による書き込みエラーが発生しないように注意してください。
- KILL/STOP フラグ関連:
  - data/kill.flag は KillSwitch が書き込み、ExecutionEngine に停止シグナルを与えます。
  - data/stop_requested.flag は起動スクリプト（run_*）でループ終了トリガに使われます。
  - KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動クリアします（本番環境では危険なので 0 を推奨）。

---

## トラブルシューティング

- .env 自動ロードされない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。
  - プロジェクトルートが .git または pyproject.toml により検出されないと自動ロードはスキップされます。
- psutil による優先度設定が失敗する場合:
  - 権限不足や OS 非対応で警告が出ますが、プロセスは継続します（フォールバック）。
- DuckDB / SQLite のファイルパスに指定したディレクトリが存在しない場合、validate_config で警告が出ます（起動時に自動作成されるケースあり）。

---

この README はコードベースに含まれる主要な機能と運用手順の要約です。実装の詳細や設計文書（PortfolioConstruction.md 等）がリポジトリにある場合はそちらも参照してください。質問や追加のドキュメント生成が必要であればお知らせください。