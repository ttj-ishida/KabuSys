# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI 補助（ニュース NLP / レジーム判定）などを含むモジュール群で構成されています。README は開発者・運用者向けの導入手順と主要コンポーネントの説明を日本語でまとめたものです。

---

## 概要

KabuSys は以下の目的を持つモジュール群を提供します。

- 価格データや財務データからファクター（Momentum / Value / Volatility 等）を計算
- ポートフォリオ候補選定・重み付け・株数決定（リスク制約・単元丸めを含む）
- 発注エンジン（ExecutionEngine）と BrokerClient 抽象化（paper_trading モードをサポート）
- 監視サブシステム（システム状態・注文ログ・リスク監視）と Kill Switch
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）およびレジーム判定
- 運用支援ツール（設定ウィザード・設定検証・ペーパートレード検証レポート など）

設計方針として、DB（SQLite / DuckDB）を利用した永続化、ユニットに分割された純粋関数群（ポートフォリオ計算等）、フェイルセーフ（API 失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- config 管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行 / 監視
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能
- 監視（monitoring）
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス生存チェック
  - trade_monitor: 注文滞留・約定異常の検出（ログ参照）
  - risk_monitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を生成し ExecutionEngine を停止させる
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重、セクター上限適用、レジーム乗数、株数算出（単元丸め）
- リサーチ（research）
  - ファクター計算（Momentum/Value/Volatility）、将来リターン、IC 計算、統計要約
- AI（ai）
  - news_nlp: OpenAI を用いたニュースセンチメントスコア生成（ai_scores テーブルに保存）
  - regime_detector: ETF + マクロニュースで市場レジーム判定、market_regime に書き込み
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

---

## 要件（推奨）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （PyYAML は設定ファイルの検証用。必須ではない）
- ※ 実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください（この README 内のコードから主要依存を推測しています）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... ; cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは pyproject.toml を使用している場合は pip install .[dev] 等

4. 環境変数の初期設定（.env 作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参照して JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD などを設定

5. 設定検証
   - python -m kabusys.validate_config
   - 本番起動前に --strict オプションで警告も FAIL 扱いにすることを推奨:
     - python -m kabusys.validate_config --strict

6. DB ディレクトリ作成（必要なら）
   - デフォルトのパスは data/ 以下（DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db）
   - .env でカスタムパスを指定できます

---

## 主要環境変数（主なもの）

必須（稼働に最低必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI 関連
- OPENAI_API_KEY — news_nlp / regime_detector などで必要

運用・DB 設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）

ロギング・監視
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）

その他
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト時に便利）

（注）config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。

---

## 使い方（起動コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading にすると MockBroker を使用し data/paper_trading.db に記録。
    - 起動時に data/stop_requested.flag が既に存在するとエンジンは起動せず終了します。
    - 実行中は data/execution.pid に PID が書かれます（設定で変更可）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 監視は Settings.sqlite_path を（環境に関係なく）使用して監視 DB に接続します。
    - 停止は data/stop_requested.flag の作成で行います（監視はこのフラグを検出すると終了します）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、OPENAI_API_KEY を利用して ai_scores に書き込む
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill Switch

- KillSwitch はリスク条件（ドローダウンやポジション数超過）で data/kill.flag を作成します。ExecutionEngine はこのフラグの存在を検出して停止します。
- 手動停止（運用者）:
  - data/kill.flag を作成すればエンジン停止シグナルを送れます（内容は理由の文字列）。
  - data/stop_requested.flag を作成すると run_* スクリプトのメインループが検出して終了します（監視・実行の両方で使用）。

---

## ログ設定

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - コンソール（stdout）出力と日次ローテーションするファイル（logs/<app_name>.log）を自動設定
  - ログレベルは引数／環境変数 LOG_LEVEL（またはデフォルト INFO）で決定
  - ログディレクトリは LOG_DIR 環境変数で上書き可能（デフォルト logs/）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・パッケージのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py                — OpenAI を使ったニューススコアリング
      - regime_detector.py         — レジーム判定
    - monitoring/
      - monitoring_db.py           — SQLite 永続層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py           — （アラート送信はここで集約）
    - execution/
      - execution_engine.py       — 発注エンジン（EngineCore）
      - broker_factory.py
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
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                        — デフォルトの DB / フラグ / pid ファイルが置かれる想定ディレクトリ（実行時に作成）

---

## 実装上の注意点 / 運用メモ

- .env 自動読み込み:
  - OS 環境変数 > .env.local > .env の優先順位で読み込みます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで有用）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブル作成と簡単な列追加（マイグレーション）を行います。
- Paper Trading 分離:
  - run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使います。本番 DB と完全分離されます。
- AI モジュール:
  - OpenAI API 呼び出しは外部ネットワークに依存します。API キーと呼び出し回数の管理に注意してください。
  - API エラーは基本的にリトライやフォールバックで安全側に処理されますが、ログで失敗を必ず確認してください。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼んでプロセス優先度を上げます（プラットフォームに依存して実行可能か試行します）。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README は主要な利用フローとコードベースの構成を概観するためのものです。詳細な設計・仕様（PortfolioConstruction.md 等）や追加の運用手順がある場合は、該当ドキュメントを参照してください。必要であれば README に追記しますので、補足したい点（例: 実際の requirements.txt、運用チェックリスト、systemd ユニット例 など）を教えてください。