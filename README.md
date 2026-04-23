# KabuSys

日本株自動売買システム（KabuSys）  
このリポジトリは、戦略の研究・ポートフォリオ構築・発注エンジン・監視・AI ニューススコアリング等を含む自動売買プラットフォームのコアライブラリです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤で、以下の主要機能を備えます。

- データ解析・研究（DuckDB を利用したファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ決定）
- 発注実行（ExecutionEngine、paper_trading モードをサポート）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- AI ベースのニュースセンチメント評価（OpenAI API を利用）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- 共通ユーティリティ（ロギング設定・プロセス優先度設定など）

設計上の方針として、本番 DB とペーパートレード DB を分離し、ルックアヘッドバイアスを避ける実装が各所で採用されています。

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルートに基づく）
  - Settings クラスで環境変数を一元管理
  - `python -m kabusys.config_setup` による対話式 .env 作成
  - `python -m kabusys.validate_config` による設定検証

- 発注・実行
  - ExecutionEngine（run_execution.py で起動）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、`data/paper_trading.db` に記録

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor の集合体として MonitoringEngine
  - run_monitoring.py によるポーリング監視（MONITOR_POLL_INTERVAL で間隔調整可能）
  - Kill Switch（データベースのリスクイベントにより `data/kill.flag` を作成しエンジン停止）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - ニュース記事をまとめて OpenAI に送り、銘柄単位のセンチメントスコアを ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート生成（期間指定可能）
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 必要環境 / 依存パッケージ

- Python 3.10 以上（PEP 604 の | 型表記を使用）
- 必須ライブラリ（実行する機能に依存）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 任意
  - PyYAML（config/*.yaml の内容検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, time など

依存関係はプロジェクト側で requirements.txt を用意しているケースが多いです。以下は一例：

pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 主要な環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. データディレクトリ等の準備
   - logs/ ディレクトリは logging_setup が自動生成しますが、権限等で作成失敗する場合は事前に作成して下さい。
   - data/ ディレクトリは sqlite/duckdb ファイルを置きます（.env のパスに合わせる）。

---

## 使い方（主要スクリプト）

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 DB に記録（本番 DB と分離）
    - live: 実ブローカーを使用（注意して設定してください）
  - エンジン PID は data/execution.pid に記録されます
  - 停止要求は data/stop_requested.flag を作成（存在検出で停止）または monitoring 側で kill.flag が書き込まれると停止

- Monitoring の起動（監視ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を使用（環境に依らず本番監視 DB を参照）
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、KillSwitch を評価し必要に応じて data/kill.flag を書き込みます

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH より優先して指定可能

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを ai_scores に書き込み
    - OPENAI_API_KEY 環境変数または明示的な api_key 引数が必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを判定して market_regime テーブルへ書き込み

---

## 停止 / Kill Switch に関する注意

- 手動停止: プロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- Kill Switch: 監視処理が重大なリスク（例: ドローダウン超過、ポジション上限超過）を検出した場合、`data/kill.flag` を作成します。ExecutionEngine はこのファイルの存在を検知して停止します。
- KILL_FLAG_CLEAR_ON_START（.env）:
  - 本番で誤って自動クリアされないようデフォルトは 0。開発で自動クリアしたい場合に 1 を設定できます（ただし本番では推奨されません）。

---

## ロギング

- 共通ロギング設定: kabusys.utils.logging_setup.setup_logging を使用
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル（デフォルト logs/<app_name>.log、30 日保持）
- 環境変数:
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（ファイル出力先ディレクトリ、デフォルト logs/）

---

## ディレクトリ構成（抜粋）

以下は主要なソースツリー（src/kabusys 以下）の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager 等は実装ファイル群)
  - data/                    — 実行時データ（SQLite/DuckDB ファイル、フラグファイル等）
  - config/                  — YAML 設定ファイル群（system_config.yaml など）

---

## 開発・運用の注意点

- KABUSYS_ENV:
  - development: 開発用（発注無し等の安全設定）
  - paper_trading: ペーパートレード（実発注は行わないが注文・履歴等は DB に記録）
  - live: 本番（実際の発注が行われるため慎重に設定すること）
- DB 分離:
  - 監視用の SQLite（monitoring.db）は監視プロセスが使用
  - paper_trading の場合、発注関連は data/paper_trading.db に記録され本番 DB と分離
- ルックアヘッド対策:
  - AI / レジーム判定 / ファクター計算等は日付に厳密で、内部で datetime.today() を参照しない設計を遵守
- テーブルマイグレーション:
  - init_monitoring_db は冪等にテーブルを作成し、必要なカラム追加の簡易マイグレーションを行います

---

## よく使うコマンド一覧

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 発注エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 貢献 / 変更のヒント

- 追加の設定項目は config_setup.py の _ITEMS に追記してください。
- YAML 設定ファイル（config/*.yaml）は validate_config.py で検証されます（PyYAML がインストールされている場合）。
- ロギングやプロセス優先度設定は utils 下のユーティリティを通じて行うことで一貫性を保てます。

---

必要に応じて README を拡張して CI / デプロイ手順、Docker イメージ化、より詳しい実行シーケンス（ExecutionEngine のイベントフローや OrderManager の契約など）を追加できます。追加で記載して欲しい項目があれば教えてください。