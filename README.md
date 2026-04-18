# KabuSys

日本株自動売買システムのコアライブラリ群（モニタリング、ExecutionEngine、ポートフォリオ構築、リサーチ、AI補助モジュール等）。

この README はリポジトリ内の主要スクリプト・ユーティリティを利用するための概要、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine: 注文発行・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード切替対応）。
- Monitoring: システム状態・データ鮮度・注文状態・リスク監視と、必要に応じた Kill Switch 発動（フラグファイル書き込み）。
- Portfolio: 銘柄選定・重み算出・ポジションサイズ計算・セクターキャップなどのポートフォリオ構築ロジック（純粋関数群）。
- Research: DuckDB 上の時系列データを用いたファクター計算・特徴量解析ユーティリティ。
- AI: ニュース NLP によるセンチメント算出・市場レジーム判定（OpenAI API を利用、オプション）。
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- Utils: ロギング設定、プロセス優先度制御、設定読み込み等の共通ユーティリティ。

設計上の特徴:
- 本番用 / ペーパートレード用 DB を分離（`KABUSYS_ENV=paper_trading` の場合は専用 SQLite を使用）。
- .env を使った環境変数管理と対話式ウィザード、起動前設定検証 CLI を提供。
- DuckDB を分析用ローカル DB、SQLite を監視・トレードログの永続化に使用。

---

## 主な機能一覧

- 設定管理 (.env 自動読み込み / config ウィザード)
- 設定検証 CLI (`kabusys.validate_config`)
- ExecutionEngine 起動（本番 / paper_trading 切替）
- Monitoring のポーリングループ実行（System / Trade / Risk の監視）
- Kill Switch：条件に基づく停止フラグ (data/kill.flag) の書き込み
- ポートフォリオ構築関数群（候補選定、重み付け、ポジションサイズ決定）
- DuckDB ベースのファクター計算（モメンタム / ボラティリティ / バリュー）
- OpenAI を用いたニュースセンチメント評価 / レジーム検出（任意）
- ペーパートレード検証レポート生成ツール

---

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows (PowerShell)
     ```

2. 依存パッケージのインストール
   - 必須（代表的なもの）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（`validate_config` が YAML 検証を行う場合に推奨）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - （プロジェクトが requirements ファイルを持つ場合はそちらを利用してください）

3. プロジェクトルートの .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に `.env` を手動作成してください。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. DB ファイルやログディレクトリのパーミッションを確認
   - デフォルトパス:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`
     - ログディレクトリ: `logs/`（`LOG_DIR` で上書き可）

注: OpenAI を使う機能（ニュース NLP / レジーム検出）は `OPENAI_API_KEY` を `.env` に設定するか、関数呼び出し時に API キーを渡してください。

---

## 使い方

以下は主要スクリプトの実行例と動作方針です。

- ExecutionEngine を起動
  - 本番 / 開発環境は `KABUSYS_ENV` で切替（`development` / `paper_trading` / `live`）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - `KABUSYS_ENV=paper_trading` の場合:
    - MockBrokerClient を使い、`data/paper_trading.db` に記録します（本番 DB とは分離）。
  - 起動時、`data/stop_requested.flag` が存在すると起動を拒否します。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンが停止します。
  - PID ファイル: `data/execution.pid`（設定で変更可）

- Monitoring を起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト: 60）。
  - Monitoring は環境にかかわらず本番の `sqlite_path` を使用して監視ログを永続化します。
  - `data/stop_requested.flag` の検出でループを終了します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（ニュース NLP / レジーム判定）
  - 直接 Python から呼び出す:
    ```py
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続（duckdb.connect）を渡して使用
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_API_KEY")
    ```
  - OpenAI API キーが `.env` の `OPENAI_API_KEY` に設定されていれば、`api_key` を省略可能。

---

## 主要環境変数（代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — INFO 等（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — ペーパートレードの注文約定動作 ("instant" | "partial" | "never" | "reject")
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env をロードしない場合に 1 を設定

※ `.env` の自動読み込みはプロジェクトルートが特定できる場合にのみ行われます（`.git` または `pyproject.toml` をルート判定）。

---

## ディレクトリ構成（抜粋）

（root）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度・CPU affinity
    - execution/                — 実行エンジン関連（broker, engine, order_manager 等）
    - monitoring/
      - monitoring_db.py       — SQLite テーブル初期化 / 永続化ラッパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/                — 銘柄選定・配分・リスク調整・サイズ決定
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/                 — ファクター計算 / 特徴量探索
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — ニュースセンチメント（OpenAI）
      - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
    - tools/
      - paper_verification_report.py
    - data/                    — 実行時に使用する DB/フラグ/ログ等（デフォルト）
- logs/                        — ログ出力（デフォルト）

（注）上記は主要ファイルのみ抜粋しています。詳細なモジュールは `src/kabusys` 以下をご参照ください。

---

## 運用上のポイント / トラブルシューティング

- ログ
  - デフォルトで stdout（console）と日次ローテートされたファイルに出力されます（`logs/<app_name>.log`）。
  - ログディレクトリに書き込み権限がない場合はコンソール出力のみになります。

- プロセス優先度設定
  - `psutil` を用いて優先度を設定します。権限不足の場合は警告が出てスキップされます。

- Kill Switch / Stop フラグ
  - `data/kill.flag` は Kill Switch の発動トリガー（ExecutionEngine 停止要求に使用）。
  - `data/stop_requested.flag` は run_* スクリプトを優雅に終了させるための外部停止フラグ（存在を検出するとループを抜ける）。

- DB マイグレーション
  - `monitoring_db.init_monitoring_db` は冪等的にテーブル・インデックスを作成します。既存の DB に列が欠けている場合は簡易マイグレーション（ALTER TABLE ADD COLUMN）を行います。

- OpenAI API 呼び出し
  - レート制限・ネットワークエラー・5xx は指数バックオフでリトライしますが、完全に失敗した場合はフェイルセーフとして中立値（0.0 等）で継続します。
  - API キーは必ず `.env` または引数で設定してください。

- .env の自動読み込み
  - OS 環境変数が優先されます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発 / テスト向けメモ

- モジュールは可能な限り副作用を排除しており、単体関数（ポートフォリオ計算等）は純粋関数として実装されています。ユニットテストが書きやすい設計です。
- MonitoringEngine や各 Monitor には `run_once()` / `check_once()` のようなテスト用 API が用意されています。ユニットテストではこれらを直接呼び出して検証できます。
- OpenAI 呼び出しはラッパー関数を通しており、ユニットテストでは `unittest.mock.patch` で差し替えてテスト可能です。

---

必要に応じて、README をプロジェクト固有の運用手順（デプロイ方法、systemd ユニット例、バックアップ方針など）で拡張してください。質問や README に追加してほしい具体的な項目があれば教えてください。