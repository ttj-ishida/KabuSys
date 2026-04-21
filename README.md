# KabuSys

日本株向けの自動売買／研究基盤ライブラリ & 実行スクリプト群です。  
主に以下の役割を持ちます。

- 発注エンジン（ExecutionEngine）と監視（Monitoring）を分離して運用できる構成
- DuckDB を用いたリサーチ／ファクター計算
- Paper Trading 用の分離された SQLite DB サポート
- ニュース NLP / レジーム判定（OpenAI API）による補助機能
- 環境設定ウィザード・設定検証ツール・運用ツール群

バージョン: 0.1.0

---

## 主な機能

- 環境設定管理
  - .env ウィザード（python -m kabusys.config_setup）
  - 起動前チェック（python -m kabusys.validate_config）
- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合、MockBroker を利用して data/paper_trading.db に記録（本番 DB と分離）
  - Monitoring のポーリングループ起動スクリプト（run_monitoring.py）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - 監視は本番用 sqlite_path を常に参照（環境に依らず）
- 監視関連
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン / ポジション上限監視と kill flag のトリガー
  - KillSwitch: data/kill.flag による ExecutionEngine 停止シグナル発行
  - MonitoringDB: SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算（lot 単位丸め含む）
- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計
- AI 支援
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に保存
  - regime_detector: ETF の MA200 とマクロニュースの LLM 出力を合成して市場レジーム判定
  - ※ OpenAI 呼び出しには OPENAI_API_KEY が必要
- 運用ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提・依存

主なライブラリ（pip でインストールすることを想定）:

- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML の内容検証を有効にする場合）
- (標準ライブラリに含まれる sqlite3 等は不要)

仮想環境を作成してからインストールすることを推奨します:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # 実プロジェクトでは requirements.txt を用意してください
# または最小インストール例:
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主要）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / よく使う設定（デフォルト付与あり）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード専用 DB）
- LOG_LEVEL: INFO（DEBUG, WARNING, ...）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API を利用する機能で必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（kill flag 動作関連）

.env は .git に含めないでください（config_setup により生成可）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / プロジェクトディレクトリへ移動
2. 仮想環境作成 & 依存インストール（上記参照）
3. 環境変数ファイルを作成
   - 対話式ウィザードで簡単に作成できます:

     ```bash
     python -m kabusys.config_setup
     ```

   - 生成後は設定を検証:

     ```bash
     python -m kabusys.validate_config
     # 警告も失敗扱いにしたい場合:
     python -m kabusys.validate_config --strict
     ```

4. 必要ディレクトリ（data, logs など）は通常自動で作成されますが、手動で作る場合:

   ```bash
   mkdir -p data logs
   ```

5. DuckDB / SQLite の初期化は各コンポーネント起動時に行われます（monitoring は init_monitoring_db を実行）。

---

## 実行方法（運用）

- ExecutionEngine 起動:

  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
  - ペーパートレード時は MockBroker と分離 DB を使います

  ```bash
  # ペーパートレード（例）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 本番（注意: 実際に発注されます）
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

  実行時、data/execution.pid（デフォルト）に PID が書き込まれ、data/stop_requested.flag が存在すると起動／継続を停止します。

- Monitoring 起動:

  ```bash
  # デフォルト（MONITOR_POLL_INTERVAL=60）
  python -m kabusys.run_monitoring

  # ポーリング間隔を短く設定する例（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  Monitoring は設定にかかわらず本番 sqlite_path（SQLITE_PATH）を参照します。監視スクリプトは stop_requested.flag を検知してループを終了します。

- Kill Switch（手動で Execution を停止させたい場合）
  - kill.flag を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch クラス経由で監視ルールに基づき自動作成されます）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- Paper Trading 検証レポート:

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## ライブラリ利用例（研究用 API）

DuckDB 接続を渡してファクター計算等を呼び出せます。簡単な例:

```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 4, 10)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

AI 機能を使う場合は環境変数 OpenAI キーを設定してください:

```bash
export OPENAI_API_KEY="sk-..."
python -m kabusys.ai.news_nlp  # 直接モジュールではなく score_news 等を呼ぶ設計
```

（score_news / score_regime は DuckDB 接続と target_date を受け取る関数として提供されています）

---

## 運用上のポイント

- Paper Trading はデータベースが分離されるので実際の発注ログを汚しません。PAPER_TRADING_SQLITE_PATH を利用。
- Monitoring は常に本番用の SQLITE_PATH を参照する設計になっています（監視は本番 DB を見る想定）。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリが作れない場合はコンソール出力のみになります。
- プロセス優先度は起動スクリプト内で set_process_priority("high") が呼ばれます（権限によっては失敗して警告が出ます）。
- OpenAI を用いる処理は外部 API に依存するため、失敗時はフォールバック（ゼロ値やスキップ）でフェイルセーフに動作するよう設計されています。
- 設定検証（validate_config）は .env と config/*.yaml の存在や基本妥当性をチェックします。PyYAML があると YAML の中身も検証されます。

---

## ディレクトリ構成

主要ファイル・モジュールの概観（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

（上の tree は抜粋です。詳細はソースツリーを参照してください）

---

## 追加情報 / トラブルシューティング

- .env の自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- log ディレクトリ作成失敗時はコンソール出力のみになります。ファイル書き込みに失敗した場合は警告が出ます。
- DuckDB/SQLite のファイルパスは Settings によるデフォルトを持ち、環境変数で上書きできます。データディレクトリ（data/）は起動時に作成されるケースが多いですが、権限等で失敗する場合は手動で作成してください。
- OpenAI 関連の処理はレート制限や一時的な API エラーに対して指数バックオフでリトライしますが、最終的に失敗した場合は該当箇所をスキップして継続します（例外は上位へ伝播しない設計）。

---

必要に応じて README を拡張します。運用フロー（systemd / Docker / コンテナ化）、CI 設定、さらなるデプロイ手順などを追加したい場合は用途を教えてください。