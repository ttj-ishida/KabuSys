# KabuSys

日本株向けの自動売買・研究プラットフォーム（KabuSys）のリポジトリ向け README。  
このドキュメントはリポジトリ内のスクリプト・モジュール群（execution / monitoring / research / ai / portfolio など）を簡潔に説明し、導入・起動手順や主な設定項目をまとめたものです。

注意: 実行には Python3 と外部ライブラリ（duckdb, psutil, openai など）が必要です。requirements.txt がある場合はそれを使用して依存関係をインストールしてください。

## プロジェクト概要

KabuSys は日本株の自動売買エンジンと運用支援ツール群の集合です。主な目的は以下の通りです。

- 日次のファクター計算・研究（DuckDB を用いた prices_daily / raw_financials ベースの計算）
- ポートフォリオ構築（候補選定、重み付け、単元調整、リスク制御）
- ExecutionEngine による発注管理（本番・ペーパートレード両対応）
- Monitoring（システム稼働／注文／リスクの監視）と Kill Switch（条件で ExecutionEngine を停止）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- 運用検証ツール（ペーパートレード検証レポート等）

設計方針として、DB 操作は明確に分離され、Look-ahead バイアスや本番誤操作を避ける工夫（ペーパー口座分離・タイムウィンドウ設計・フェイルセーフ）が入っています。

## 機能一覧

- Execution
  - ExecutionEngine 起動（`kabusys.run_execution`）
  - BrokerClientFactory による本番/ペーパー分岐（KABUSYS_ENV=paper_trading で MockBroker）
  - リスク管理（RiskManager）、注文管理（OrderManager）、突合（Reconciler）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン / ポジション上限監視（dashboard, positions）
  - MonitoringEngine: 上記をまとめてポーリングし、KillSwitch や AlertManager へ通知

- Data / Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（スピアマン）等
  - AI: news_nlp（OpenAI でニュースをスコアリング）、regime_detector（MA200 と LLM を組み合わせてレジーム判定）

- Portfolio
  - 銘柄選定（select_candidates）
  - 重み付け（等金額・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- ユーティリティ
  - 環境設定ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）
  - ロギング/プロセス優先度ユーティリティ

## セットアップ手順（基本）

1. リポジトリをクローンし、Python 仮想環境を作成してアクティベートする（任意）:
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール:
   - もし requirements.txt があれば:
     - pip install -r requirements.txt
   - 主な依存パッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（`kabusys.validate_config` の YAML 検証を使う場合）

3. .env の作成:
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは `.env.example`（存在する場合）を参考に手動作成。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. 設定検証:
   - python -m kabusys.validate_config
   - 重要: 本番実行前は `--strict` を付けて警告も FAIL 扱いで検証することを推奨:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）:
   - デフォルト DB / ログ等は `data/` / `logs/` を使用します。自動で作成されますが手動で準備しておくと良いです。

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー発注時の約定モード（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 任意（アラート送信用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: Execution 用の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

## 使い方（起動例）

- 環境をセットした上で、主要なモジュールはモジュール実行（-m）で起動できます。

1. ExecutionEngine の起動
   - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録します。
     - 起動時に `data/stop_requested.flag` が既にあれば起動せず終了します。
     - 停止は外部プロセスで `data/stop_requested.flag` を作成するか（run_execution はこれを監視します）、Kill Switch が `data/kill.flag` を書き込むことでトリガーされます。

2. Monitoring の起動
   - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を高く設定し、Settings.sqlite_path（監視 DB）を使って監視ログを保持します（monitoring は環境にかかわらず本番 sqlite_path を使用）。
     - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
     - 停止は `data/stop_requested.flag` を作成すると監視ループが終了します。

3. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を fail にする）:
     - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可

6. AI / Regime 判定 等（ライブラリ利用）
   - ai モジュールはプログラムからインポートして使用します。例:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - いずれも OPENAI_API_KEY が必要（引数で API キーを渡すことも可）。

ログ出力:
- ログは `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートファイル（デフォルト: logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 `LOG_DIR` で変更可能です。

停止フロー / フラグファイル:
- data/stop_requested.flag: run_monitoring / run_execution のループを安全に終了させるために参照されるファイル。存在するとループは次の周期で終了します。
- data/kill.flag: KillSwitch が条件を満たすと書き込まれ、ExecutionEngine に対する停止シグナルとなります。`KILL_FLAG_CLEAR_ON_START=1` により起動時に自動クリアする設定もあります（本番では危険なのでデフォルトは 0）。

## ディレクトリ構成（主要ファイル）

リポジトリのソースは `src/kabusys` 以下に配置されている想定です。主要な構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings の管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring の起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 層（テーブル作成 / 永続化）
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — 注文関連監視（trade_logs の分析） ※ファイルあり
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各 Monitor の統合ポーリング
    - kill_switch.py         — フラグファイル書き込みによる停止シグナル
    - alert_manager.py       — （AlertManager がある場合）
  - execution/
    - execution_engine.py    — Execution のコア（EngineConfig, run_session など）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLU / OpenAI 呼び出しと ai_scores 書き込み
    - regime_detector.py     — マーケットレジーム判定（MA200 + LLM）
  - data/                    — 実行時に利用する DB / フラグファイル / pid 等（推奨）

その他:
- config/*.yaml            — 各種設定テンプレート（system_config.yaml, strategy_config.yaml 等）
- .env / .env.local        — 環境変数ファイル（生成は config_setup.py で可能）
- logs/                    — ログ出力先（日次ローテート）

（上記は主要ファイルを抜粋したもので、細かいモジュールは実装に合わせて追加されます）

## 開発者向けメモ / 注意点

- Monitoring は監視 DB（Settings.sqlite_path）を必ず使用します。開発環境でも monitoring が別 DB を使う挙動はないため注意してください。
- ExecutionEngine のペーパートレードは DB を分離しており、KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用します。
- OpenAI 関連の処理は API 呼び出し失敗をフェイルセーフに扱い、スコア未取得時はスキップやデフォルト値で続行する設計です。ただし API キーが未設定だと明示的に例外を出す箇所もあります（呼び出し先により異なる）。
- log ディレクトリの作成に失敗した場合はファイルハンドラを設定せず stdout のみで動作します（setup_logging の動作）。
- 各種 CLI スクリプトは Python モジュールとして実行する形（python -m kabusys.<module>）を想定しています。

---

この README はコードベースの現状（主なモジュール、設定、起動方法）を短くまとめたものです。実運用に移す前に .env の必須項目を設定し、`python -m kabusys.validate_config --strict` によるチェックを必ず行ってください。追加の詳細や具体的なパラメータ調整は各モジュール（config/*.yaml、EngineConfig、RiskConfig 等）の実装コメントを参照してください。