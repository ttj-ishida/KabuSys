# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム「KabuSys」のソースコードです。  
本 README はコードベース（src/kabusys 以下）に基づき、プロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な役割は次の通りです。

- データ処理・リサーチ（DuckDB を利用したファクター計算）
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）
- ExecutionEngine（発注管理・ブローカー抽象化、paper/live 切替）
- 監視（System / Trade / Risk のポーリング監視、Kill Switch）
- AI 支援（ニュースの NLP によるセンチメント、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポート）

設計上の特徴：
- DuckDB（分析用）と SQLite（監視・履歴用）を併用
- 環境ごとに paper_trading を分離（専用 SQLite）
- OpenAI（gpt-4o-mini）を用いたニュース評価・レジーム判定（任意）
- .env による環境変数管理と対話式セットアップ/検証ツール

---

## 主な機能一覧

- Execution:
  - ExecutionEngine（ブローカラッパ、OrderManager、RiskManager、Reconciler）
  - paper_trading モードで MockBroker を利用・本番 DB と分離
- Monitoring:
  - SystemMonitor, TradeMonitor, RiskMonitor を統合する MonitoringEngine
  - kill.flag による停止（Kill Switch）機能
  - 監視ログを SQLite に永続化
- Portfolio:
  - 候補選定（スコア順）、等金額/スコア重み配分
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、資金配分・スケーリング）
- Research:
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC 計算、特徴量サマリ
- AI:
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector: ETF とマクロ記事を用いた市場レジーム判定と保存
- ユーティリティ:
  - 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存ライブラリ（requirements.txt を用意することを推奨）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイルの検証に任意）
- その他: 標準ライブラリ（sqlite3 等）

※ 実行環境により追加の依存やシステムパッケージが必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン・チェックアウトし、仮想環境を作成・有効化します。

   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai pyyaml
   ```

2. 必須環境変数を設定するために .env を作成します（対話式ウィザード推奨）。

   ```
   python -m kabusys.config_setup
   ```

   ウィザードは .env を生成します。手動で作成する場合は .env.example を参考にしてください。

   主要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - OPENAI_API_KEY — AI 機能を使う場合に必要
   - LOG_LEVEL — デフォルト: INFO
   - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか (0/1)

3. 設定検証（起動前に推奨）:

   ```
   python -m kabusys.validate_config
   ```

   --strict を付けると警告も失敗扱いになります。

4. 必要なディレクトリを作成（ログ、data 等）:

   ```
   mkdir -p logs data
   ```

5. DB 初期化: 実行スクリプトが起動時に必要テーブルを作成します（init_monitoring_db が呼ばれます）。DuckDB のスキーマや分析用テーブルは別途ロード・準備してください。

---

## 実行方法（使い方）

- ExecutionEngine（注文実行エンジン）起動:

  - 本番/開発/ペーパーは KABUSYS_ENV に依存します。paper_trading の場合は MockBroker が使用され、専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。

  ```
  python -m kabusys.run_execution
  ```

  実行中は data/execution.pid 等が管理されます。停止は data/stop_requested.flag や kill.flag を利用できます（運用手順に従ってください）。

- Monitoring（監視ループ）起動:

  ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。

  ```
  # 例: 30 秒間隔で監視
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  監視は常に本番用の sqlite_path（Settings.sqlite_path）を使って記録します。

- Paper Trading 検証レポート（ツール）:

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  DB の指定は --db または環境変数 PAPER_TRADING_SQLITE_PATH。

- AI 機能の呼び出し（ライブラリ経由）:
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続を受け取りテーブル（raw_news, news_symbols, prices_daily 等）を参照します。API キーは OPENAI_API_KEY で指定するか、引数で渡してください。

- ログ:
  - ルートロガーは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが必要）。
  - コンソール出力は stdout に出ます。

- 停止フラグ / Kill Switch:
  - Monitoring がリスク閾値超過等を検出すると data/kill.flag を書き込み ExecutionEngine 停止のトリガにできます（KillSwitch）。
  - 手動停止や外部制御用に data/stop_requested.flag を作成すると各 run_* スクリプトが検出して終了します。

---

## 主要設定（概要）

- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の fills の挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に既存 kill.flag を自動でクリア（0/1）

.env の例（一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-xxxxxxxx
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・ディレクトリの構成（このリポジトリで提供されているファイルに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — 対話式 .env 生成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite persistence（テーブル作成・CRUD）
    - monitoring_engine.py   — 各 Monitor 結合とポーリングループ
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （trade 監視ロジック）
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （LINE 等への通知管理）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（EngineConfig 等）
    - broker_factory.py      — ブローカークライアント生成（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

（注）一部ファイルは抜粋・要約しています。実行に必要な補助モジュールや strategy / data 関連は別ディレクトリにある想定です。

---

## 運用上の注意

- live 環境では特に注意：KABUSYS_ENV=live に設定すると実際の発注が行われます。環境変数や kill switch の設定を慎重に確認してください（validate_config は live 時に追加の警告を出します）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI 等外部 API を利用する場合、レート制限やコストに注意してください。AI 呼び出しはリトライ・フェイルセーフを実装していますが、運用ポリシーに従ってください。
- Monitoring は常に本番 sqlite_path を参照します（KABUSYS_ENV に依存せず監視用 DB を使う設計です）。
- paper_trading モードは本番 DB と分離されるように設計されていますが、設定ミスにより上書きしないよう注意してください。

---

## 開発・テスト

- モジュールは関数単位で純粋関数（DB 参照なし）として実装されている箇所が多く、ユニットテストを容易に書けます（例: portfolio.calc_position_sizes 等）。
- AI 呼び出し部分は _call_openai_api を切り替えてモック化しやすい設計です（unittest.mock.patch 推奨）。
- validate_config.run で環境の早期チェックが可能です。

---

## 参考コマンドまとめ

- .env 作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔 override）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、デプロイ／systemd ユニット例、運用手順（Kill Switch の使用例やログローテーションポリシー）なども作成します。どの追加情報が要りますか？