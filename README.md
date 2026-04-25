# KabuSys

日本株自動売買システムのリポジトリ（モジュール群のみ）。  
この README は、プロジェクトの目的、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わるコンポーネント群（市場リサーチ、ポートフォリオ構築、発注エンジン、監視、AIベースのニュース解析など）を提供する Python パッケージです。  
設計方針の要点：

- DuckDB / SQLite を用いたローカル分析・ログ永続化
- 本番 / ペーパートレードの切替（環境変数 `KABUSYS_ENV`）
- LLM（OpenAI）を用いたニュースセンチメント・レジーム判定の統合
- 監視（Monitoring）/ Kill Switch / アラートの仕組み
- テスト容易性を考慮した設計（自動 .env ロードの抑制、モックブローカー等）

パッケージバージョン: `__version__ = "0.1.0"`

---

## 主な機能一覧

- 設定管理
  - `.env` 自動ロード（プロジェクトルート検出）および `Settings` クラスによる環境変数アクセス
  - 対話式設定ウィザード（`config_setup.py`）
  - 起動前チェックツール（`validate_config.py`）

- 実行エンジン
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し専用 DB に記録。

- 監視
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔、`MONITOR_POLL_INTERVAL` で上書き可）
  - 監視データ永続化（SQLite）と DuckDB 連携
  - Kill Switch（`kill.flag`）による安全停止
  - RiskMonitor、TradeMonitor、SystemMonitor を束ねる MonitoringEngine

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み付け（等配分 / スコア加重）、ポジションサイズ算出、セクターキャップ、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析ユーティリティ

- AI（OpenAI）連携
  - ニュース NLP：記事をまとめて LLM に投げ、銘柄別センチメントを ai_scores に書き込む（`ai.news_nlp`）
  - レジーム判定：ETF MA + マクロニュースの LLM センチメントを合成して market_regime を算出（`ai.regime_detector`）

- ユーティリティ
  - ロギング設定ユーティリティ（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール（`tools/paper_verification_report.py`）

---

## セットアップ手順

前提: Python 3.10 以上（`X | Y` 型注釈などを利用しているため）。例では venv を使用します。

1. リポジトリをクローンして移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/コマンドプロンプト)
   ```

3. 依存パッケージをインストール  
   必要最低限（例）:
   ```
   pip install duckdb psutil openai
   ```
   追加（開発 / 一部機能）:
   ```
   pip install PyYAML
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. 環境変数の準備  
   対話式ウィザードで `.env` を生成:
   ```
   python -m kabusys.config_setup
   ```
   または `.env` ファイルを手動で作成。重要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live） - デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用の専用 DB path）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - LOG_LEVEL（DEBUG / INFO / ...）

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要スクリプト）

各モジュールはパッケージモジュールとして実行できます（`python -m kabusys.<module>`）。いくつかの例:

- ExecutionEngine を起動
  - 本番/ペーパーは `KABUSYS_ENV` で切替:
    ```
    export KABUSYS_ENV=paper_trading   # Linux/macOS
    set KABUSYS_ENV=paper_trading      # Windows (cmd)
    python -m kabusys.run_execution
    ```
  - ペーパートレード時は MockBroker を使用し、デフォルトで `data/paper_trading.db` に記録します。
  - 起動前に停止フラグ `data/stop_requested.flag` があると起動せず終了します。正常稼働中は `data/execution.pid` が作成されます。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。
  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を使用します（環境にかかわらず）。
  - 監視スクリプトも `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコア/レジームの実行（プログラム的に呼ぶ想定）
  - ニューススコア (例):
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - 注意: OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。API 呼び出しはリトライやフォールバック（失敗時はスコア 0.0 等）を備えていますが、呼び出し制限や課金に注意してください。

- ロギング
  - ログの設定は `kabusys.utils.logging_setup.setup_logging` で統一されます。
  - 環境変数 `LOG_DIR`（または引数）でログ出力先を指定できます。デフォルトは `logs/`。

---

## 重要な挙動メモ

- KABUSYS_ENV:
  - development: 開発用（発注なし）
  - paper_trading: ペーパートレード。MockBroker + 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）
  - live: 本番（実際の発注を行う）

- Kill Switch / Stop flag:
  - 実行停止のトリガーは `data/kill.flag`（KillSwitch で作成）と `data/stop_requested.flag`（停止の要求に使用）などのフラグファイルで行われます。
  - `Settings.kill_flag_clear_on_start` が `1` の場合、起動時に kill flag を自動クリアする設定になります（本番では推奨しない）。

- DB:
  - DuckDB: 分析用（デフォルト: `data/kabusys.duckdb`）
  - SQLite: 監視・トレードログ等（デフォルト: `data/monitoring.db`）
  - Paper Trading 用 SQLite は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）に分離されます

- プロセス優先度:
  - 実行スクリプトは起動直後にプロセス優先度を `high` に設定しようとします。権限不足時には警告を出してスキップされます。

---

## ディレクトリ構成（要点）

大まかなファイル/ディレクトリ構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       (参照あり)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (参照あり)
  - execution/
    - execution_engine.py    (参照あり)
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリでは `src/` の配下にさらにファイルが存在します。上記は主要モジュールの抜粋です。）

---

## 開発上の注意点 / 追加情報

- Python の型注釈（Union 演算子 `|`）を使用しているため Python 3.10 以上を推奨します。
- DuckDB / SQLite のスキーマに依存するコードが多いため、初回起動時に DB スキーマ初期化（`init_monitoring_db` など）が行われます。既存 DB のマイグレーション処理も一部実装されています。
- AI（OpenAI）関連はネットワーク・API制限・コストが関係します。テスト時はモック化して実行することを推奨します（ソース内にモック差し替え可能なポイントがあります）。
- `.env` は絶対に Git にコミットしないでください（`config_setup.py` のヘッダにも注意書きあり）。

---

この README はコードベースのエントリと基本運用手順をまとめたものです。より詳細な設計文書（PortfolioConstruction.md、StrategyModel.md 等）に基づく実装や追加設定が存在することを想定しています。運用・テスト時に不明点があれば該当モジュールの docstring を参照してください。