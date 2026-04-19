# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群です。本リポジトリは以下の機能群を含み、運用／ペーパートレード／研究用途で利用できます。

- 自動発注エンジン（ExecutionEngine）
- 監視（Monitoring）・Kill Switch
- ポートフォリオ構築ユーティリティ（選定・配分・ポジションサイズ）
- ファクター計算・研究モジュール（DuckDB／prices_daily ベース）
- ニュース NLP / レジーム判定（OpenAI を利用するモジュール）
- 設定ウィザード・設定検証ツール・検証レポート生成ツール

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い DB を分離。
- run_monitoring: SystemMonitor 等のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を調整可能（デフォルト 60 秒）。
- config_setup: 対話式ウィザードで `.env` を生成／更新。
- validate_config: .env および config/*.yaml の整合性チェック CLI。
- tools.paper_verification_report: ペーパートレードの検証レポート生成（SQLite DB から各種指標を算出）。
- portfolio モジュール: 候補選定、重み算出、セクター制約、レジーム乗数、ポジションサイズ決定（純粋関数で DB 参照なし）。
- research モジュール: モメンタム / ボラティリティ / バリューなどのファクター計算、将来リターン・IC 計算、統計サマリー。
- ai モジュール: ニュースに対する NLP スコアリング（OpenAI）や市場レジーム判定（OpenAI + ETF MA を合成）。
- monitoring: system/trade/risk の各モニタ、監視用 DB（SQLite）への永続化、アラート発行、Kill Switch。

---

## 必要条件（概略）

- Python 3.9+
- 必須ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（`validate_config` の YAML 検証で必要）
- SQLite（Python 組み込み）
- ネットワーク接続（OpenAI 等を利用する場合）

インストールは環境に合わせて仮想環境を作成し、必要パッケージをインストールしてください（一般例）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# またはパッケージをまとめた requirements.txt がある場合:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を用意して依存をインストール（上記参照）。

3. 環境変数設定（.env）
   - 対話式ウィザードで作成／更新：
     ```
     python -m kabusys.config_setup
     ```
   - `.env` の自動ロード
     - 実行時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込みます。
     - OS 環境変数は上書きされません。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（logs, data など）は自動作成されることがありますが、必要に応じて手動で作成してください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行設定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

- データベース / ファイルパス
  - DUCKDB_PATH: 分析用 DuckDB パス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用 flag（デフォルト data/kill.flag）

- モニタリング
  - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）

- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュール利用時）
- PAPER_FILL_MODE: paper_trading 時の MockBroker のフィル動作（instant/partial/never/reject）

注意: config_setup に項目リストと説明があります。`.env` は絶対に Git へコミットしないでください。

---

## 使い方（実行コマンド）

- ExecutionEngine 起動（発注エンジン）
  ```
  # 環境例: ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading の場合、MockBroker を使用し `data/paper_trading.db` に記録して本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンに停止シグナルが送られます。
  - 実行の PID は `data/execution.pid` に保存されます（設定により変更可）。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒）。
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用 sqlite_path を使って監視ログを書きます（KABUSYS_ENV に依存しません）。
  - 停止するにはプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C。

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
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア等）はライブラリ API としても利用可能です（例）
  ```python
  from kabusys.ai import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date: datetime.date
  count = score_news(conn, target_date, api_key="sk-...")
  ```

---

## Kill Switch / 停止フラグ

- Kill Switch は監視コンポーネントが異常を検出した場合に `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
- 手動で停止シグナルを送る場合は `data/kill.flag` を作成します（内容は理由のテキスト）。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアしますが、本番では推奨されません（安全上の理由）。

停止フラグ（run_monitoring/run_execution）が監視するファイル:
- data/stop_requested.flag — 監視／実行ループを穏やかに終了させるためのフラグ
- data/kill.flag — Kill Switch 用（主に ExecutionEngine を停止させる）

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用してログを統一的に設定します。
- デフォルトのログディレクトリ: `logs/`。アプリ名ごとに日次ローテートされるログファイルが生成されます（例: logs/execution.log, logs/monitoring.log）。
- LOG_DIR 環境変数でログディレクトリを変更可能。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要部分（src/kabusys 以下）です。実際のリポジトリには追加のモジュールやスクリプトが含まれる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite のスキーマと永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねる実行エンジン
    - kill_switch.py         — kill.flag の管理
    - trade_monitor.py       — 発注／約定ログの監視（詳細実装）
    - alert_manager.py       — アラート通知（LINE など、具体実装は別途）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 株数計算・集計キャップ/ロット丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム等ファクター計算（DuckDB）
    - feature_exploration.py — IC/統計解析ユーティリティ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py     — レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/                      — デフォルト DB / フラグファイル 保存先（実行時に作成）
- logs/                      — ログ出力先（setup_logging による）

---

## 開発・研究での利用例

- ファクター計算（研究用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 4, 10))
  ```

- ポートフォリオ組成
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

---

## 注意事項 / 運用上のヒント

- `.env` は機密情報を含むため絶対に Git にコミットしないこと。
- KABUSYS_ENV を `live` に設定する場合は `validate_config` を実行し、LINE 通知等の本番用設定を必ず確認してください。
- OpenAI を使用する機能は API コストとレイテンシが発生します。API キー管理・リトライ制御の挙動（429, 5xx 対応など）が実装されていますが、運用時は注意してください。
- 監視は Monitoring 用 SQLite に状態を記録します。monitoring モジュールは本番と切り離して動作する設計の箇所がありますが、設定値（SQLITE_PATH 等）は事前確認を推奨します。
- process_priority や CPU affinity の設定はプラットフォーム依存で失敗する場合があるため、警告をログに出してスキップします。

---

必要であれば、README に加えて以下を追加作成できます：
- requirements.txt（依存固定）
- デプロイ / systemd / Docker 用の起動例
- よくある運用手順（バックアップ、DB マイグレーション、ログローテーション運用） 

ご希望があれば、上記いずれかを作成します。