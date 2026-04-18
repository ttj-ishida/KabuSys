# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）のリポジトリです。  
この README はコードベース（src/kabusys 以下）を元にまとめたものです。

> 対象: run_execution / run_monitoring / config 関連 CLI / portfolio / research / ai / monitoring / tools 等の主要コンポーネント

---

## プロジェクト概要

KabuSys は、日本株の自動売買エンジンとそれを支える監視・リサーチ・ポートフォリオ構築・AI 補助モジュールを含むコード群です。  
主な設計方針：

- 本番／ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え（`development` / `paper_trading` / `live`）。
- DuckDB を分析・リサーチ用に利用、SQLite を監視・注文履歴保存に利用。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（センチメント）やレジーム判定をサポート（API キー必須）。
- 監視（Monitoring）コンポーネントはシステム状態・注文滞留・リスクをチェックし、必要に応じて Kill Switch を発動して実行エンジンを停止する。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト
  - python -m kabusys.run_execution（`KABUSYS_ENV=paper_trading` 時は MockBroker を使用して `data/paper_trading.db` に分離）
  - プロセス優先度を上げて実行（psutil 利用）
- Monitoring（監視）
  - python -m kabusys.run_monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン、ポジション上限の監視とリスクログ記録
  - KillSwitch：危険条件で `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送る
  - MonitoringEngine：各 Monitor をまとめてポーリングし通知/kill を管理
- AI モジュール
  - kabusys.ai.news_nlp：ニュースを集約して OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ保存
  - kabusys.ai.regime_detector：ETF (1321) の MA200 乖離 + マクロニュースセンチメントで市場レジーム（bull/neutral/bear）を判定して保存
- Research / ファクター計算
  - factor_research.py：モメンタム / バリュー / ボラティリティ等のファクターを DuckDB の prices_daily/raw_financials から計算
  - feature_exploration.py：将来リターン、IC 計算、統計サマリーなど
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、セクター制約、ポジションサイズ計算（単元株丸め等）
- CLI ツール
  - config_setup.py：.env 対話式ウィザード（.env の初期作成/更新）
  - validate_config.py：環境変数・config/*.yaml の事前検証
  - tools.paper_verification_report：Paper Trading 用の検証レポート生成

---

## 前提・依存

最低限の想定環境：

- Python 3.10 以上（型表記に `|` を使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証を行う場合に推奨）
- SQLite（標準ライブラリ）
- 実行ユーザーがファイル作成・プロセス操作できること（pid ファイル操作など）

インストール例（venv を作ってから）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

必要に応じてパッケージを pyproject.toml / requirements.txt に追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてソースルートへ移動
2. 仮想環境作成・依存パッケージインストール（上記参照）
3. 環境変数設定（.env 作成推奨）
   - 対話式で作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - または `.env.example` を参考に `.env` を作成してルートに置く（このコードベースは自動で .env をロードします。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化可能）。
4. 設定検証（必須環境変数や config ファイル構成をチェック）:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合は --strict
   python -m kabusys.validate_config --strict
   ```
5. DB 初期化
   - 監視用 SQLite は `init_monitoring_db()` によりテーブルは自動作成されます。run_monitoring / run_execution 起動時に自動で作成されます。
6. 実行準備完了

---

## 主要な環境変数（要設定項目）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV：実行環境（`development` | `paper_trading` | `live`、デフォルト `development`）
- OPENAI_API_KEY：OpenAI を使う場合（news_nlp / regime_detector）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（`instant` | `partial` | `never` | `reject`, デフォルト `instant`）
- LOG_LEVEL（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`、デフォルト `INFO`）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知）

その他:
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- PID_FILE_PATH（実行エンジンの PID ファイルパス、デフォルト: data/execution.pid）

注意:
- Monitoring はコード中の仕様により KABUSYS_ENV にかかわらず `sqlite_path`（監視 DB）を使用します。一方、`run_execution` は `KABUSYS_ENV=paper_trading` の時に `paper_sqlite_path` を使用して本番 DB と分離します。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン（発注エンジン）起動
  - 本番またはペーパートレードは KABUSYS_ENV に依存します
  ```bash
  # 例: paper_trading モードで起動する場合
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします
  - 実行中は `data/execution.pid` が作成されます

- Monitoring（監視ループ）起動
  ```bash
  # デフォルトポーリング間隔 60 秒。環境変数で上書き:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - `stop_requested.flag` が存在すると監視ループを終了します
  - 監視モジュールは system_status / trade_logs / risk_logs / dashboard などのテーブルを作成・更新します

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼ぶ）
  - ニューススコア付与:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも `api_key` を明示的に渡すか `OPENAI_API_KEY` を環境変数に設定してください。

---

## ファイル / ディレクトリ構成（主要部分）

以下は src/kabusys 以下の主要ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（OrderManager 等）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 監視 DB 層（テーブル作成 / read/write）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に使用するデータ・DB を置く想定)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
  - tools/
    - __init__.py
    - paper_verification_report.py

（実際のリポジトリにはさらに execution や data pipeline、order_repository など多くのモジュールが存在します。上は主要なファイルのサマリです。）

---

## 運用上の注意 / 補足

- PID / フラグファイル:
  - デフォルト PID ファイル: data/execution.pid
  - 停止フラグ: data/stop_requested.flag（スクリプトはこのファイルの存在を検出して終了）
  - Kill Switch が発動すると data/kill.flag が書き込まれ、ExecutionEngine の停止を促します
- DB 分離:
  - `KABUSYS_ENV=paper_trading` の場合、Execution は `paper_sqlite_path`（デフォルト data/paper_trading.db）を使用して本番データと完全分離します
  - 監視 DB（monitoring）は常に `SQLITE_PATH` を使用します（環境に依らず）
- OpenAI API:
  - API 呼び出しはリトライ/バックオフ等の対策あり。ただし API キーの管理、レート制限、コストに注意してください
- ログレベル:
  - Settings.log_level で `LOG_LEVEL` を指定できます
- テスト・デバッグ:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動 .env ロードを抑制できます（単体テストで便利）
- Python バージョン:
  - 型表記（`X | Y`）が入っているため Python 3.10 以上を推奨します

---

## よく使うコマンド（まとめ）

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- 実行エンジン起動:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```

- Paper トレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をプロジェクトの実際の README.md として調整します（パッケージインストール手順の追加、より詳細な .env.example のサンプル、実行例ログ、デプロイ手順など）。どのレベルまでドキュメント化したいか教えてください。