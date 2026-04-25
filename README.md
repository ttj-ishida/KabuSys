# KabuSys — README

日本株自動売買システムのコアライブラリ群（開発用リポジトリ向け README）。  
この README はリポジトリ内の Python モジュールを元に要点を整理したものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動／実行コマンド）
- 重要な環境変数
- 停止・制御フラグ
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を持つ Python モジュール群です。

- マーケットデータ（DuckDB）を使ったファクター計算・研究モジュール
- ポートフォリオ構築（候補選定、重み計算、銘柄ごとの株数算出）
- ExecutionEngine（注文送出／注文管理）とペーパートレード分離
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）機構
- ニュース NLP（OpenAI）を使ったセンチメント評価、レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- 検証用のレポート生成スクリプト（Paper Trading 検証レポート）

設計方針の例：
- 本番用 DB とペーパートレード DB を分離（KABUSYS_ENV による）
- ルックアヘッドバイアス回避のため datetime.today() を直接参照しない
- OpenAI 呼び出しはリトライやレスポンス検証を行いフェイルセーフ化

---

## 主な機能一覧

- config: 環境変数の自動読み込み / Settings クラス
- config_setup: 対話式 `.env` 作成ウィザード
- validate_config: 起動前チェック（必須環境変数や config/*.yaml の確認）
- run_execution: ExecutionEngine の起動スクリプト（実取引 / ペーパートレード対応）
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト
- monitoring: monitoring_db（SQLite）、risk_monitor、system_monitor、trade_monitor、kill_switch、alert_manager、monitoring_engine 等
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限・レジーム乗数
- research: ファクター計算（momentum / value / volatility）、特徴量探索ツール
- ai: news_nlp（ニュースセンチメント） / regime_detector（市場レジーム判定）
- tools: paper_verification_report（ペーパートレード検証レポート生成）
- utils: logging_setup（統一ログ設定）、process_priority（優先度・CPU affinity）

---

## セットアップ手順

1. リポジトリをクローンしてソースツリーへ移動
   - Git のプロジェクトルートは .git または pyproject.toml により自動検出します。

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用、任意）
   - 具体的な requirements.txt がない場合は手動インストール:
     - pip install duckdb psutil openai PyYAML

4. 初期設定 (.env)
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` をプロジェクトルートに作成（.env.example を参考）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります。

6. データディレクトリ（ログ・DB 等）の作成
   - デフォルトのパスは `.env` で上書き可能（下記参照）。ログは `logs/`、データは `data/` に保存する想定。

---

## 使い方

以下は主要なスクリプトの実行例です。実行はプロジェクトルートから行ってください。

- 環境ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid を使用（設定で上書き可）
    - プロセス優先度を "high" に設定しようとします（psutil が必要）

- Monitoring の起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60秒）
  - 監視は Monitoring の SQLite（settings.sqlite_path）を使います（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）
  - 停止は data/stop_requested.flag を作成することでループを抜けます

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（デフォルト: data/paper_trading.db）

- AI 関連
  - OpenAI を利用する処理（news_nlp.score_news / regime_detector.score_regime）は OPENAI_API_KEY が必要
  - これらは DuckDB 接続を受け取り DB 内の raw_news 等を参照して書き込みを行います
  - API 呼び出しはリトライ・レスポンスバリデーションを行う設計です

---

## 重要な環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境・動作モード:
  - KABUSYS_ENV — environment: development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

- DB / ファイルパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — monitoring 用 SQLite（run_monitoring は常に本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0 or 1): 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

- AI（OpenAI）:
  - OPENAI_API_KEY — gpt 系モデルを使う場合に必要

- その他:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading での MockBroker の fill モード（instant/partial/never/reject、デフォルト "instant"）
  - LOG_DIR — ログ出力先（デフォルト logs/）

注意: .env 自動読み込み機能が有効（デフォルト）で、プロジェクトルートにある `.env` / `.env.local` を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 停止・制御フラグ

- data/stop_requested.flag
  - run_execution/run_monitoring のポーリングループで存在を確認し、見つかれば安全に停止します。
  - 外部プロセス（運用スクリプト）から停止指示を出す際に使用。

- data/kill.flag（Kill Switch）
  - RiskMonitor / KillSwitch の判定により書き込まれ、本番の ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は drawdown やポジション上限違反などの条件で write します。KillSwitch の書き込みは冪等です（既存なら上書きしない）。

- PID ファイル
  - data/execution.pid: ExecutionEngine の PID を記録する用途など。

---

## ロギング

- 共通のログ設定ユーティリティを持ちます（kabusys.utils.logging_setup.setup_logging）。
- デフォルトではコンソール出力（stdout）と `logs/<app_name>.log`（日次ローテーション・30日保持）に出力します。
- LOG_DIR / LOG_LEVEL は環境変数で制御可能。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュールがまとまっています。主要ファイルの抜粋ツリーは以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照：TradeMonitor 実装あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (アラート送信ロジック)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/ (上記)
    - data/ (想定ディレクトリ: DB ファイル・フラグを置く)
    - logs/ (ログ出力先)

（注）上記はコードベース内で確認できる主要モジュールの一覧です。細かな補助モジュールや実装ファイルが追加で存在する可能性があります。

---

## 運用メモ / 注意点

- run_monitoring は Monitoring 用の SQLite（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計になっています（意図的）。
- run_execution は KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）と Mock ブローカーを使用して本番 DB と分離します。
- OpenAI を利用する機能は API キーが必要です。API コストやレート制限に注意してください。実行時はネットワーク・API エラーを考慮したリトライが組み込まれていますが、運用ルールを決めてください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って kill.flag をクリアしないようにするため）。
- .env は機密情報を含むため Git へコミットしないでください。

---

この README はコード内のドキュメント文字列・設計注釈に基づいてまとめています。追加で「インストール用 requirements.txt の生成」や「Docker / systemd 用の起動ユニット例」を希望する場合は教えてください。