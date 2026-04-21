# KabuSys — README

KabuSys は日本株の自動売買／リサーチ基盤です。  
このリポジトリは、発注エンジン、監視（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ（ファクター計算・特徴量分析）、および AI（ニュース NLP / レジーム判定）を含むモジュール群で構成されています。

以下はこのコードベースの概要、機能、セットアップ手順、基本的な使い方、およびディレクトリ構成です。

---

## プロジェクト概要
- 自動売買システムのコアコンポーネント群（ExecutionEngine、OrderManager、RiskManager 等）を持つ。
- 監視コンポーネント（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch）により運用上の安全性を確保。
- DuckDB / SQLite を使ったデータ保管・分析基盤。
- ニュースを LLM（OpenAI）で解析して銘柄ごとのスコアを生成する AI モジュール（news_nlp）。
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・セクター制限等）。
- Paper Trading（模擬発注）を本番 DB と分離して実行可能。
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成など）。

---

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading / live / development を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: .env と config/*.yaml の検証 CLI（--strict オプションあり）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク監視、データ鮮度・プロセス生存チェック
  - RiskMonitor: ドローダウン、ポジション数の監視とリスクログ記録
  - KillSwitch: ディスク上の flag ファイル（data/kill.flag）による ExecutionEngine 停止
  - MonitoringEngine: 各モニタをまとめてポーリング、アラート通知連携
- ポートフォリオ構築
  - 候補選定、等重／スコア加重、リスクベース配分、セクター制限、単元株丸め等
- リサーチ
  - ファクター計算（モメンタム/ボラティリティ/バリュー等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores テーブルへ書込）
  - regime_detector: マクロニュース＋ETF MA を組み合わせた市場レジーム判定
- ツール
  - paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## 必須 / 推奨環境
- Python 3.9+（型アノテーションと標準ライブラリ機能を使用）
- 必要（機能に依存）パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で使用）
- 実行環境変数（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをチェックアウトし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール（必要なものだけインストールしてください）
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は用途に応じてパッケージを追加でインストールしてください）

3. 初期 .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成

   主要な環境変数（代表例）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須）
   - KABU_API_PASSWORD: （必須）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR（デフォルト: INFO）
   - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたければ --strict を付与

5. 初期データディレクトリの準備（logs / data 等は自動作成されますが、必要に応じて確認）
   - mkdir -p data logs

---

## 使い方（主なコマンド例）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中は data/execution.pid に PID を書きます（pid ファイルパスは設定で上書き可）。

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを永続化します。
  - 停止: data/stop_requested.flag を作成するとループが検出して終了します。

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションや環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- AI / リサーチ機能の利用
  - AI モジュール（news_nlp.score_news、regime_detector.score_regime）は Python API として利用できます。
  - 例（スクリプト内から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026, 4, 1), api_key="…")
  - OpenAI API Key は OPENAI_API_KEY 環境変数で指定するか、関数引数で渡します。

---

## 運用上のファイル / フラグ
- data/kill.flag
  - KillSwitch が判定したときに書き込まれる停止フラグ。ExecutionEngine に停止シグナルを送る用途。
- data/stop_requested.flag
  - run_monitoring / run_execution のループを安全に終了させるために監視されるフラグファイル。運用上の手動停止に使用。
- data/execution.pid（デフォルト）
  - 実行中の ExecutionEngine の PID を保存（設定でパス変更可能）。
- ログ
  - logs/<app_name>.log に日次ローテートで出力。ログ設定は kabusys.utils.logging_setup を通じて統一的に設定されます。

---

## 主要な環境変数（まとめ）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 設定例（デフォルト値）
  - KABUSYS_ENV = development
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
  - LOG_LEVEL = INFO
  - KILL_FLAG_CLEAR_ON_START = 0
  - MONITOR_POLL_INTERVAL = 60 (監視ポーリング間隔 秒)
  - PAPER_FILL_MODE = instant | partial | never | reject（Paper Trading の約定挙動）
  - OPENAI_API_KEY = （AI 機能利用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID = （任意、アラート通知用）

---

## 注意点 / 運用上のヒント
- 本番（KABUSYS_ENV=live）では必ず設定を精査してください。validate_config は本番用の追加警告を出します。
- Paper Trading は本番データベースと完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Kill Switch（data/kill.flag）は本番で重要な安全機構です。KILL_FLAG_CLEAR_ON_START=1 は本番では危険（自動で Kill Flag をクリアしてしまうため）。
- ログディレクトリ作成に失敗するとコンソールのみの出力になります。ログディレクトリのパーミッションを確認してください。
- process_priority.set_process_priority を用いて起動時に優先度を "high" に設定します（権限がない場合は警告が出ます）。
- OpenAI 呼び出しはリトライやフェイルセーフ（失敗時に 0 やスキップ）を実装しているため、API の一部失敗でプロセスが停止することはありませんが、API キーの設定は必要です。

---

## ディレクトリ構成（抜粋）
（プロジェクトルートは .git または pyproject.toml を基準に自動検出）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定読み込み
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — 優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py       — 監視用 SQLite 永続層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - risk_manager.py
      - reconciler.py
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
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (上記 YAML は存在しない場合、validate_config が警告を出します)
- data/
  - （SQLite / flag / pid 等のデータファイルを配置）
- logs/
  - （ログファイルを出力）

---

## 開発・テストのヒント
- モジュールは多くが純粋関数（副作用のない計算）または DB 接続を受け取る形で設計されているため、ユニットテストが書きやすい構造です（DuckDB コネクションや sqlite.Connection をモック／一時 DB に差し替えてテスト可能）。
- OpenAI 呼び出し部分は _call_openai_api を patch してモックできます（news_nlp、regime_detector 内で明示的に切り離し済み）。
- 設定の自動読み込みはプロジェクトルート探索で行われます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定して自動ロードを無効化できます。

---

必要があれば、README に以下の追加情報を追記できます:
- 具体的な systemd / supervisor 用のサービス定義例
- Dockerfile / docker-compose の例
- より詳細な開発ワークフロー（ユニットテスト、CI 設定）
- 各サブモジュール（ExecutionEngine、OrderManager 等）の API リファレンス

ご要望があれば上記のいずれかを追加します。