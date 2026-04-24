# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等のコンポーネントで構成されています。

※ この README はソースコード（src/kabusys 以下）を参照して作成しています。

## プロジェクト概要
- 実運用を意識した設計
  - 本番 / ペーパートレードの分離（KABUSYS_ENV）
  - SQLite（監視用 / ペーパートレード用）と DuckDB（分析用）を利用
  - ログは stdout と日次ローテーションファイルに出力
  - プロセス優先度設定、Kill Switch、監視アラートなどの運用機構を備える
- 主な用途
  - 戦略のリサーチ・ファクター計算（DuckDB ベース）
  - ポートフォリオ構築（候補選定・重み・株数決定）
  - ExecutionEngine による発注管理（本番/モック）
  - Monitoring によるシステム健全性監視・Kill Switch の発動
  - OpenAI を使ったニュースセンチメント・レジーム判定（オプション）

## 主な機能一覧
- Execution
  - ExecutionEngine（発注・注文管理・リスク管理・再調整）
  - BrokerClientFactory による本番/モックの切り替え（KABUSYS_ENV）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常等の検出（monitoring 内）
  - RiskMonitor: ドローダウン、ポジション上限の監視とアラート記録
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタの束ねと通知呼び出し
- Portfolio
  - 候補選定（score / rank）、重み計算（等重・スコア重み）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ、レジーム乗数の適用
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリ
- AI（オプション）
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores への書き込み）
  - regime_detector: MA / マクロセンチメントを合成した市場レジーム判定
- ツール
  - 環境設定ウィザード (.env 作成): kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

## 必要条件（例）
- Python 3.10+
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/.yaml の検証を行う場合）

（実際の requirements.txt / pyproject.toml があればそちらを参照してください）

## セットアップ手順（ローカル開発用）
1. リポジトリをクローン
2. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （もし用意されている場合）
   - もしくは最低限: pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
4. 初期設定（.env 作成）
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
5. 設定確認（推奨）
   - python -m kabusys.validate_config
   - 警告も厳密にチェックする場合:
     - python -m kabusys.validate_config --strict
6. データディレクトリ作成（自動作成されることも多いですが事前準備）
   - mkdir -p data logs

## 主要な環境変数（代表）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / 動作に影響する主要なもの:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH に記録される
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: paper_trading 時のモック約定動作（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理用

## 使い方（代表的なスクリプト）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、ペーパートレード用 DB に書き込まれる
    - 実行は data/execution.pid（デフォルト）に PID を書き、data/stop_requested.flag を検知して終了
- 監視プロセス起動（ポーリング）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒指定可能（デフォルト 60）
    - 監視は常に本番用 sqlite_path を参照（環境にかかわらず）
    - 停止フラグ (data/stop_requested.flag) によってループを終了
- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

## 運用上のポイント
- KABUSYS_ENV=live では十分に注意:
  - LINE 通知の設定や Kill Switch 設定 (KILL_FLAG_CLEAR_ON_START) を確認
- Kill Switch:
  - 条件（大きなドローダウンやポジション上限超過）により data/kill.flag を書き込み、ExecutionEngine に停止信号を送る
- ロギング:
  - logs/<app_name>.log に日次ローテーションで出力
  - stdout にもログが出るためコンテナ/cron のログ収集に適する
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行う

## 開発・テスト用ヒント
- 自動で .env を読み込む仕組みがある（project root にある .env / .env.local）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 関連の呼び出しは _call_openai_api を経由しているため、テストではこの関数をモックすることで外部 API を切り離せます
- DuckDB 接続を使ったリサーチ関数は副作用がなく、単体テストが行いやすい設計になっています
- logging_setup.setup_logging を各スクリプトで最初に呼び出し、統一されたログ設定で動かすことを推奨

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — 監視 DB 永続化層（SQLite）
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — （注文監視ロジック、ソース参照）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch ロジック
    - monitoring_engine.py    — 各モニタの統合ループ
    - alert_manager.py        — 通知ラッパー（LINE など、実装参照）
  - execution/
    - execution_engine.py     — 実行エンジン本体
    - broker_factory.py       — BrokerClient の生成（本番 / mock 切替）
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
  - data/                     — データファイル（実行時に生成する data/*.db や flag）
  - logs/                     — デフォルトのログ出力先（実行時に生成）

（実際のファイルは src/kabusys 以下を参照してください）

## よくある操作例
- ペーパートレードで実行する（.env で KABUSYS_ENV=paper_trading を設定）
  - python -m kabusys.run_execution
- 監視を起動（60秒間隔）
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更したい場合
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

## 追加情報 / 注意点
- 本プロジェクトは実際に証券会社 API へ発注する可能性があるため、KABUSYS_ENV=live の設定時は十分に注意し、必ず validate_config で設定を確認してください
- .env ファイルは機密情報（API トークン等）を含むため、決して Git にコミットしないでください

---

README に不足している点や、特定モジュールの詳しい使い方（API 仕様やパラメータ説明）を追加したい場合は、対象箇所（例: ExecutionEngine の設定、RiskManager のパラメータ、AI モジュールの使用法）を教えてください。必要に応じてサンプル .env テンプレートや起動スクリプト例も作成します。