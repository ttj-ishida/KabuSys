# KabuSys

日本株向け自動売買システムの一部をまとめたサンプル実装です。本 README はこのリポジトリに含まれる主要モジュール／スクリプトの概要、セットアップ方法、使い方、ディレクトリ構成を日本語で説明します。

注意：本プロジェクトは実際の資金を扱う設計を含みます。`KABUSYS_ENV=live`（本番）での実行は慎重に行ってください。`.env` は絶対にリポジトリへコミットしないでください。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステム群で、主に以下の機能を含みます。

- 実行エンジン（ExecutionEngine）: 発注、リスク管理、約定の整合化などを行う（run_execution.py 起動スクリプト）。
- 監視（Monitoring）: システム状態・データ鮮度・注文異常・リスク（ドローダウン等）を定期的にチェックし、ログ保存・アラート・キルスイッチ制御を行う（run_monitoring.py 起動スクリプト）。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群（kabusys.portfolio）。
- リサーチ / ファクター計算: モメンタム・ボラティリティ・バリューなどのファクター計算・IC 等の解析（kabusys.research）。
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定（kabusys.ai）。
- ユーティリティ: プロセス優先度設定、設定ウィザード、設定検証ツール、紙トレード検証レポート等。

データ永続化:
- DuckDB: 価格・財務・生のニュース等の分析用（デフォルト: data/kabusys.duckdb）
- SQLite: 監視ログ / 発注履歴等（デフォルト: data/monitoring.db）
- Paper trading 用 SQLite は本番 DB と分離（data/paper_trading.db）

---

## 機能一覧（主なもの）

- run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を利用して paper_trading DB に記録。
- run_monitoring.py: SystemMonitor をポーリング実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（秒、デフォルト 60）。
- config_setup.py: 対話式ウィザードで .env を生成／更新。
- validate_config.py: 起動前に .env や config/*.yaml の整合性検証（--strict オプションあり）。
- tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）。
- kabusys.ai.news_nlp: raw_news を集約して OpenAI で銘柄別センチメントを算出し ai_scores に格納。
- kabusys.ai.regime_detector: ETF（1321）MA 等とマクロニュースを組み合わせて市場レジーム判定を行い market_regime テーブルへ保存。
- monitoring/*: MonitoringDB（SQLite スキーマ初期化）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager（LINE push）等。
- portfolio/*: 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数。

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法を使用）
- OS によっては psutil の特権が必要な場合があります（プロセス優先度設定や CPU affinity）。

1. リポジトリをクローン / 展開
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML
   - 注意: PyYAML は config の YAML 検証で任意（未インストール時はファイル存在チェックのみ行われます）。

4. `.env` の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - (必要に応じて) OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - 注意: .env は機密情報を含むため Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前に `--strict` を付けて警告も FAIL 扱いにできます。

6. データディレクトリの作成（必要なら）
   - mkdir -p data

7. （AI 機能を使う場合）OpenAI API キーの設定
   - 環境変数 OPENAI_API_KEY を .env に追加するか、score_news / score_regime 呼び出し時に引数で渡す。

---

## 使い方（実行例）

基本的な起動フロー:

1. 監視プロセスを起動
   - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（1 以上の整数）
   - python -m kabusys.run_monitoring
   - run_monitoring は monitoring DB（Settings.sqlite_path）に書き込みします。monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。

2. 実行エンジン（ExecutionEngine）を起動
   - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB（Settings.paper_sqlite_path）を使用し MockBrokerClient を利用します（本番 DB と完全分離）。
   - python -m kabusys.run_execution
   - run_execution は data/execution.pid を作成し、停止は data/stop_requested.flag / data/kill.flag で制御します。

停止 / キルについて:
- KillSwitch は監視の結果（ドローダウン超過等）で data/kill.flag を作成し、ExecutionEngine に停止シグナルを与えます。
- 管理用の停止フラグ: data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
- Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

Paper Trading レポート生成:
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- デフォルト DB: data/paper_trading.db（--db オプションで上書き可）

AI 機能:
- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は OpenAI API を使用します。OPENAI_API_KEY を設定してください。
- モデルやバッチサイズなどはソース内の定数で管理されています。

設定検証:
- python -m kabusys.validate_config
- 問題があれば INFO/WARNING/ERROR が出力されます。

設定ウィザード:
- python -m kabusys.config_setup

注意すべき環境変数（抜粋）:
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API パスワード
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）

---

## 注意点 / 運用上のポイント

- 本番環境（KABUSYS_ENV=live）では慎重に設定を確認してください。validate_config は live での注意喚起も行います。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも明記されています）。
- OpenAI 連携は API コストとレイテンシに注意してください。失敗時はフォールバックが用意されている箇所もありますが、運用ルールを作ってください。
- monitoring は monitoring DB を共有して実行状況を記録します。Paper Trading の履歴は paper_trading.db に分離されます。
- process priority や CPU affinity 設定はプラットフォーム依存で失敗する場合があります（psutil の権限など）。失敗時は警告ログを出してスキップします。

---

## 主要ディレクトリ構成

（リポジトリ内 src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py  (バージョン情報)
  - config.py              (Settings / .env 自動読み込みロジック)
  - config_setup.py        (対話式 .env ウィザード)
  - validate_config.py     (設定検証 CLI)
  - run_monitoring.py      (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py       (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py  (Paper Trading レポート生成)
  - ai/
    - news_nlp.py           (ニュース NLP / OpenAI によるセンチメント)
    - regime_detector.py    (市場レジーム判定)
  - monitoring/
    - monitoring_db.py      (SQLite スキーマ初期化・永続層)
    - monitoring_engine.py  (各 Monitor の統合ポーリング)
    - system_monitor.py     (システム状態・データ鮮度監視)
    - trade_monitor.py      (注文滞留・約定異常監視)
    - risk_monitor.py       (ドローダウン・ポジション上限監視)
    - kill_switch.py        (kill.flag 制御)
    - alert_manager.py      (LINE push 通知)
  - portfolio/
    - portfolio_builder.py  (候補選定・重み計算)
    - position_sizing.py    (株数決定・資金制約・単元丸め)
    - risk_adjustment.py    (セクター制限・レジーム乗数)
  - research/
    - factor_research.py    (ファクター計算: momentum/value/volatility)
    - feature_exploration.py (将来リターン、IC、統計サマリ)
  - utils/
    - process_priority.py   (プロセス優先度 / CPU affinity ユーティリティ)
  - (他: execution や data 等のパッケージがプロジェクトに含まれる想定)

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

必要に応じて README を拡張して、運用手順（サービス化、systemd ユニットやコンテナ化手順）、依存パッケージの固定版、より詳細な設定項目一覧やトラブルシューティングを追加できます。追加で載せたい情報があれば教えてください。