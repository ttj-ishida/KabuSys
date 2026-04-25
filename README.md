# KabuSys

日本株自動売買プラットフォームのコアライブラリ群（モニタリング・実行エンジン・ポートフォリオ構築・リサーチ・AI ユーティリティ等）。  
このリポジトリは、ローカル開発 / ペーパートレード / 本番（live）に対応したモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な目的は以下です。

- ExecutionEngine による発注処理（実口座／ペーパートレード切替）
- Monitoring によるプロセス可用性・注文ログ・リスク監視、Kill Switch（停止フラグ）による安全停止
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出）
- リサーチ用ファクター計算（DuckDB を利用）
- ニュースの NLP によるセンチメント評価（OpenAI）
- 各種 CLI ツール（設定ウィザード・設定検証・ペーパートレード検証レポート）

設計方針として、可能な限り副作用を抑えた純粋関数群と、SQLite / DuckDB を使ったデータ永続化・分析基盤を分離しています。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（発注・注文管理・リスク管理・約定調整）
  - BrokerClientFactory による実口座 / MockBroker の切替（KABUSYS_ENV=paper_trading）
  - Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor: 注文ログの巡回（滞留注文・異常約定検出等）
  - RiskMonitor: ドローダウン・ポジション数の監視とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を安全に停止
  - MonitoringEngine: 上記を束ねてポーリング実行（interval 可変）

- ポートフォリオ（Portfolio）
  - 銘柄選定（スコア順）
  - 等重・スコア加重の重み算出
  - セクター上限適用、レジームに応じた投下資金乗数
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）

- リサーチ（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（スピアマン）などの解析ユーティリティ

- AI（OpenAI）
  - ニュース NLP（銘柄別センチメントを ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ETF ma200 乖離 + マクロセンチメント合成）
  - OpenAI 呼び出しは堅牢にリトライ・バリデーションを行う設計

- ツール / CLI
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...  
   - cd <repo>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール  
   （requirements.txt は本リポジトリに含まれていないため、最低限必要なパッケージを例示します）
   - pip install duckdb psutil openai
   - （任意）PyYAML は config.yml 検証で使われる: pip install PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合は表示に従って修正。--strict を付けると警告も失敗扱いになります。

6. 初期データディレクトリ
   - デフォルトで使用するディレクトリ: data/ （SQLite DB 等）
   - logs/ にログファイルが出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能。

注意:
- OpenAI API を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定してください。
- 実口座アクセスには J-Quants / kabuステーション のトークン等が必要です（.env に設定）。

---

## 環境変数（主要）

以下はよく使う環境変数（デフォルト値を含む）。詳しくは kabusys.config.Settings を参照してください。

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…） — デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

---

## 使い方（起動例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（または Ctrl-C）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db に記録されます。
  - 実行中に停止するには data/stop_requested.flag を作成するか、実行プロセスに対して標準的に SIGINT 等を送ってください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア等）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をアプリケーションコードから呼び出してください（OpenAI API キー必須）。

ログ:
- setup_logging により stdout と logs/<app_name>.log（日時ローテーション）が設定されます。ログディレクトリは LOG_DIR 環境変数で変更可能。

---

## 停止 / Kill Switch の動作

- KillSwitch モジュールはリスク / ドローダウン・ポジション上限などの条件に応じて data/kill.flag を書き込みます。
- ExecutionEngine 起動時には kill.flag の有無や、KILL_FLAG_CLEAR_ON_START 設定に注意してください（本番で自動クリアは危険）。
- 各起動スクリプトは data/stop_requested.flag を参照して graceful shutdown（ループ脱出や engine.stop() 呼び出し）を行います。

---

## ローカルファイル・ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（src/kabusys 配下抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化層
    - system_monitor.py
    - trade_monitor.py       — （コードベース内に参照あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信管理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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
  - data/                    — （実行時に作成される / デフォルトで DB を置く場所）
  - tools/
    - paper_verification_report.py

外部依存（主要）:
- duckdb
- psutil
- openai
- (任意) PyYAML（validate_config の YAML 検証で使用）

---

## 実運用時の注意点 / トラブルシューティング

- プロセス優先度設定（psutil）や CPU affinity は管理者権限が必要な場合があります。権限不足で設定に失敗しても警告ログを出して継続します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（エラーにはならない）。
- OpenAI 呼び出しはリトライ・バリデーションロジックがありますが、API キーやネットワークが正しく設定されていることを確認してください。
- Paper Trading は監視 DB と分離された専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するため、本番資金に影響しません。
- monitor は「監視 DB（SQLITE_PATH）」を環境にかかわらず使用します（監視は本番 DB を想定しているため）。

---

## 開発・拡張メモ

- DuckDB を用いたリサーチ処理は SQL と Python を組み合わせており、prices_daily / raw_financials 等のテーブル設計に依存します。
- AI モジュールは OpenAI の Chat Completions（gpt-4o-mini 等）を使用する想定。出力フォーマットは厳密な JSON を期待します。応答のバリデーション処理が組み込まれています。
- ログのフォーマット / ローテーションは kabusys.utils.logging_setup.setup_logging で一元管理されています。

---

必要に応じて README の追加項目（API リファレンス、設定ファイルの具体例、データスキーマ、開発用ユニットテストの実行方法等）を作成できます。特にどの情報を詳細化したいか教えてください。