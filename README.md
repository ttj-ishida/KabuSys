# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ + 起動スクリプト群）。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング等の主要コンポーネントが含まれます。

## 概要
KabuSys は以下の目的を持つコンポーネント群から構成されます。

- ExecutionEngine: 発注処理・注文管理・リスク管理を行う実行エンジン（paper_trading と live の分離対応）
- Monitoring: システム稼働・注文・リスクを監視し、必要に応じて Kill Switch を発動するコンポーネント
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算などのポートフォリオ構築ロジック
- Research: DuckDB を用いたファクター計算・特徴量探索ユーティリティ
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・レジーム判定
- CLI ユーティリティ: .env ウィザード (`config_setup`)、設定検証 (`validate_config`)、Paper Trading レポート生成ツール など

## 主な機能一覧
- 起動スクリプト:
  - `python -m kabusys.run_execution` — ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - `python -m kabusys.run_monitoring` — SystemMonitor ポーリングループを起動
- 設定管理:
  - `.env` 自動ロード（プロジェクトルートの `.env` / `.env.local`）
  - 対話式ウィザードで `.env` を作成・更新 (`python -m kabusys.config_setup`)
  - 起動前チェック (`python -m kabusys.validate_config`)
- Paper Trading 検証レポート:
  - `python -m kabusys.tools.paper_verification_report` — ペーパートレード DB から各種指標を集計してレポート出力
- ポートフォリオ構築:
  - 銘柄選定、スコア重み付け、等分配、リスクベースの株数算出、セクター上限適用等
- AI / リサーチ:
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility 等）
  - OpenAI を用いたニュースセンチメントスコアリング（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- 監視:
  - システム資源・プロセス死活・データ鮮度チェック、注文滞留・約定異常監視、ドローダウン監視
  - Kill Switch（`data/kill.flag`）の生成と ExecutionEngine 停止

## 動作環境 / 前提
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - （任意）PyYAML（config 検証時に YAML ファイルを検証する場合）
- SQLite（組み込み）およびファイル I/O にアクセス可能な環境
- ネットワーク接続（kabu API / OpenAI を利用する場合）

必要なパッケージはプロジェクトに requirements ファイルがない場合、手動でインストールしてください。例:
```bash
python -m pip install duckdb psutil openai
```

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作る:
   ```bash
   git clone <repo_url>
   cd <repo_root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai
   ```

2. .env を生成または編集:
   - 対話式ウィザードを実行して初期 `.env` を作成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他の重要な環境変数:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 時）
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能を使う場合）

3. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

4. 必要に応じて data ディレクトリや logs ディレクトリを準備（自動作成されますが権限に注意）:
   ```bash
   mkdir -p data logs
   ```

## 使い方

- ExecutionEngine 起動:
  - paper_trading モード（環境を切り替えて実行）:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。実プロダクション DB と分離されます。

  - live モード:
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```

  - 起動時に ExecutionEngine は `data/execution.pid`（デフォルト）などの PID ファイルを作成します。停止は Kill Switch（`data/kill.flag`）または監視側からの停止指示・フラグファイルで制御できます。

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60 秒）。
  - 監視は本番 sqlite_path（`SQLITE_PATH`）を常に参照します（環境に依らず本番 DB を監視する意図）。

- 停止・強制停止の仕組み:
  - run_execution/run_monitoring はプロジェクトの `data/stop_requested.flag` を監視し、存在するとループを終了します。
  - Kill Switch（監視コンポーネント）はリスクトリガー発生時に `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - Kill flag を手動でクリアするには:
    ```bash
    rm -f data/kill.flag
    ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は env または data/paper_trading.db
  ```

- ログ:
  - デフォルトは `logs/<app_name>.log`（例: logs/execution.log, logs/monitoring.log）に日次ローテートで保存されます。`LOG_DIR` で変更可能。
  - `LOG_LEVEL` で出力レベルを制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

## プログラム的に利用する（ライブラリ API 例）

- AI ニューススコアリング（DuckDB 接続を渡す）:
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

- ポートフォリオ関数の利用例:
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  # buy_signals = [...]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_equal_weights(candidates)
  shares = calc_position_sizes(weights, candidates, portfolio_value=10000000, available_cash=2000000, current_positions={}, open_prices={...})
  ```

## 主な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要/設定例:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (INFO)
- LOG_DIR
- OPENAI_API_KEY（AI を使う場合）
- PAPER_FILL_MODE (instant | partial | never | reject)
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒）

詳しくは `src/kabusys/config.py` を参照してください。

## ディレクトリ構成（主要ファイル）
以下はソースツリーの簡易概要（`src/kabusys` 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定解決ロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（init / CRUD）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文ログ監視（滞留・異常検出）※実装参照
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor の統合ループ
    - alert_manager.py — アラート送信管理（LINE など）※実装参照
  - execution/ — ExecutionEngine 関連（エンジン・リスク管理・オーダー管理等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・キャップ調整
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility 等の計算
    - feature_exploration.py — 将来リターン・IC 等の評価
  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - data/ — 実行時生成されることが想定されるディレクトリ（DB / pid / flag 等）
  - logs/ — ログファイル出力先（デフォルト）

（実際の詳細はソース内ドキュメントを参照してください）

## 運用上の注意
- 本番環境（KABUSYS_ENV=live）では .env の内容・LINE 通知設定・Kill Switch 設定を慎重に確認してください。validate_config の警告をよく確認してください。
- OpenAI API キーを扱う際は `.env` をバージョン管理に含めないでください（README 内の注意にも記載）。`.env` は Git にコミットしないこと。
- Paper Trading は本番 DB と完全分離するよう設計されています（`PAPER_TRADING_SQLITE_PATH` を使用）。

## 開発 / 貢献
- 追加の依存パッケージを導入する際は、ドキュメントに記載し README を更新してください。
- テスト、CI、コードフォーマット等は別途整備を推奨します。

---

README は簡潔にしていますが、各モジュールはソース中に詳細な docstring が含まれているため、必要に応じて `src/kabusys/*` の該当ファイルを参照してください。質問や補足があれば知らせてください。