# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）。

この README はリポジトリ内の主要スクリプト・モジュールに基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行前に必ず `.env` を適切に設定し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークです。主な役割は以下の通りです。

- シグナル生成やポートフォリオ構築（research / portfolio）
- 注文の管理・発注（execution）
- システム・発注・リスク監視（monitoring）
- Paper Trading（検証用の模擬発注）とその評価ツール
- ニュースを用いた NLP スコアリング / レジーム判定（OpenAI を利用）
- ロギング、環境管理、運用サポート用ユーティリティ

本コードはライブラリとして各機能を提供するとともに、CLI で起動する実行スクリプト（監視ループ／実行エンジン等）を含みます。

---

## 主な機能一覧

- Execution エンジン（実注文 / ペーパートレード分離）
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を利用して paper DB に記録。
- Monitoring（監視）
  - run_monitoring.py：SystemMonitor のポーリングループ起動。データ鮮度・プロセス状態・ディスク/CPU/メモリなど監視。
  - monitoring_engine.py：複数の Monitor を束ね、Kill Switch 評価や Alert 発行を行う。
  - RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch 実装。
  - SQLite ベースの監視 DB（monitoring_db.py）を初期化・利用。
- Portfolio 構築
  - 銘柄選定、重み付け、ポジションサイジング、セクター制限、レジーム乗数などの純粋関数群（portfolio/*）。
- Research（因子計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（duckdb を用いる）。
  - forward returns / IC / 統計サマリ機能。
- AI（OpenAI 経由）
  - news_nlp.py：ニュース記事を LLM でセンチメント評価し ai_scores テーブルへ保存。
  - regime_detector.py：ETF の MA とマクロニュースの LLM スコアを合成して市場レジームを決定。
- 運用ユーティリティ
  - config_setup.py：.env の対話式ウィザード（初期設定支援）。
  - validate_config.py：環境変数 / config/*.yaml の静的検証 CLI。
  - tools/paper_verification_report.py：Paper Trading の成績・稼働率レポート生成。

---

## 必要条件 / 推奨環境

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証で必要）
- SQLite（標準ライブラリに含まれる）
- ネットワーク接続（OpenAI API を使う場合）

依存関係はプロジェクトに requirements.txt があればそれを利用してください。無ければ仮想環境作成後に上記パッケージをインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. 環境変数設定
   - 推奨: `python -m kabusys.config_setup` を実行して対話式に `.env` を生成／更新する。
   - あるいは `.env.example` を元に `.env` を作成し必要な値を設定する。
4. 設定検証:
   - `python -m kabusys.validate_config`
   - 必要に応じて `--strict` を付けると警告も失敗（exit(1)）扱いに。
5. DB 初期化:
   - monitoring 用の SQLite（デフォルト `data/monitoring.db`）は起動スクリプト内で `init_monitoring_db()` により自動作成・マイグレーションされます。
   - Paper Trading の SQLite（`data/paper_trading.db`）は paper 環境で Execution を起動した際に使用されます。

---

## 環境変数（主なもの）

自動ロードの優先順: OS 環境 > .env.local > .env（プロジェクトルートが検出できる場合にのみ自動ロードされます）。

主なキー（Settings クラスより）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意、アラート通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
- PAPER_FILL_MODE (デフォルト: instant) — instant | partial | never | reject
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR（ログ保存先、デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch / PID 管理関連）
- OPENAI_API_KEY（AI 機能使用時に必要）

詳しい説明は `kabusys.config.Settings` と `config_setup.py` の _ITEMS を参照してください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（本番または paper_trading は KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - 起動時に `Settings` を読み込み、SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用し、MockBrokerClient を使います。
  - 起動時に `stop_requested.flag` が存在する場合は起動せず終了します。
  - 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine 内の kill flag を書く（KillSwitch 参照）ことで行います。
  - PID ファイル: `data/execution.pid`（設定により変更可）

- Monitoring を起動（監視ループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  挙動:
  - SystemMonitor を定期実行（デフォルト 60 秒ごと）。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可。
  - 監視は本番 sqlite_path を使い、DuckDB も接続します。
  - ループ停止は `data/stop_requested.flag` を作成することで検出され安全終了します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラム的に呼び出す）
  - ニュース NLP スコアリング（DuckDB 接続が必要）
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date は datetime.date
    score_count = score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

- ライブラリ関数（portfolio / research）
  - ポートフォリオ作成関数群は pure function（DB 参照なしのものが多い）として利用可能:
    ```python
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```

---

## 運用・停止方法（重要）

- Graceful stop（監視/実行ループ共通）
  - `data/stop_requested.flag` を作成すると `run_execution.py` / `run_monitoring.py` が検知して安全に停止します。
- Kill Switch（リスクにより ExecutionEngine を外部から停止）
  - `KillSwitch` は監視ロジックに基づき `data/kill.flag` を書き込みます。ExecutionEngine は起動時や定期チェックでこのフラグを検出し、停止します。
  - 設定 `KILL_FLAG_CLEAR_ON_START=1` に注意（本番では 0 を推奨）。
- PID ファイル
  - ExecutionEngine は起動時に PID ファイル（デフォルト `data/execution.pid`）を扱います。プロセス管理や stale PID 検出に利用されます。

---

## 監視 DB（SQLite）について

- 監視用 DB は `kabusys.monitoring.monitoring_db.init_monitoring_db` によってテーブル作成・マイグレーションされます。
- 主要テーブル:
  - system_status（CPU/Memory/Disk/プロセス正常性）
  - trade_logs（発注 / 約定ログ。latency_ms カラムあり）
  - positions（保有）
  - risk_logs（リスクイベント）
  - dashboard（ダッシュボード集計、id=1 の単一行）
- run_monitoring / run_execution は適宜この DB を使用・更新します。

---

## ディレクトリ構成

以下は主要なファイル・モジュール一覧（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - config_setup.py                  — .env 対話ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading レポート
  - ai/
    - news_nlp.py                    — ニュースを LLM でスコアリング
    - regime_detector.py             — 市場レジーム判定
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py                — アラート管理（実装あり）
  - execution/                       — 注文実行関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py                — ロギング初期化
    - process_priority.py             — プロセス優先度設定ユーティリティ
  - data/ （実行時に生成される想定）
    - *.db, *.flag, execution.pid, etc.

（実際のリポジトリのファイル・フォルダツリーを参照してください。）

---

## 開発者向けメモ / 注意事項

- Python の型ヒントで `|` を使っているため Python 3.10+ が必要です。
- DuckDB を利用した分析/リサーチ関数は duckdb の接続オブジェクトを受け取り SQL を組み合わせて処理します。
- OpenAI API を使うモジュールは API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数引数で明示的に渡してください。API 呼び出しはリトライ・フォールバック実装を含みますが、キーが未設定だと例外になります。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` を通じて統一されています。ログディレクトリの書き込み権限に注意してください。
- Paper Trading と本番は DB を分離しており、誤って本番 DB を操作しないように環境変数を管理してください。
- Kill Switch / stop flag による停止動作については本番運用前に十分検証してください（特に `KILL_FLAG_CLEAR_ON_START`）。

---

README の内容はコードベースの現状（主要スクリプト・モジュール）に基づいています。追加で README に載せたい操作例、設定ファイルテンプレート、または運用手順（systemd / Docker / cron の設定例など）があれば教えてください。必要に応じて具体的な導入手順・systemd ユニットファイル・Dockerfile なども作成します。