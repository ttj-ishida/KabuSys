# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ・実行スクリプト群）。  
この README はコードベースの主要コンポーネント、セットアップ手順、起動方法、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は、J-Quants / kabuステーション 等を利用した日本株の自動売買基盤です。  
主な責務は以下です。

- データ基盤（DuckDB を分析用に、SQLite を監視・注文履歴用に使用）
- シグナル生成・ファクター計算（research モジュール）
- ポートフォリオ構築・ポジションサイズ計算（portfolio モジュール）
- ExecutionEngine による発注処理（本番 / ペーパートレード切替）
- 監視 (monitoring)：システム稼働監視、取引ログ検査、リスク監視、Kill Switch
- AI 補助（news NLP によるニュースセンチメント、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計上の注意点：
- 本番 / ペーパートレードは明確に分離されるよう設計（DB パス等で切替）。
- LLM（OpenAI）利用箇所は環境変数による API キー管理・リトライ等の安全策あり。
- 自動的に .env をプロジェクトルートの `.env` / `.env.local` から読み込み（無効化可能）。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: `kabusys.config_setup`
- 設定検証 CLI（環境変数・config/*.yaml のチェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `run_execution.py`
  - KABUSYS_ENV=paper_trading の場合は MockBroker（ログは data/paper_trading.db）
- 監視ループ起動スクリプト（SystemMonitor）: `run_monitoring.py`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）
  - 監視ログは SQLite（Settings.sqlite_path）に永続化
- 監視エンジン（複数モニタ統合、Kill Switch/アラート連携）
- RiskMonitor（ドローダウン・ポジション上限監視） / TradeMonitor / SystemMonitor
- AI モジュール
  - news_nlp: ニュースを LLM でスコアリングし ai_scores に保存
  - regime_detector: MA200 とマクロニュースを合成して市場レジーム判定
- Research（ファクター計算、将来リターン、IC 計算 等）
- Portfolio（候補選定・重み計算・ポジションサイズ決定）
- ユーティリティ（ログ設定、プロセス優先度設定 等）
- 開発用ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発 / 実行環境）

※ プロジェクトに requirements ファイルがある前提です（ない場合は依存ライブラリを手動でインストールしてください）。

1. Python（推奨 3.10+）を用意する。

2. 仮想環境を作成・有効化：
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存関係をインストール（requirements.txt がある場合）:
   - pip install -r requirements.txt

   主要な依存例（プロジェクト参照）:
   - duckdb
   - psutil
   - openai（OpenAI SDK）
   - PyYAML（設定ファイルチェック用。任意）

4. .env を作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - 対話ウィザードが .env を生成します。
   - あるいは手動で `.env` を作成してください（.env.example を参考に）。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   OpenAI を使う機能を使う場合:
   - OPENAI_API_KEY を設定

5. 設定検証:
   - python -m kabusys.validate_config
   - 問題がなければ OK メッセージが出ます。`--strict` を付けると警告も失敗として扱います。

6. データディレクトリ作成（必要に応じて）:
   - デフォルトの DB / PID / フラグファイルは `data/` 配下に置かれます。自動で作成されることもありますが、権限等に注意してください。

7. ログディレクトリ:
   - デフォルトは `logs/`。必要に応じて `LOG_DIR` 環境変数で変更可能。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 解説:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` があると起動せず終了します。
    - 実行中は `data/execution.pid` に PID が書かれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - オプション・挙動:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可（デフォルト 60）。
    - 監視は常に本番用 SQLite（Settings.sqlite_path）を使用します（環境に依らず）。
    - 停止するには `data/stop_requested.flag` を作成して監視ループに検知させるか、プロセスを停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - デフォルト DB: `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI モジュール（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI API キーは `OPENAI_API_KEY` 環境変数、または api_key 引数で渡す必要があります。

---

## 主要設定（環境変数）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

注意: 必須環境変数が未設定だと validate_config や Settings によりエラーになります。

---

## 安全機能・運用上の注意

- Kill Switch
  - RiskMonitor 等が条件を満たすと `data/kill.flag` に理由を書いて ExecutionEngine を停止させます。
  - Kill Switch の自動クリアは `KILL_FLAG_CLEAR_ON_START` を 1 にすると有効（本番では 0 を推奨）。

- PID / Stop フラグ
  - 実行エンジンは `data/execution.pid` に PID を書きます。
  - 停止制御は `data/stop_requested.flag`（run_monitoring / run_execution が監視）によって行います。

- 本番運用時の警告
  - KABUSYS_ENV=live を設定すると validate_config で警告が出ます。LINE 通知設定や Kill Switch の挙動を十分確認してください。

- OpenAI 利用
  - API 呼び出しはリトライ・バックオフを実装していますが、API キーやコスト管理には注意してください。
  - LLM 出力は JSON バリデーションを行いますが、想定外のレスポンスはスキップしてフェイルセーフで継続します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys/` 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - config_setup.py                -- .env 対話式ウィザード
  - validate_config.py             -- 設定検証 CLI
  - run_execution.py               -- ExecutionEngine 起動スクリプト
  - run_monitoring.py              -- SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  -- ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                  -- ニュース NLP スコアリング
    - regime_detector.py           -- 市場レジーム判定
  - research/
    - factor_research.py           -- Momentum/Value/Volatility 等の計算
    - feature_exploration.py       -- 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py         -- 候補選定 / 重み計算
    - position_sizing.py           -- 発注株数計算
    - risk_adjustment.py           -- セクター制限 / レジーム乗数
  - monitoring/
    - monitoring_db.py             -- SQLite 用永続化層
    - system_monitor.py            -- システム状態監視
    - risk_monitor.py              -- ドローダウン・ポジション数監視
    - trade_monitor.py             -- 取引ログ監視（存在する想定）
    - monitoring_engine.py         -- 各 Monitor を束ねる
    - kill_switch.py               -- Kill Switch 書き込みユーティリティ
    - alert_manager.py             --（存在想定）通知管理
  - execution/
    - execution_engine.py          -- ExecutionEngine（存在想定）
    - broker_factory.py            -- Broker クライアント生成
    - order_manager.py             -- 注文管理
    - order_repository.py          -- 注文永続化
    - reconciler.py                -- 差分調整
    - risk_manager.py              -- 実行時リスク管理
  - data/                           -- 既定: data/kabusys.duckdb, data/monitoring.db 等
  - logs/                           -- ログ（デフォルト）

（注）一部モジュールは README 作成時点で抜粋されたコード中に参照のみされている場合があります。詳細はソースを参照してください。

---

## よく使うコマンドまとめ

- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 参考・補足

- DB マイグレーションやスキーマの初期化は monitoring_db.init_monitoring_db() で行われます。
- ログ設定は kabusys.utils.logging_setup.setup_logging() を通じて統一されます（コンソール + 日次ローテートファイル）。
- プロセス優先度設定ユーティリティ（psutil を利用）： kabusys.utils.process_priority.set_process_priority()
- 開発時に自動で .env を読み込む挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

この README はコードベースの主要点をまとめたものです。詳細実装や追加ユーティリティについては各モジュールの docstring とソースコードを参照してください。何か特定の利用シナリオ（デプロイ手順、Docker化、CI/CD 設定等）が必要であれば、その用途に合わせた追補を作成します。