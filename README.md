# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。  
主要機能は以下のカテゴリに分かれ、実運用を意識した設計（監視・フェイルセーフ・ペーパートレード分離など）になっています。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視コンポーネント（System / Trade / Risk モニタ）
- Kill Switch（異常時にエンジン停止）
- ポートフォリオ構築（候補選定、重み付け、株数計算）
- 研究用モジュール（ファクター計算、IC、forward returns）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント：
- 本番とペーパートレードの DB を明確に分離
- .env による環境設定（自動読み込み/ウィザード/検証ツールあり）
- DuckDB を分析用 DB、SQLite を監視/発注ログ用 DB として利用
- OpenAI を用いたニュース解析・レジーム判定（オプション、APIキー必須）

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と完全分離。
- 監視ループ起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL で間隔指定可能（デフォルト 60 秒）。
- 設定管理・ウィザード
  - config_setup.py: 対話式で .env を作成/更新。
  - validate_config.py: .env と config/*.yaml の検証（--strict で警告を FAIL 扱いに）。
- モニタリング
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine: CPU/メモリ/ディスク、注文滞留、約定異常、ドローダウン等を監視し、アラートや Kill Switch を管理。
  - monitoring_db: SQLite テーブルの初期化・読み書き。
- AI / ニュース処理
  - ai.news_nlp.score_news: raw_news を LLM（OpenAI）で解析し ai_scores に書き込む。
  - ai.regime_detector.score_regime: ma200 とマクロニュースを合成して市場レジームを判定。
- 研究・分析
  - research.factor_research: Momentum / Volatility / Value などのファクター計算（DuckDB ベース）。
  - research.feature_exploration: forward returns / IC / 統計サマリー 等。
- ポートフォリオ構築
  - portfolio.portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み付け、株数決定、セクター制限、レジーム乗数等。
- 運用ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成。

---

## セットアップ手順

前提
- Python 3.9+ を想定（ソースは型注釈に依存）
- Git リポジトリまたは pyproject.toml がプロジェクトルートにあることを想定（自動 .env ロードのため）

1. リポジトリをクローン / 配置
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使ってください。なければ概ね以下）
   - pip install duckdb psutil openai requests PyYAML

   注意: OpenAI クライアントや psutil、duckdb は一部プラットフォームでネイティブ依存があるため、OS ごとの調整が必要になる場合があります。

4. 環境ファイル作成
   - 対話式ウィザードで .env を作成: python -m kabusys.config_setup
   - または .env.example を参考に手動作成

5. 設定検証（必須項目が満たされているか確認）
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL にする）: python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト起動時に必要テーブルは自動作成・マイグレーションされます（monitoring_db.init_monitoring_db が実行されます）。

---

## 環境変数の主な項目（.env）

主なキー（デフォルト / 必須の概略）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意; デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (分析 DB; デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite; デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject; デフォルト: instant)
- KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL; デフォルト: INFO)
- OPENAI_API_KEY (AI 機能使用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信用、未設定なら送信はスキップ)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: "0" or "1"; 本番は 0 推奨)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- MONITOR_POLL_INTERVAL (run_monitoring.py のポーリング間隔秒数, デフォルト 60)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動メモ:
    - 起動時に set_process_priority("high") を呼び出します（psutil に依存し権限により失敗する場合は警告）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) を使用し、MockBroker を使ってペーパートレードを行います。
    - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
    - 実行中に data/stop_requested.flag が作成されると Engine.stop() が呼ばれて安全に停止します。
    - PID ファイルはデフォルト data/execution.pid（Settings.pid_file_path）に書き込まれます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。
  - 停止は data/stop_requested.flag の作成で行います（存在を検知してループを抜ける）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で DB パスを明示指定可能（優先順位: --db > PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db）

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続、target_date: date
    - api_key が None の場合 OPENAI_API_KEY 環境変数を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OPENAI_API_KEY を使用

- ライブラリ関数（研究 / ポートフォリオ）
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - kabusys.portfolio.calc_position_sizes / apply_sector_cap / calc_regime_multiplier

---

## 停止・Kill Switch・フラグファイル

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視する「停止要求」フラグ。存在すると起動を抑止 / 動作中に停止します。

- data/kill.flag（デフォルト、Settings.kill_flag_path）
  - KillSwitch が書き込むフラグファイル。ExecutionEngine はこのフラグを監視して緊急停止する仕組みです。KillSwitch は drawdown やポジション上限などの条件で書き込みます。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で kill.flag をクリアします（本番では 0 推奨）。

---

## ログ / プロセス優先度

- ログレベルは LOG_LEVEL 環境変数で指定（デフォルト: INFO）。
- プロセス優先度は起動時に set_process_priority("high") を呼び出します。psutil によるためプラットフォーム依存・権限依存で警告が出る場合があります。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings クラス、自動 .env 読み込み
- config_setup.py          — .env ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 書込み
  - regime_detector.py    — レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化・CRUD
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/                — 発注周り（OrderManager 等。ソース全体がある前提）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

データディレクトリ（実行時に期待されるファイル/パス例）
- data/kabusys.duckdb        (DuckDB のデフォルト)
- data/monitoring.db         (Monitoring SQLite DB のデフォルト)
- data/paper_trading.db      (Paper Trading 用 SQLite DB)
- data/execution.pid         (PID ファイル、デフォルト)
- data/kill.flag             (Kill Switch フラグ)
- data/stop_requested.flag   (停止要求フラグ)

---

## 注意点・運用メモ

- 本番運用時は KABUSYS_ENV を "live" に設定し、.env の LINE トークンなどは適切に設定してください。validate_config の live 向け警告を確認してください。
- Paper Trading は本番 DB と完全分離するよう設計されています（paper_trading モードで PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須。API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 等でフォールバック）を含みますが、API 利用回数/コストに注意してください。
- psutil によるプロセス優先度や cpu_affinity の設定は権限によって失敗することがあります（警告ログのみ）。
- monitoring は監視ログを常に production sqlite_path に保存します（KABUSYS_ENV に依存しない点に注意）。

---

もし README に追加したい内容（例: サンプル .env、実行例のスクリーンショット、テスト実行方法など）があれば教えてください。必要に応じてセクションを拡張して具体例やコマンド例を追加します。