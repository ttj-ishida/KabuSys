# KabuSys

日本株向け自動売買システムのサンプル実装（KabuSys）。  
このリポジトリには、実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール群から構成されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・約定管理を行う。
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウンやポジション数）を定期的にチェックし、Kill Switch やアラートを発動する。
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ計算・セクター制約などの純関数実装。
- リサーチ: DuckDB 上の時系列データからファクター計算・将来リターン計算・IC 計算などを行う。
- AI 関連: ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存、マクロセンチメントと ma200 を合成して市場レジームを判定する。
- ツール: ペーパートレードの検証レポート生成などのユーティリティ。

設計方針の一部:
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番データベースと分離（独立した SQLite）。
- DuckDB を分析用 DB、SQLite を監視／発注履歴用 DB として使用。
- .env による環境設定、設定ウィザードと事前検証ツールを提供。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、`data/paper_trading.db` に記録。
  - 停止はフラグファイル（data/stop_requested.flag）や kill.flag による制御。
- 監視起動スクリプト（run_monitoring）
  - 定期ポーリングで SystemMonitor を実行。ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL）。
  - 監視はプロダクションの sqlite_path を常に使用（環境に依らず）。
- 監視コンポーネント
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, MonitoringDB
- ポートフォリオ
  - 候補選定、等重／スコア加重、リスクベースのポジションサイズ計算、セクター上限適用、レジーム乗数。
- リサーチ（DuckDBベース）
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン、IC、統計サマリー。
- AI（OpenAI 経由）
  - ニュースのセンチメントスコアリング（ニュースごとに銘柄スコア生成・ai_scoresへ保存）
  - マクロニュース + ma200 から市場レジーム判定（market_regime へ保存）
- ツール
  - Paper Trading 検証レポート生成（稼働率・注文成功率・レイテンシ等の評価）

---

## 前提・依存関係

最低限の推奨環境:
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を有効にする場合）
- SQLite（標準ライブラリの sqlite3 を使用）
- （任意）ログ出力先ディレクトリ書き込み権限

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定
   - 対話式ウィザードで `.env` を生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成（例はウィザードで生成されます）。
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要なディレクトリを作成:
   - デフォルトでは `data/` と `logs/` を使用するため、書き込み権限を確保するか自動作成許可を与えてください。
   - `.env` 内で `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を変更した場合は適切に配置してください。

注意:
- 自動で `.env` を読み込む動作は、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。
- `.env` は決して Git にコミットしないでください（ウィザードのヘッダにも注意書きあり）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト含む）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API を利用する場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のモック約定モード）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

その他（.env ウィザード参照）:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env の作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 監視ループを起動（常駐プロセス）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止: `data/stop_requested.flag` を作成するとループが終了します（または Ctrl+C）。

- 実行エンジンを起動（注文処理）
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` を設定するとペーパートレード向けモックブローカーを使用し、データは `data/paper_trading.db` に記録されます。
  - 実行エンジンも `data/stop_requested.flag` を検知して停止します。KillSwitch による停止は `data/kill.flag` の作成で実行エンジンにシグナルを送れます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` が使われます。

- AI モジュールの呼び出し例（Python スクリプト内で）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # ニューススコア（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
  score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")

  # レジーム判定
  score_regime(conn, target_date=date(2026, 4, 11), api_key="sk-...")
  ```

---

## 停止・フラグ関連

- 共通停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視する外部停止フラグ（任意のファイルを作成することで停止シグナル）。
- Kill Switch:
  - data/kill.flag — KillSwitch が作成すると ExecutionEngine に停止指示を出す（主にリスクイベント時に自動生成）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアする（本番では推奨されない）。

---

## ロギング

- 共通ロギングは `kabusys.utils.logging_setup.setup_logging` を使用。
- デフォルトは stdout と日次ローテートのファイルログ（logs/<app_name>.log）。ログディレクトリは環境変数 `LOG_DIR` で変更可能。
- ログレベルは `LOG_LEVEL` で制御。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下はリポジトリ内の主要なパッケージ構成（src/kabusys 配下）です。実際のファイル数は省略されていますが、主要モジュールを示します。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 書込ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - trade_monitor.py       — （注文滞留検出等、省略）
    - alert_manager.py       — （通知管理、省略）
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py      — BrokerClient の生成（本番／Mock 分岐）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM でスコア化
    - regime_detector.py     — ma200 + macro sentiment でレジーム判定
  - tools/
    - paper_verification_report.py

注: 上記のうち一部の補助モジュール（trade_monitor, alert_manager 等）はここに要約として挙げていますが、詳細実装はリポジトリ内のファイルをご参照ください。

---

## 実行上の注意点・ベストプラクティス

- 本番（live）環境では `.env` の内容と `KABUSYS_ENV` を必ず確認してください。`validate_config` が事前チェックに有用です。
- 本番では `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを推奨します。誤って Kill Switch を消してしまうと危険です。
- OpenAI API を使う際はレート制限や料金に注意してください。AI スコアリングはバッチ/リトライロジックを持っていますが、API キーの管理は厳重に。
- DuckDB と SQLite のファイルは適切にバックアップ・スナップショットを取得してください。
- ログや DB ファイルは容量に応じてローテーション・管理を行ってください（logs/ は日次ローテーション、バックアップ 30 日がデフォルト設定）。

---

## 参考：実行例（簡易）

1. .env を作成（ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```

2. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```

3. 監視プロセス起動（別ターミナル）
   ```bash
   python -m kabusys.run_monitoring
   ```

4. 実行エンジン起動（別ターミナル）
   ```bash
   python -m kabusys.run_execution
   ```

5. ペーパートレード検証レポート
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

---

README はここまでです。リポジトリ内の個別モジュール（monitoring, execution, ai, research, portfolio）の詳細な使い方や API はそれぞれの docstring を参照してください。追加で詳しい導入手順や運用ガイド、設定例（.env.example）を作成したい場合はお知らせください。