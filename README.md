# KabuSys

日本株自動売買システムの一部を実装したライブラリ／スクリプト群です。  
このリポジトリは、戦略研究・ポートフォリオ構築・発注エンジン・監視・AIによるニュース評価などのコンポーネントを含みます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的のために設計されたモジュール群です。

- 市場データ（DuckDB）を用いたファクター計算・研究機能
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定・リスク調整）
- 発注エンジン（ExecutionEngine）によるブローカーとのやり取り（本番 / ペーパートレード切替）
- 実行状況・システムの監視（Monitoring）と Kill Switch（停止フラグ）
- ニュースの NLP 評価（OpenAI を使ったセンチメント算出）
- 運用支援 CLI（環境設定ウィザード・設定検証・検証レポート生成）

設計方針として、ルックアヘッドバイアスを避ける設計、外部 API 呼び出しのフェイルセーフ、DB の冪等な初期化などが組み込まれています。

---

## 主な機能一覧

- config モジュール
  - .env の自動読み込み（プロジェクトルートに基づく）
  - Settings クラスで環境変数を型・妥当性チェック付きで提供
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を指定可能）
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor: 発注ログの監視（滞留注文・異常約定など）
  - risk_monitor: ドローダウン・ポジション数上限監視とダッシュボード更新
  - kill_switch: 条件を満たすと data/kill.flag を書き込むことで Execution を停止
  - monitoring_db: SQLite を用いた監視ログ保存（テーブルの自動作成 / マイグレーション）
  - monitoring_engine: 各 Monitor を束ねて定期実行
- ポートフォリオ（portfolio）
  - 候補選定、等分配/スコア加重の重み計算、セクターキャップ、レジーム乗数、株数決定（単元丸め・利用可能現金のスケーリング）
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（ai）
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント算出（ai_scores テーブルへ書き込み）
  - regime_detector: MA とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール
  - config_setup.py: .env を対話式に生成／更新するウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

1. Python（推奨: 3.10 以上）を用意します。

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がない場合、代表的な依存を個別にインストールしてください）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証を使う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに移動し、.env を用意します。
   - 対話式で生成する:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参照して `.env` を作成してください。
   - .env は絶対に Git にコミットしないでください。

4. DB 初期化 / ディレクトリ作成
   - デフォルトでは `data/` に以下のファイルが使われます:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite、監視用)
     - data/paper_trading.db (ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading 時)
     - data/kill.flag, data/stop_requested.flag, data/execution.pid（運用用フラグ等）
   - logging_setup がログディレクトリ `logs/` を作成します。

注意: Settings は .env の値を基に動作します。JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等は必須です（validate_config でチェック可能）。

---

## 環境変数（主なもの）

- 必須（例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
    - paper_trading: MockBroker を使い、別 DB (PAPER_TRADING_SQLITE_PATH) に記録
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)

- Execution / Monitoring
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（Mock の約定挙動）
  - PAPER_TRADING_SQLITE_PATH: 上述

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector などで使用

---

## 使い方（主要コマンド例）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告もエラー扱い
  ```

- ExecutionEngine を起動（本番 / ペーパー混在ロジックを内包）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンが停止します。
  - 実行時に `data/execution.pid` が作成されます（pid ファイルパスは設定可能）。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視実行は monitoring DB（settings.sqlite_path）にログを保存します（環境にかかわらず sqlite_path を使用）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db、`--db` で上書き可。

- AI モジュール（プログラムから呼び出し）
  - ニュース評価:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

---

## ログ / データファイル

- logs/<app_name>.log: 日次ローテートされたログファイル（ログは console とファイルに出力）
- data/
  - kabusys.duckdb: DuckDB（市場データ / 研究データ）
  - monitoring.db: SQLite（監視・発注ログ）
  - paper_trading.db: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading）
  - kill.flag: Kill Switch による停止フラグ（ExecutionEngine 停止のため）
  - stop_requested.flag: スクリプト停止要求（運用用）
  - execution.pid: ExecutionEngine の PID

注意: run_monitoring のドキュメンテーションにもある通り、Monitoring は環境にかかわらず本番 sqlite_path を参照します（監視ログは一元管理するため）。

---

## ディレクトリ構成

以下は `src/kabusys` 内の主要ファイル／ディレクトリ構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py             — 環境変数 / Settings
  - config_setup.py       — .env ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する想定)
  - execution/            — 発注エンジン周り（Engine / BrokerFactory / OrderManager など）
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
  - data/                 — データ処理 / pipeline / stats (想定)

（実際のファイル一覧はリポジトリを参照してください）

---

## 開発者向けメモ / 運用注意

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ペーパートレードは本番 DB と分離されています。KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、キーと利用量には注意してください。
- ログディレクトリ作成に失敗した場合はコンソールログのみで継続します（警告が出ます）。
- monitor と execution は stop/kill 用にフラグファイルを使用します。運用時はこれらの挙動（作成・クリア）を理解したうえで運用してください。
- validate_config で起動前に設定チェックを行うことを推奨します。

---

この README はコードベースの主要な使い方・設計ポイントをまとめたものです。詳細な API 使用法や内部アルゴリズム（PortfolioConstruction.md / StrategyModel.md など）は該当ドキュメントを参照してください。必要であれば README を拡張して具体的な API 仕様やサンプルワークフロー（データ取得 → 研究 → シグナル → 発注）を追加します。