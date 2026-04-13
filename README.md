# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株を対象とした自動売買／リサーチ／監視コンポーネント群を含む Python パッケージです。  
以下はプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成されます。

- ExecutionEngine：発注・リスク管理・オーダー状態管理・ブローカー連携
- Monitoring：システム稼働性・注文滞留・約定異常・リスク（ドローダウン等）監視、LINE 通知、kill flag による Execution 停止
- Portfolio construction：銘柄選定・重み算出・リスク調整・ポジションサイズ決定
- Research：ファクター算出、将来リターン計算、IC 計算などの調査用機能（DuckDB を利用）
- AI モジュール：ニュース NLP による銘柄センチメント評価、レジーム判定（OpenAI API を利用）
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

設計方針のポイント：
- DuckDB / SQLite をデータ層に使用（価格・財務・ニュースは DuckDB、監視ログは SQLite）
- 本番・ペーパートレードの DB を明確に分離できる設定
- 外部 API（OpenAI / ブローカー）は抽象化され、フェイルセーフやリトライを備える

---

## 主な機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス存在 / データ鮮度）
- 注文監視（滞留注文・約定価格異常検出）
- リスク監視（ドローダウン監視、ポジション上限監視、リスクログ保存）
- Kill Switch（条件で data/kill.flag を書き込み ExecutionEngine 停止）
- LINE push によるアラート送信（cooldown 管理）
- Streamlit ベースの監視ダッシュボード（read-only）
- Portfolio 構築ユーティリティ（候補選定、重み付け、単位株丸め、セクター制限）
- Research ツール（モメンタム・ボラティリティ・バリュー算出、IC・統計サマリー）
- AI 系：ニュースを LLM でスコアリングして ai_scores に書き込む機能、レジーム判定（MA + マクロセンチメント）
- Paper Trading 検証レポート生成ツール

---

## 必要依存ライブラリ（例）

主に以下が必要です（実際のプロジェクトでは requirements.txt 等を用意してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit
- sqlite3（標準ライブラリ）
- その他（環境に応じて）

仮想環境作成とインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 設定（環境変数 / .env）

設定は基本的に環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込みます。自動読み込みは以下優先順位です：

1. OS 環境変数
2. .env.local（`.env` より優先して上書き）
3. .env（未設定キーのみセット）

自動読み込みを無効化するには：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）:

- KABUSYS_ENV: 起動環境。値: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、Execution は paper DB（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須: 使用箇所がある場合）
- KABU_API_PASSWORD: kabu API 用パスワード（必須: 本番ブローカー連携時）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。整数 >= 1。無効値はデフォルト 60 秒にフォールバック。

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-xxxx
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（開発向け簡易）

1. リポジトリをクローン
2. 仮想環境を作成してアクティベート
3. 必要パッケージをインストール（上記参照）
4. .env を作成（必要なキーを設定）
5. データディレクトリを作成：
   ```bash
   mkdir -p data
   ```
6. DuckDB / SQLite の初期化はスクリプト起動時に自動で行われます（init_monitoring_db が DB 作成・マイグレーションを担う）

---

## 実行方法（使い方）

- ExecutionEngine（実際の発注ループを起動）
  - ペーパートレードの場合は KABUSYS_ENV=paper_trading を設定するとブローカーはモックを使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 起動時にプロセス優先度を "high" に設定します（権限がない場合は警告を出してスキップ）。

- Monitoring（監視ループを起動）
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path（SQLITE_PATH）を使用する点に注意してください。

- Streamlit ダッシュボード（監視ビュー）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB が存在しない（MonitoringEngine が起動していない）場合、読み取り専用で開けない旨のエラーを表示します。

- Paper Trading 検証レポート生成ツール
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB: data/paper_trading.db（`--db` オプションか環境変数 PAPER_TRADING_SQLITE_PATH で指定可能）

- AI スコアリング / レジーム判定
  - OpenAI API キー（OPENAI_API_KEY）が必要です。関数はモジュールから直接呼び出します（例: kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime）。
  - LLM 呼び出しはリトライやフォールバック（API 失敗時に 0.0 を使う等）を備えています。

---

## 運用上の注意・挙動

- Monitoring は monitoring DB（SQLITE_PATH）に書き込みます。run_monitoring は常に設定された sqlite_path を使います（KABUSYS_ENV に関係なく本番 sqlite_path を参照する仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します。これによりペーパートレードは本番 DB と完全に分離されます。
- MONITOR_POLL_INTERVAL が 0 以下や数値以外の場合はデフォルト 60 秒にフォールバックします（警告ログあり）。
- pid file（PID_FILE_PATH）によるプロセス存在チェックを行い、stale PID を検出すると削除してリスクログに記録します。
- kill.flag の書き込みは一度書くと既存ファイルがある場合は再書き込みしません（冪等性）。Execution 側はこのファイルの有無で停止します。
- OpenAI 呼び出しは上限やネットワークエラーに対して指数バックオフでリトライします。レスポンスのバリデーションにも注意していますが、LLM の不定形出力に対する保護も組み込まれています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュール構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env ロードと Settings クラス
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - risk_adjustment.py         — セクター制限・レジーム乗数
    - position_sizing.py         — 株数決定・単元丸め
    - __init__.py
  - research/
    - factor_research.py         — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py     — 将来リターン・IC・summaries
    - __init__.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI）による銘柄スコア
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py           — monitoring 用 SQLite 層（テーブル作成・永続化 API）
    - system_monitor.py          — システム監視（CPU/メモリ/データ鮮度等）
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みユーティリティ
    - alert_manager.py           — LINE Push 通知
    - monitoring_engine.py       — 各 Monitor を束ねるループ
    - streamlit_dashboard.py     — Streamlit ダッシュボード
    - __init__.py
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - execution/                   — （発注関連、OrderManager, Reconciler など ※一部のみ抜粋）
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - risk_manager.py
  - data/                        — データパイプライン、DuckDB テーブル操作（prices_daily 等）

---

## よくある運用コマンド・例

- 監視を常駐で起動（システムデーモン / screen / systemd などで起動）:
  ```bash
  export KABUSYS_ENV=production
  python -m kabusys.run_monitoring
  ```

- Execution を起動（ペーパートレード）:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Paper Trading レポート（過去期間）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード起動:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

## 開発・拡張メモ

- DuckDB のスキーマ（prices_daily / raw_financials / raw_news / ai_scores など）をプロジェクトで共有することで、Research / AI モジュールは DB だけを参照して動作します。
- OpenAI を使う機能は API キーの設定に依存します。テスト時は API 呼び出し関数をモックする設計になっています（モジュール内の _call_openai_api をパッチ可能）。
- MonitoringDB（monitoring_db.py）は後方互換性のため簡易マイグレーション処理を含みます（カラム追加等）。

---

## 問題・トラブルシューティング

- DB が開けない（Streamlit など）: MonitoringEngine を起動して monitoring DB が作成されているか確認してください。
- MONITOR_POLL_INTERVAL が反映されない: 値が整数か 1 以上であることを確認してください。不正値は 60 秒にフォールバックします。
- OpenAI 呼び出し失敗: OPENAI_API_KEY の設定とネットワークアクセス、またはレートリミットの状態を確認してください。モジュールはリトライ・フォールバックを行いますが、完全停止の原因になる場合があります。

---

必要に応じて README を追補します。追加で記載してほしい項目（API 定義、DB スキーマ詳細、運用用 systemd サービス定義例など）があれば教えてください。