# KabuSys

日本株自動売買システムの一部コンポーネント（実行エンジン、監視、研究・ポートフォリオ構築、AI連携等）を含むリポジトリ用 README。

以下はコードベースから抽出した概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤で、主に以下の役割を持つモジュールを含みます。

- 実行（ExecutionEngine）: 注文作成・発行、リスク管理、オーダー管理
- 監視（Monitoring）: システム状態・注文状態・リスクの定期チェック、Kill Switch
- ポートフォリオ構築: シグナル選定、重み計算、ポジションサイズ決定、セクター制限
- リサーチ: ファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量解析
- AI連携: ニュースのセンチメント評価（OpenAI API を使用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定管理ツール（.env ウィザード・検証）

設計方針として、ルックアヘッドバイアスの回避、フェイルセーフ（外部 API 失敗時に安全に継続）、および本番・ペーパートレードの分離が考慮されています。

---

## 主な機能一覧

- Execution
  - Live / Paper trading 切替（KABUSYS_ENV により MockBroker を利用）
  - リスク管理（ポジション上限、利用率、ドローダウンなど）
  - OrderRepository / OrderManager による発注ログ管理
- Monitoring
  - CPU / メモリ / ディスク使用率の定期記録
  - データ鮮度チェック（DuckDB の prices_daily 等を参照）
  - Trade / Risk / System の統合監視とアラート発報
  - Kill Switch（条件成立時に data/kill.flag を書き込み、ExecutionEngine を停止）
- Research / Portfolio
  - ファクター（モメンタム・バリュー・ボラティリティ）の DuckDB ベース計算
  - ポートフォリオ候補選定、等比率・スコア加重、リスクベースの枚数決定
  - セクターキャップ・レジーム乗数の適用
- AI
  - OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価（銘柄別）
  - レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
  - API レスポンスのバリデーション、リトライ/バックオフ対応
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成（tools/paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity の設定（psutil ベース）

---

## セットアップ手順（概略）

1. リポジトリをクローンして作業ディレクトリへ移動
   - （例）git clone ... && cd your-repo

2. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主に次のライブラリを利用します（requirements.txt が無い場合は手動で）
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（config 検証で YAML をチェックする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数 / .env の設定
   - 推奨: 対話式ウィザードで .env を作成
     - python -m kabusys.config_setup
   - 必須環境変数（一部）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な環境変数（説明は次節にまとめます）
   - 自動ロード:
     - config モジュールはプロジェクトルート（.git または pyproject.toml）を探して自動で `.env` と `.env.local` を読み込みます。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. データディレクトリ作成（必要に応じて）
   - data/ （デフォルト DB やフラグファイル、PID ファイル保存）
   - logs/ （ログ出力先。LOG_DIR で変更可）

---

## 主要な環境変数一覧（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を利用する場合の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（ペーパートレード時はこちらを使用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 本番起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

注意: Settings クラスで値検証を行っています。不正な値は ValueError を送出します。

---

## 使い方（実行例）

全て Python モジュールとして提供されているため、以下のように起動します。作業ディレクトリはプロジェクトルートを想定しています。

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）
    - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可（秒）
  - python -m kabusys.run_monitoring
  - 実行中は data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - 実行時に execution.pid（デフォルト: data/execution.pid）が作成されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI 関連（ニューススコア・レジーム判定）
  - OPENAI_API_KEY を環境変数で設定してください。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用します（DuckDB 接続と target_date を渡す）。

停止方法・Kill Switch:
- 実行プロセスの手動停止: data/stop_requested.flag を作成（run_monitoring / run_execution が検知して終了）
- KillSwitch: リスク条件が満たされると data/kill.flag が作成され、ExecutionEngine 起動中に検出されると停止します。Kill flag は Settings.kill_flag_clear_on_start により起動時に自動クリアを設定できます（本番では 0 推奨）。

ログ:
- デフォルトで stdout にログを出力し、logs/<app_name>.log に日次ローテーションで書き込みます。
- ログレベルは LOG_LEVEL または setup_logging の引数で設定可能。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・ディレクトリの構成（src/kabusys 配下がパッケージ本体）。

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数/.env 管理（自動ロード機能含む）
    - config_setup.py                   — .env 対話式ウィザード
    - validate_config.py                — 設定検証 CLI
    - run_monitoring.py                 — SystemMonitor のポーリング起動スクリプト
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py                — ログ初期化ユーティリティ
      - process_priority.py             — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py                — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py               — CPU/メモリ/ディスク/データ鮮度監視
      - trade_monitor.py                 — （該当コードに基づく監視）
      - risk_monitor.py                 — ドローダウン / ポジション上限監視
      - kill_switch.py                  — Kill Switch 制御
      - monitoring_engine.py            — 各 Monitor を束ねるエンジン
      - alert_manager.py                — （アラート送信ロジック）
    - execution/
      - execution_engine.py             — ExecutionEngine本体
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py            — 候補選定・重み算出
      - position_sizing.py              — 株数決定（lot 単位丸め・aggregate cap）
      - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py              — モメンタム/ボラティリティ/バリュー計算（DuckDB）
      - feature_exploration.py          — 将来リターン・IC・統計サマリー
    - ai/
      - news_nlp.py                     — ニュースを LLM でスコアリングし ai_scores に書き込み
      - regime_detector.py              — レジーム判定（ETF MA + LLM）
    - tools/
      - paper_verification_report.py    — ペーパートレード検証レポート生成
    - data/ (実行時にプロジェクトルートに作成される想定)
      - monitoring.db / paper_trading.db / kabusys.duckdb
      - stop_requested.flag
      - kill.flag
      - execution.pid
  - その他: config/（*.yaml のテンプレート）、pyproject.toml 等

---

## 開発時の注意点 / 補足

- DB
  - Monitoring は Settings.env に関わらず本番 sqlite_path を使用する設計の箇所があります（run_monitoring など）。
  - Paper trading 時は専用 DB（PAPER_TRADING_SQLITE_PATH）を用いて本番 DB と分離します（run_execution）。
- 自動 .env ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。
  - テストなどで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング
  - setup_logging() は stdout とファイル（logs/<app_name>.log）に出力します。ログディレクトリ作成が失敗した場合はファイル出力はスキップされます。
- OpenAI / API 呼び出し
  - AI 関連はネットワーク/API エラーを考慮したリトライとフォールバック（失敗時に安全な既定値）を実装していますが、API コストやレート制限に注意してください。
- テスト
  - 外部 API 呼び出し部分（OpenAI 決定的処理など）はテスト時にモック差替えしやすいよう分離されています（関数単位で差し替え可能）。

---

## 参考コマンドまとめ

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースより機能と使い方を要約したものです。追加の詳細（API 仕様、DB スキーマ詳細、Strategy / Execution の内部ロジック等）は個別ドキュメント（Project のドキュメントディレクトリや Markdown）を参照してください。必要であれば README に追記する内容（例: requirements.txt, 実行時の systemd/cron 例、CI 設定）を教えてください。