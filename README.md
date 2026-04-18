# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ & 起動スクリプト群）の README。  
このドキュメントはプロジェクトの概要・機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングを目的としたモジュール群です。  
主な設計方針は次のとおりです。

- 発注処理と監視・レポーティングを分離（SQLite / DuckDB を利用）
- ペーパートレード用に本番 DB と完全分離された専用 DB を用意
- ファクター計算・ポートフォリオ構築は純粋関数で実装（DB 参照は限定）
- LLM（OpenAI）を用いたニュース NLP / レジーム判定の連携機能を持つ（API キー必須）
- 冗長性を考慮したフェイルセーフ（API リトライ、部分成功時の DB 書き込み保護 等）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパー）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定管理 / CLI
  - config_setup.py: 対話式の .env 作成ウィザード
  - validate_config.py: 環境設定 / config/*.yaml の静的検証 CLI
- モニタリング
  - monitoring_engine.py: 各種 Monitor を束ねるポーリング実行器
  - system_monitor.py / trade_monitor.py / risk_monitor.py: システム・注文・リスク監視
  - monitoring_db.py: 監視ログ用 SQLite テーブル定義と永続化 API
  - kill_switch.py: 条件に応じて停止フラグ（data/kill.flag）を書き込む
- Execution（発注周り）
  - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler（発注ロジックは別ファイル群で実装）
  - BrokerClientFactory により本番ブローカー or Mock ブローカーを切替（paper_trading 用）
- リサーチ / ポートフォリオ構築
  - research: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量解析（IC 等）
  - portfolio: 候補選定、重み計算、ポジションサイジング、セクターキャップ等の純粋関数群
- AI（OpenAI 依存）
  - ai.news_nlp: ニュースのセンチメントを OpenAI で評価して ai_scores に保存
  - ai.regime_detector: 市場レジーム（bull/neutral/bear）判定と保存
- ツール
  - tools.paper_verification_report.py: ペーパートレード DB を解析して検証レポート生成

---

## 必要依存ライブラリ（主なもの）

（プロジェクトの requirements.txt を参照してください。無ければ下記を目安にインストールしてください）

- duckdb
- psutil
- openai
- PyYAML（config 検証を有効にする場合）
- Python 標準の sqlite3, logging, threading, datetime 等

インストール例（プロジェクトに requirements.txt がある場合）:
```
pip install -r requirements.txt
```
または手動で:
```
pip install duckdb psutil openai PyYAML
```

---

## 環境変数 / .env について

- 自動ロード
  - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（OS環境変数が優先）。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 主要な環境変数
  - 必須:
    - `JQUANTS_REFRESH_TOKEN` — J-Quants API 用リフレッシュトークン
    - `KABU_API_PASSWORD` — kabuステーション API パスワード
  - 運用環境:
    - `KABUSYS_ENV` — `development` | `paper_trading` | `live`（デフォルト: development）
      - `paper_trading` の場合、発注は MockBrokerClient を使い、DB は `data/paper_trading.db` を利用
  - ログ/DB パス:
    - `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）
    - `SQLITE_PATH`（監視 DB、デフォルト: data/monitoring.db）
  - LLM / 通知:
    - `OPENAI_API_KEY` — OpenAI を使う機能（news_nlp, regime_detector）で必要
    - `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` — LINE 通知用（任意）
  - ログレベル:
    - `LOG_LEVEL` — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
  - その他:
    - `PAPER_FILL_MODE` — ペーパートレードの約定挙動（instant/partial/never/reject）
    - `PAPER_TRADING_SQLITE_PATH` — ペーパー用 SQLite DB パス（上書き可能）
    - `PID_FILE_PATH`, `KILL_FLAG_PATH` — 各種ファイルパス

- .env 作成支援
  - `python -m kabusys.config_setup` を実行すると対話式ウィザードで `.env` を作成できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを入手
2. Python 環境を準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # または必要なパッケージを個別にインストール
   ```
4. .env を作成
   - 対話式:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env.example` を参考に自分で作成
5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります
6. DB / データディレクトリの作成（通常は起動時に自動作成されるが事前に作ることも可）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動 & CLI）

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは `KABUSYS_ENV` で切替
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 説明:
    - paper_trading の場合、MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録
    - 起動時に `data/stop_requested.flag` があると起動を行わず終了する
    - 実行中、`data/stop_requested.flag` を作ることで実行を安全に停止できます（監視側からも検知されます）

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を利用（KABUSYS_ENV に依らず本番 DB を参照する仕様あり）
  - 停止:
    - `data/stop_requested.flag` を作成するとループが検出して終了

- 設定検証（前述）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - もしくは DB を直接指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（ニュース NLP / レジーム判定）
  - 実行には `OPENAI_API_KEY` が必要
  - 例（ライブラリ呼び出し）:
    - news scoring:
      ```
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="xxxx")
      ```
    - regime scoring:
      ```
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="xxxx")
      ```

---

## ログ / ファイル配置（運用メモ）

- ログ
  - デフォルトで `logs/` に日次ローテートで出力（TimedRotatingFileHandler, 30日分保持）
  - ログレベルは `LOG_LEVEL` または `setup_logging()` の引数で指定
- PID / フラグファイル
  - `data/execution.pid`（デフォルト） — ExecutionEngine の PID ファイル
  - `data/stop_requested.flag` — run_* スクリプトの外部停止用フラグ（監視 / 実行スレッドでチェック）
  - `data/kill.flag` — KillSwitch が書き込むフラグ（致命的な条件で ExecutionEngine を停止させる）

---

## 主要テーブル（monitoring DB: SQLite）

monitoring_db.py により以下のテーブルが作成されます（冪等）:

- system_status: CPU/MEM/DISK、プロセス健全性、timestamp
- trade_logs: 発注イベントログ（Created/Filled/Sent 等）、latency_ms を保持
- positions: 保有ポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクアラート履歴（重複抑制機能あり）
- dashboard: 単一行の集計（id=1、portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

---

## ディレクトリ構成

下記は主要ファイル／ディレクトリの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py     — マーケットレジーム判定（LLM + ma200）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義 / API）
    - monitoring_engine.py   — モニタリング実行器
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラートの送信/管理、詳細は実装参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（上記に加えて execution/*, data/*, strategy/* といった追加モジュールが存在する想定です）

---

## 運用上の注意 / ベストプラクティス

- 本番運用前に必ず `python -m kabusys.validate_config` で設定を検証してください。
- `KABUSYS_ENV=live` のときは特に LINE 通知設定や kill flag の設定を確認してください。
- OpenAI を使う機能は API コストとレイテンシに注意。APIキーは安全に管理してください。
- `MONITOR_POLL_INTERVAL`（秒）は短くしすぎると負荷や API 制限に影響するので注意。
- ペーパートレードは実運用と DB を分離することで安全に検証できます（`KABUSYS_ENV=paper_trading`）。

---

## よく使うコマンドまとめ

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に含めるサンプル .env の例や systemd / Supervisor の起動ユニット例、より詳しい API / モジュール間の相互作用図も作成します。どの情報を追加しますか？