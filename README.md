# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ＋起動スクリプト群）

このリポジトリはアルゴリズムトレーディングの主要コンポーネント（戦略計算、ポートフォリオ構築、発注エンジン、監視、AI 補助モジュールなど）を分離して実装したものです。実運用を想定した安全装置（Kill Switch、監視ログ、ペーパートレード分離等）を備えています。

注意: 本 README はリポジトリ内のソースコード（src/kabusys 以下）を基にした概要・利用手順です。実際の本番稼働前に必ず設定の確認とテストを行ってください。

---

## 特徴（主な機能）

- 環境管理
  - .env を対話式に作成する `config_setup` ウィザード
  - 起動前チェックを行う `validate_config`（必須環境変数や config/*.yaml の存在チェック）
- 発注（Execution）
  - 実環境 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - Broker クライアントを抽象化（MockBroker を用いた paper_trading）
  - リスク管理（ポジション上限・ドローダウンなど）
  - OrderManager / Reconciler 等の発注関連コンポーネント
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログを SQLite に永続化（monitoring_db）
  - Kill Switch: 条件により `data/kill.flag` を書き込んで ExecutionEngine を停止
- ポートフォリオ構築（純関数）
  - 候補選定、等ウェイト／スコア重み付け、ポジションサイズ計算、セクター上限・レジーム調整
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI 補助
  - ニュース NLP（OpenAI）を用いた銘柄センチメントのスコアリング
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（LLM 使用）
  - API エラーに対するリトライ・フェイルセーフ実装
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - ペーパートレードの検証レポート生成スクリプト

---

## 必要条件 / 推奨環境

- Python 3.10+
  - ソースは型ヒントに Python 3.10 の構文（| 型合併）を使用しています。
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config`で YAML 検査を行う場合）
- DB
  - SQLite（標準ライブラリで利用）
  - DuckDB（分析用、duckdb パッケージ）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実運用では requirements.txt を用意して pip install -r することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して依存をインストール（上記参照）

3. 環境変数の初期化（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードに従って .env を作成します（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` は必須）。
   - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれか。
   - `PAPER_TRADING_SQLITE_PATH` を指定しておくとペーパートレード DB を分離できます。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - オプション `--strict` を付けると警告も失敗（exit 1）扱いになります。
   - `PyYAML` がない場合は config/*.yaml の検査がスキップされます。

5. ディレクトリ（data, logs）は自動作成されることが多いですが、必要に応じて手動で用意して下さい:
   ```
   mkdir -p data logs
   ```

注意:
- 自動で `.env` を読み込む仕組みはデフォルトで有効です。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- デフォルトの DB/ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log

---

## 起動・使い方

主要なモジュールは Python モジュールとして起動できます。プロジェクトルートで実行してください。

- ExecutionEngine（発注エンジン）起動
  - 本番 / ペーパートレードは KABUSYS_ENV により切り替わります。
  - ペーパートレード時は MockBrokerClient を使用し、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録されます。
  ```
  python -m kabusys.run_execution
  ```

  - 起動時、既に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 停止（外部から）は `data/stop_requested.flag` を作成するか、Monitoring の Kill Switch が `data/kill.flag` を書き込みます。

- Monitoring（監視ループ）起動
  - 監視ループは SystemMonitor 等を 60 秒間隔でポーリングします。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒
  - 監視は MonitoringDB（sqlite）へログを記録します。
  - 停止: `data/stop_requested.flag` を作成するとループを終了します。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出し）
  - OpenAI API を用いる処理は環境変数 `OPENAI_API_KEY` または関数引数で API キーを渡します。
  - 例: ニュース NLP スコア付け（ライブラリ関数）
    ```python
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date
    score_news(conn, target_date, api_key="sk-...")
    ```

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - `run_execution` / `run_monitoring` が監視している外部停止フラグ（存在すると起動しない / ループを抜ける）。
- data/kill.flag
  - KillSwitch により作成される（ExecutionEngine に停止シグナルを送る）。
  - Execution 側の設定（Settings.kill_flag_clear_on_start）により起動時に自動クリア可能（デフォルトは 0）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動時に書き込まれる想定）。
- logs/<app_name>.log
  - 日次ローテーションで出力されるログファイル（logs ディレクトリ）。

フラグの操作例:
```bash
# Execution/Monitoring を止めたい（外部から）
touch data/stop_requested.flag

# kill.flag を消す（復旧時）
rm -f data/kill.flag

# stop フラグを消して再起動
rm -f data/stop_requested.flag
python -m kabusys.run_execution
```

---

## 環境変数（主なもの）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 起動モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ログ
  - DUCKDB_PATH（default: data/kabusys.duckdb）
  - SQLITE_PATH（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
  - LOG_DIR（ログ出力先、default: logs）
- 監視関連
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、default: 60）
  - PID_FILE_PATH（Execution の PID ファイルパス、default: data/execution.pid）
  - KILL_FLAG_PATH（KillSwitch が書き込むパス、default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、"1" はクリア、default: "0"）
- AI / OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector が参照）
- Paper Trading 動作モード
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

（上記は .env で定義可能。`python -m kabusys.config_setup` で対話的に作成可）

サンプル .env（一部）:
```env
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## ディレクトリ構成（主要ファイル）

（src 以下を想定、抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  (発注関連コンポーネント)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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

（実際のファイルはリポジトリ内を参照してください）

---

## ログ・監視について

- ログは stdout に出力され、同時に logs/<app_name>.log に日次でローテートされます。
- Monitoring は system_status / trade_logs / risk_logs / positions / dashboard のテーブルを SQLite に保管します。
- RiskMonitor はドローダウンやポジション数上限を監視し、必要時に risk_logs にイベントを記録、KillSwitch がトリガーされると data/kill.flag を作成します。

---

## 開発者向けメモ

- DuckDB 接続を受け取ってファクター計算や AI 用のデータ集約を行う設計なので、テスト時は DuckDB のメモリ内 DB を用いると便利です。
- AI 呼び出しは外部依存のため、ユニットテストでは _call_openai_api をモックすることで制御できます（ソースにもテスト向けコメントあり）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI / テストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい。

---

## トラブルシューティング（よくある事項）

- ログファイルが作られない／ファイルハンドラ作成に失敗する場合:
  - `LOG_DIR` のディレクトリ作成権限を確認してください。作成不可の場合は stdout のみで動作します（warning が出ます）。
- OpenAI API 呼び出しで失敗する場合:
  - `OPENAI_API_KEY` を正しく設定しているか確認。ネットワーク・レート制限による一時失敗はリトライ実装があります。
- run_execution がすぐ終了する場合:
  - `data/stop_requested.flag` が存在していないか確認してください（存在すると起動を行いません）。

---

README はここまでです。実行方法や設定に関して不明点があれば、使用したいユースケース（開発 / ペーパートレード / 本番）を教えてください。それに合わせて具体的な手順やサンプル .env を追加で作成します。