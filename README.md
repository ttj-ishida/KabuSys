# KabuSys

日本株向け自動売買／研究基盤（リファクタ・モジュール群）  
この README はコードベースの主要コンポーネント、セットアップ手順、実行方法、およびディレクトリ構成をまとめたものです。

---

## プロジェクト概要
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。  
主要機能は次のとおりです。

- 戦略・ファクター計算（DuckDB を用いた prices_daily / raw_financials ベース）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制約）
- ExecutionEngine（ブローカーとの発注ロジック、発注管理・リスク管理・突合せ）
- Monitoring（システム稼働・注文・リスクのポーリング監視、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定：OpenAI を利用）
- 開発ツール（.env 対話式ウィザード、設定検証、Paper Trading レポート生成）

設計方針の一部：
- DuckDB を分析 DB、SQLite を監視・注文ログ用 DB として利用
- 本番/ペーパーは設定で分離（paper_trading は専用 SQLite を使用）
- ランタイム設定は環境変数 / .env で管理
- ログはコンソール + 日次ローテートファイルで出力

---

## 主な機能一覧
- portfolio
  - 候補選定 (select_candidates)
  - 重み付け (等分/スコア加重)
  - ポジションサイズ計算（リスクベース等）
  - セクターキャップ適用、レジーム乗数計算
- research
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- ai
  - news_nlp: ニュース記事から銘柄別センチメントを取得して ai_scores に書き込み（OpenAI）
  - regime_detector: ETF・マクロを合わせた日次レジーム判定（OpenAI）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch による停止フラグ生成（data/kill.flag）
  - MonitoringDB: SQLite スキーマ作成・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading 時は MockBroker）
  - run_monitoring.py: SystemMonitor 単体ポーリングループ（MONITOR_POLL_INTERVAL で調整）
- ツール
  - config_setup.py: .env を対話式で生成・更新
  - validate_config.py: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 必要要件（代表）
このリポジトリでは少なくとも次のパッケージが必要になります（バージョンは例示）:

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の内容検証時）

インストール例:
- 仮想環境作成: python -m venv .venv
- 有効化: source .venv/bin/activate もしくは .venv\Scripts\activate
- インストール: pip install duckdb psutil openai PyYAML

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. data/ および logs/ ディレクトリを作成（多くの処理は自動作成しますが、手動で作ると権限問題回避）
   - mkdir -p data logs
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、内容を確認・必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. DB 初期化は起動スクリプトが行います（MonitoringDB の init は起動時に呼ばれます）。DuckDB / SQLite の初期ファイルはデフォルトで data/ 以下に作成されます。

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient（data/paper_trading.db に記録）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュールを使う場合必須）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒。デフォルト 60）

Kill Switch / 停止フラグ
- kill.flag のデフォルトパス: data/kill.flag（Settings.kill_flag_path）
- 起動時にこのフラグがあると ExecutionEngine は起動しません
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に自動クリア（本番では 0 推奨）

---

## 使い方（実行例）

- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict
- 監視ループ起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - paper_trading の場合、.env で KABUSYS_ENV=paper_trading を設定して起動
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db
- AI スコアリング（プログラムから呼ぶ）
  - ニュース NLP: from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None) — api_key None の場合 OPENAI_API_KEY 環境変数を参照
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

ログ
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力されます（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout に出力されます（logging_setup が設定）

停止 / Kill Switch 操作
- ExecutionEngine を強制停止したい場合は data/kill.flag に理由テキストを書き込んでください（KillSwitch クラスが検知）
- Monitoring が条件を満たすと自動で kill.flag を作成する場合があります（例: ドローダウン超過等）

注意点
- paper_trading モードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）
- OpenAI を使う機能は API キーが必要であり、API 呼び出しは課金対象です
- .env は絶対に Git にコミットしないでください（config_setup でも警告あり）

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル・モジュールの概観です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py        —（trade_monitor 実装あり）
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        —（アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - research/ (上記参照)
  - data/ (実行時生成されるデフォルトディレクトリ)
  - logs/ (ログ出力先)

（この README はコードベースの主要箇所に基づいて要約しています。詳細は各モジュールの docstring を参照してください。）

---

## 開発メモ / 運用メモ（短く）
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと自動 .env ロードを抑制できます。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil に依存）。権限がない場合は警告でスキップされます。
- MonitoringDB の init_monitoring_db は冪等で、既存 DB に対する簡単なカラム追加マイグレーションを含みます。
- AI モジュールはリトライ／バックオフやレスポンス検証を実装しており、失敗時はフェイルセーフ（例: macro_sentiment=0.0）で継続しますが、API 利用状況には注意してください。

---

必要であれば README に以下を追加できます：
- サンプル .env.example（例示）
- よくあるトラブルシューティング項目（権限、DB パス、OpenAI エラー など）
- デプロイ / systemd / cron 用のサンプルユニットファイル

追加要望があれば教えてください。