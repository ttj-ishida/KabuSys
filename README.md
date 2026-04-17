# KabuSys

日本株向けの自動売買システムのコアライブラリ群（リファレンス実装）。

このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などを含むモジュール群を提供します。実行環境（開発 / ペーパートレード / 本番）に応じて振る舞いが切り替わります。

---

## プロジェクト概要

- モジュール化された自動売買基盤の実装例。
- SQLite（監視・発注ログ）および DuckDB（時系列 / ファクター計算）をデータ格納に使用。
- 実行環境:
  - `development` : 開発・テスト（発注なし）
  - `paper_trading` : ペーパートレード（Mock ブローカーを利用、発注は data/paper_trading.db に記録）
  - `live` : 本番（実際に発注）
- モジュール群は互いに疎結合化され、AI（OpenAI）や LINE 通知と連携可能。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - ブローカーファクトリ、オーダー管理、リスク管理、リコンサイル
  - ペーパートレードモード（実DBと分離、専用 SQLite を使用）

- Monitoring
  - System / Trade / Risk モニタ（`monitoring/*`）
  - 監視ログ永続化（SQLite via `monitoring_db.py`）
  - Kill Switch（条件に応じて `data/kill.flag` を書き込み、ExecutionEngine を停止）
  - LINE 通知用 AlertManager

- Portfolio
  - 候補選定、重み計算、リスク調整、ポジションサイズ算出（等金額／スコア加重／リスクベース等）

- Research / AI
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算（feature_exploration）
  - ニュース NLP による銘柄別センチメント算出（OpenAI 経由・`ai/news_nlp.py`）
  - マクロ＋ETF MA による市場レジーム判定（`ai/regime_detector.py`）

- ツール
  - .env 対話ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）

---

## 必要条件（依存ライブラリ）

推奨 Python バージョン: 3.10+

主要依存（抜粋）:
- duckdb
- psutil
- requests
- openai
- PyYAML（config 検証時に YAML 検査を行う場合に必要）

pip インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai pyyaml
```

（プロジェクトに requirements ファイルがある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 & 依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install duckdb psutil requests openai pyyaml
   ```

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   これによりプロジェクトルートの `.env` が生成されます。.env は絶対に VCS にコミットしないでください。

   自動ロード:
   - デフォルトで `.env` / `.env.local` は自動ロードされます（`kabusys.config`）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いで失敗させる場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ
   - デフォルトの DB 等は `data/` 配下に保存されます（例: `data/monitoring.db`, `data/kabusys.duckdb`）。
   - 必要に応じて `.env` で `SQLITE_PATH`, `DUCKDB_PATH`, `PAPER_TRADING_SQLITE_PATH` を指定してください。

---

## 実行方法（主要コマンド）

- ExecutionEngine（トレード実行エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使われ、発注ログは `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）に保存されます。
  - 起動前に `data/stop_requested.flag` が存在する場合は起動しません。
  - 停止するには `data/stop_requested.flag` を作成してください（スクリプトは定期的に存在をチェックして安全に停止します）。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト: 60）。
  - Monitoring は常に本番用の sqlite_path を使用して監視ログを記録します（環境に関わらず）。
  - 終了は `data/stop_requested.flag` の作成または Ctrl+C。

- .env 対話ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - デフォルト DB: `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`

- AI モジュール（ニュースセンチメント / レジーム判定）
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` を呼び出す。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` を呼び出す。
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
  - エラー時はフェイルセーフ（デフォルト値で継続）する設計です。

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live)

- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)

- ロギング:
  - LOG_LEVEL (DEBUG | INFO | WARNING | ...)

- LINE 通知:
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- AI:
  - OPENAI_API_KEY

- 監視/制御:
  - KILL_FLAG_PATH (デフォルト: data/kill.flag) — Kill Switch が書き込むフラグ
  - KILL_FLAG_CLEAR_ON_START (0|1) — ExecutionEngine 起動時に kill.flag を自動除去するか
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

---

## 停止・Kill スイッチについて

- ExecutionEngine の安全停止:
  - `KillSwitch` は RiskMonitor 等の結果に基づき `data/kill.flag` を作成し、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は kill.flag を参照し停止処理を行う設計を想定）。
  - `KillSwitch.clear()` で kill.flag を削除できます（起動時に自動クリアを許可する場合は `KILL_FLAG_CLEAR_ON_START=1`）。
- 全プロセス停止用フラグ:
  - `data/stop_requested.flag` を作成すると、`run_monitoring` / `run_execution` のループが検知して終了します（起動スクリプトで参照）。

---

## ディレクトリ構成（主要ファイル・概要）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数／自動 .env ロード、Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores へ書き込む
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite の監視用テーブル定義と MonitoringDB ラッパ
    - system_monitor.py — CPU / メモリ / データ鮮度 / Execution PID チェック
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限チェック（Kill 判定に寄与）
    - kill_switch.py — 条件に応じて kill.flag を書き込む
    - monitoring_engine.py — 各モニタを束ねてポーリング実行
    - alert_manager.py — LINE へのプッシュ通知（クールダウン管理等）

  - execution/ (発注関連; 実装本体は一部省略されている想定)
    - order_manager.py, order_repository.py, execution_engine.py, risk_manager.py, reconciler.py, broker_factory.py, ...

  - portfolio/
    - portfolio_builder.py — 候補選定・ウェイト計算
    - position_sizing.py — 発注株数計算（単元丸め・スケーリング）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ （実行時に使用されるローカルストレージ）
  - monitoring.db（デフォルト）
  - kabusys.duckdb（デフォルト）
  - paper_trading.db（ペーパートレード用）
  - execution.pid / kill.flag / stop_requested.flag など

---

## 追加の設計ノート（運用向け）

- Monitoring は本番の monitoring DB（`SQLITE_PATH`）を常に使用する設計です（環境に関係なく）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合 DB を分離します（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）呼び出しでは 429 / ネットワーク / サーバーエラーに対して指数バックオフでリトライします。API キーの管理は慎重に。
- process priority 設定には psutil の権限が必要な場合があります。権限不足時は警告を出してスキップします。
- .env 自動ロードはプロジェクトルート検出（.git または pyproject.toml）に依存します。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用してください。

---

必要であれば、README に実際の .env のテンプレートや systemd ユニットファイルの例、運用チェックリスト（起動手順、バックアップ、監視）を追記できます。ご希望があればその内容に合わせて追加します。