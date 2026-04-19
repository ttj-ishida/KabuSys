# KabuSys

日本株自動売買システムのリファクタリング済みコアライブラリと起動スクリプト群。

概要・ユーティリティ・Execution / Monitoring / Research / AI 等の主要コンポーネントを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア実装です。主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）
  - 実口座／ペーパートレード（MockBroker）を切り替え可能
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - リコンサイル（Reconciler）
- 監視（Monitoring）
  - システム稼働監視（CPU/メモリ/ディスク、プロセス生存確認）
  - 取引監視（滞留注文・約定異常など）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件を満たしたら data/kill.flag を書き込み Execution を停止）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算、ポジションサイジング、セクターキャップ、レジーム乗数
- リサーチ / ファクター（DuckDB を用いたファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC 計算・統計サマリー
- AI モジュール
  - ニュースセンチメント（OpenAI を用いたニュース NLP）: ai.news_nlp
  - 市場レジーム判定（ma200 + マクロセンチメント）: ai.regime_detector
- 開発ツール
  - 環境ウィザード（.env 作成支援）
  - 設定検証 CLI（validate_config）
  - Paper Trading レポート生成ツール（tools.paper_verification_report）

---

## 主な機能一覧

- 環境管理
  - .env（自動ロード）/ .env.local 優先度対応
  - Settings クラスによる集中管理（KABUSYS_ENV, DB パス, 各種閾値 等）
- 起動スクリプト（モジュールとして実行可能）
  - run_execution.py: ExecutionEngine 起動
  - run_monitoring.py: SystemMonitor ポーリング起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視と通知
  - MonitoringDB（SQLite）でログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager（抽象）経由で通知（LINE 等の実装は別途）
  - KillSwitch による安全停止
- ポートフォリオ構築
  - 候補選定（score によるソート）
  - 等重・スコア加重・リスクベース配分
  - 単元株丸め、最大ポジション／アグリゲートキャップ制御
- リサーチ
  - DuckDB 接続を受け、prices_daily / raw_financials などのテーブルを参照して計算
- AI（OpenAI）
  - ニュースを銘柄別に集約して LLM へ送信、スコアを ai_scores テーブルへ保存
  - マクロニュースによるレジーム判定（ma200 との組合せ）

---

## 動作要件（目安）

- Python 3.10+
  - typing の `X | Y` 構文を使用しているため 3.10 以上を想定
- 主な依存パッケージ（プロジェクトで実行する場合に必要）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（validate_config で YAML 検証を行う場合に推奨）
- その他: SQLite 標準ライブラリを使用

（実運用時は requirements.txt / Poetry 等で依存管理してください）

---

## セットアップ手順

1. リポジトリをクローン/配置
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実際の依存リストはプロジェクトの requirements.txt / pyproject.toml を参照してください

4. 環境変数（.env）を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参考にしてください

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. DB 初期化・ディレクトリ権限
   - data/ や logs/ の作成と適切な書込み権限を確認
   - 初回実行時に必要な SQLite / DuckDB ファイルは自動生成される（親ディレクトリが存在すること）

注意:
- KabuSys は .env 自動ロードを行います。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要な環境変数（抜粋）

- 基本
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- API
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - LOG_DIR: ログ格納ディレクトリ（デフォルト: logs/）
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai.* を利用する際に必要）

---

## 使い方（起動例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（エンジン起動）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録する
    - data/stop_requested.flag があれば起動せず終了
    - 実行中は PID ファイル（data/execution.pid 等）を管理

- Monitoring（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルト 60 秒間隔で SystemMonitor.check_once() を実行（MONITOR_POLL_INTERVAL で上書き可）
    - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを残す
    - data/stop_requested.flag が存在するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI / Research をプログラムから呼ぶ例（スクリプト内）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

## 運用上のポイント / 注意点

- KABUSYS_ENV による振る舞い差分
  - paper_trading: 発注はモック、専用 DB を使用（本番 DB と分離）
  - live: 実際の発注が行われるため慎重に設定してください（validate_config は live の場合に警告を出します）
- Kill Switch
  - Kill 条件（ドローダウンやポジション上限）に該当すると data/kill.flag を書き込むことで Execution を停止させます
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨
- MONITOR_POLL_INTERVAL は正の整数で指定（無効値はデフォルト 60 秒にフォールバック）
- OpenAI API
  - OpenAI を用いる機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY が必要
  - API 呼び出しはリトライとフォールバック（失敗時は安全に 0.0 等を適用）を実装済み
- プロセス優先度 / CPU affinity
  - 起動時に set_process_priority("high") を呼ぶため、環境や権限によっては警告が発生することがあります（権限不足時はスキップ）
- ロギング
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力
  - ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみになります
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存テーブルにカラムがない場合は ALTER TABLE による簡易マイグレーションを試みます

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール配置（省略形）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (抽象等)
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (runtime)
    - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid
  - config/ (設定テンプレート: system_config.yaml 等)

（上記は主要ファイルのみ抜粋しています。詳細はコードを参照してください）

---

## よくある操作フロー（例）

1. ローカルで検証用セットアップ
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config
2. ペーパートレードで当日のセッションを実行
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution
3. 監視プロセスを別プロセスで起動
   - python -m kabusys.run_monitoring
4. 終了（手動キル）
   - data/stop_requested.flag を作成すると run_* スクリプトが検知して終了
   - data/kill.flag は Kill Switch が書き込むファイル（Execution 停止のため）

---

## トラブルシューティング

- psutil に関連する権限エラー
  - プロセス優先度設定や CPU affinity 設定は権限が必要になることがあります。エラーは警告でスキップされます。
- OpenAI 呼び出し失敗
  - API キーが未設定の場合は ValueError が発生します。キーを設定するか、AI 機能を使わないでください。
  - 一時的な通信障害はリトライされますが、最終的に失敗した場合はフェイルセーフ（スコア 0.0 等）で継続します。
- DB ファイルが見つからない / パス権限
  - validate_config でパスの親ディレクトリ存在を警告します。必要なら mkdir -p data logs を行ってください。

---

## 参考

- .env の作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行: python -m kabusys.run_execution
- 監視: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report

---

必要であれば、README にインストール用 requirements.txt の例や systemd / supervisor 用の起動スクリプトテンプレート、より詳細な環境変数一覧（全キーと説明）を追加します。どの情報を優先して追加しましょうか？