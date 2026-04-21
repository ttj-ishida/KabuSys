# KabuSys

日本株向け自動売買システムのパッケージ（KabuSys）。  
この README はリポジトリの主要コンポーネント、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視機能を備えたモジュール群です。主な機能は次のとおりです。

- ExecutionEngine：発注フロー（実際のブローカ／ペーパートレード両対応）
- Monitoring：システム稼働状況・取引状況・リスクの定期監視とアラート
- Portfolio construction：銘柄選定、配分、ポジションサイズ計算
- Research：ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI 支援：ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定など
- ツール：Paper Trading 検証レポート生成スクリプト など

パッケージは pure-Python で構築され、DuckDB / SQLite をデータ格納に利用します。実行時は環境変数および `.env` により挙動を制御します。

---

## 主な機能一覧（抜粋）

- Execution
  - 本番（live）／ペーパートレード（paper_trading）切替
  - paper_trading 時は MockBrokerClient を使用し DB を分離（デフォルト: `data/paper_trading.db`）
  - PID ファイル管理、停止フラグ検出
- Monitoring
  - CPU / メモリ / ディスク / プロセス存否の定期チェック
  - 取引ログ / リスクログ / ダッシュボード永続化（SQLite）
  - Kill Switch（ドローダウン等で ExecutionEngine を停止）
  - アラート管理（LINE 等の外部通知は設定次第）
- Portfolio
  - 候補選定、等金額/スコア配分、リスクベースのポジション決定、セクター制限
- Research
  - モメンタム / ボラティリティ / バリューファクター等の計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI
  - ニュースを LLM（OpenAI）でスコア化して ai_scores に格納
  - マクロニュースと ETF 指標を組み合わせて市場レジーム判定
- ツール
  - 設定ウィザード（`.env` 作成）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 必要な依存関係（代表）

（プロジェクトの requirements.txt がある場合はそれを優先してください）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML のパースを行う場合に必要）
- （その他: 標準ライブラリのみで動作する機能も多数あります）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローン
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 初期 `.env` を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動作成。最低限必要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 代表的な設定例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
4. 設定検証（任意、起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL として扱う
   ```
5. データディレクトリなどの作成は起動スクリプトが自動で行う場合がありますが、手動で `data/` と `logs/` を作っておくと良いです。

---

## 主要コマンド使い方

- ExecutionEngine 起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - 環境切替（ペーパートレード）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用され、本番 sqlite は変更されません。
  - 実行中に停止させるには `data/stop_requested.flag` を作成するか（stop フラグ）、Execution 側が Kill Switch により `data/kill.flag` を検出して停止します。

- Monitoring 起動
  - デフォルトポーリング間隔 60 秒（環境変数で変更可）
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を上書き:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - 監視はモニタリング用の sqlite パス（Settings.sqlite_path）を常に参照します（ドキュメント注記: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します）。

- 設定ウィザード
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
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` で明示可、あるいは `PAPER_TRADING_SQLITE_PATH` 環境変数で指定。

- AI 機能を使う場合
  - 環境変数に OpenAI API キーを設定:
    ```
    export OPENAI_API_KEY=sk-...
    ```
  - ニューススコアリング（ライブラリ関数）:
    - 例: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` — api_key が None の場合は環境変数を参照

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB/ファイル:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- Monitoring:
  - MONITOR_POLL_INTERVAL（秒、デフォルト: 60）
- その他:
  - OPENAI_API_KEY（AI 機能で必要）
  - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant | partial | never | reject）

設定の自動ロード:
- プロジェクトルートが .git または pyproject.toml により検出される場合、`.env` と `.env.local` が自動で読み込まれます（OS 環境変数を上書きしない挙動に注意）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定。

---

## ログ・プロセス管理

- ロギングは `kabusys.utils.logging_setup.setup_logging` を通じて統一管理。デフォルトで stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を出力します。
- プロセス優先度は `kabusys.utils.process_priority.set_process_priority` により起動時に `high` に設定されます（権限等により失敗してもスキップされます）。
- PID ファイル: Execution は `data/execution.pid` に PID を書く（設定で上書き可）。
- 停止フラグ:
  - `data/stop_requested.flag`：run_* スクリプトが監視している停止要求フラグ（存在でループ終了）。
  - `data/kill.flag`：KillSwitch が書き込む Execution 停止用フラグ（存在で Execution を停止）。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされますが、本番では `0` を推奨。

---

## 注意点 / 実運用上のメモ

- Monitoring は常に「本番」用の sqlite_path を参照する仕様がある（run_monitoring のドキュメント参照）。運用時は監視用 DB の配置に注意してください。
- Execution の paper_trading モードは本番 DB と分離され、`PAPER_TRADING_SQLITE_PATH` を使用します。リスクのある書き換えを防ぐため本番 DB を誤って使わないようにしてください。
- OpenAI を使う機能は API 呼び出しの失敗に対してリトライやフォールバックを備えていますが、API キーの上限や課金に注意してください。
- DuckDB 側の SQL クエリは日付範囲（ルックアヘッド）に注意して実装されています（研究・AI モジュールともに将来データを参照しない配慮あり）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 以下の主要構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境設定管理（.env 自動ロード / Settings）
  - config_setup.py           — .env 作成ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                 — ExecutionEngine 関連（broker, order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は代表的なファイルを抜粋しています。細かい実装は各ファイルを参照してください。）

---

## 開発・デバッグ

- 単体関数群（portfolio、research、monitoring_db 等）は外部副作用を最小限にした純粋関数として設計されており、ユニットテストが書きやすい構成になっています。
- DuckDB / SQLite を用いるモジュールは接続オブジェクトを引数で受け取るため、テスト用の一時 DB を用意してテスト実行できます。
- OpenAI 呼び出し箇所は内部でラップしてあり、テスト時は該当関数をモックすることで外部 API 呼び出しを回避できます（ソース中に patch 用のコメントがある箇所あり）。

---

## バージョン

パッケージバージョンは `kabusys.__version__` により管理（現状: 0.1.0）。

---

必要であれば、運用手順（systemd 単位ファイル例、Docker 化、デプロイ手順）や詳細な環境変数一覧、さらに具体的な運用ガイド（ログローテーション確認、DB バックアップ、Kill Switch 運用ポリシー等）も追加で作成します。どの部分を深掘りしましょうか？