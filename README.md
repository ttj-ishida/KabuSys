# KabuSys

日本株自動売買システムのサブセット実装です。ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュース NLP / レジーム判定）などの機能群を含みます。本リポジトリはモジュール単位で実行可能なスクリプト群とライブラリ群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを持ちます。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状態・注文状態・リスク（ドローダウン等）を定期監視してログ・アラート・Kill Switch を提供
- Portfolio コンポーネント: 候補選択、重み計算、ポジションサイズ計算、セクター制約など
- Research: ファクター計算・特徴量探索（DuckDB を使用）
- AI モジュール: ニュースを LLM（OpenAI）で評価してスコア化、レジーム判定
- ユーティリティ: ログセットアップ、プロセス優先度設定、環境設定ウィザード、設定検証、検証レポートなど

設計方針の一部:
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアスを避けるため、日付/時刻参照は明示的引数で行うことを推奨
- 外部 API（OpenAI など）呼び出しはフェイルセーフ設計（失敗時はフォールバック）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper_trading 用クライアントを選択）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- portfolio: 候補選択 / 重み算出 / ポジションサイズ算出 / セクター制約
- research: ファクター計算（momentum, value, volatility）、IC 計算、統計要約
- ai: ニュース NLP スコアリング（OpenAI）、レジーム判定
- monitoring: DB 永続化（SQLite）、System/Trade/Risk モニタ、Kill Switch、AlertManager（実装に応じて通知）

---

## 前提・依存ライブラリ（例）

少なくとも以下をインストールしてください（プロジェクトの依存リストがある場合はそちらを参照）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml (validate_config の YAML 検証を使う場合)

インストール例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# パッケージとしてインストールする場合（pyproject.toml が存在する前提）:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワーク環境に移動:
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数ファイルの作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートの `.env` を生成/更新します。
   - もしくは `.env.example` を参考に `.env` を直接作成してください。

4. 設定検証（起動前に推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告も fail 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの準備:
   - デフォルトの SQLite / DuckDB パスは `.env` で設定可能（環境変数 `SQLITE_PATH`, `DUCKDB_PATH`）。
   - `data/` ディレクトリや `logs/` ディレクトリは自動作成されますが、権限に注意してください。

6. （オプション）OpenAI 機能を使う場合:
   - 環境変数 `OPENAI_API_KEY` を設定します。
   - AI 機能は key が未設定だと例外が出る設計（明示的エラー）です。

---

## 実行方法（使い方）

### 環境変数の重要項目（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI API（AI 機能利用時）

### ExecutionEngine の起動
- 本番 / 開発 / ペーパートレードは KABUSYS_ENV で制御:
  ```bash
  # ペーパートレードで起動（専用 DB に記録）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 本番環境で起動
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```
- 起動時、`data/execution.pid` に pid ファイルを書きます。
- 停止シグナルは `data/stop_requested.flag` または監視側で生成される `data/kill.flag` によって行えます。

### Monitoring の起動
- ポーリングループを開始します（デフォルト 60 秒間隔）。環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能。
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を 30 秒に変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 監視は監視用 sqlite_path (`SQLITE_PATH`) を使用します。run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します（重要）。

### Kill Switch / 停止フラグ
- KillSwitch は `settings.kill_flag_path`（デフォルト `data/kill.flag`）に理由テキストを書き込みます。
- ExecutionEngine は `data/stop_requested.flag`（あるいは `data/kill.flag` の存在）を検知して終了します。
- Kill flag を手動でクリアするにはファイルを削除します（`KillSwitch.clear()` を使うか手動で削除）。

### Paper Trading 検証レポート
- ペーパートレードの DB から検証レポートを生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

### AI / リサーチ関数の利用例（ライブラリ呼び出し）
- スクリプトや REPL から直接モジュールを呼べます（例: duckdb 接続を渡す）:
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 20), api_key="sk-...")
  ```
  - OpenAI を使う場合は `OPENAI_API_KEY` が必要（関数引数でも指定可能）。

---

## ロギング

- 共通ロギング設定は `kabusys.utils.logging_setup.setup_logging` を使って初期化されます。
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテーションのファイル出力: logs/<app_name>.log（30日保持）
- 環境変数 `LOG_DIR`、`LOG_LEVEL` または `setup_logging` の引数で上書きできます。

---

## 便利な CLI

- .env の初期作成 / 更新:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定の事前検証:
  ```bash
  python -m kabusys.validate_config
  ```

---

## 注意事項 / 運用上のヒント

- run_monitoring は KABUSYS_ENV に関わらず `SQLITE_PATH`（＝本番監視 DB）を使用します。開発中は別 DB を指定するか注意して実行してください。
- 実行時にデータベースやログディレクトリの作成に失敗するとファイル出力ハンドラが無効化されコンソールのみになる場合があります（権限等を確認してください）。
- AI 機能は API レート制限やエラーを踏まえフォールバック処理が多く入っていますが、API キーやコストに注意してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（Kill Switch を自動クリアしてしまうため）。デフォルトは `0`（自動クリアしない）を推奨します。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/            # ExecutionEngine, OrderManager 等（実装はこのリポジトリ内に存在）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (実装により存在)
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

（上記は本 README に含まれる主要ファイルの抜粋です。実際のリポジトリにはさらに細かなモジュールが含まれます）

---

## 追加情報 / 開発者向けメモ

- プロジェクトルートの検出は `kabusys.config._find_project_root()` が .git または pyproject.toml を基準に行います。これにより `.env` の自動読み込みが CWD に依存せずに機能します。
- DuckDB を用いたリサーチ部分は大規模データでも高速に集計が可能です。prices_daily / raw_financials / raw_news 等のテーブル設計に依存します。
- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して環境自動ロードを無効化できます。

---

問題や改善案があれば README を更新します。運用フロー（デプロイ、監視、アラート経路など）に合わせて README を適宜拡張してください。