# KabuSys

日本株自動売買システムのコアライブラリ / 起動スクリプト群です。  
このリポジトリはトレード実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース/NLP）連携などの主要機能を持つモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要な以下の機能を提供する Python モジュール群です。

- 発注エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- リスク管理（RiskMonitor / KillSwitch）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- ファクター計算・特徴量探索（research）
- ニュースを用いた AI スコアリング（OpenAI 経由）
- 設定ウィザード / 設定検証 用 CLI ツール
- ペーパートレード用ログ解析レポート作成ツール

設計方針の一部:
- 環境変数／.env による設定管理
- DuckDB（価格・財務データ）と SQLite（監視・発注ログ）を併用
- 本番とペーパートレードを DB レベルで分離（paper_trading モード）
- OpenAI（gpt-4o-mini 等）を使った NLP 部分は API キー必須、失敗時はフェイルセーフ動作

---

## 主な機能一覧

- run_execution.py — ExecutionEngine の起動（本番 / ペーパートレード対応）
- run_monitoring.py — SystemMonitor ポーリングループの起動（MONITOR_POLL_INTERVAL で間隔変更可）
- config_setup.py — .env を対話式に生成・更新するウィザード
- validate_config.py — .env と config/*.yaml の事前検証 CLI
- tools/paper_verification_report.py — ペーパートレードログからの検証レポート生成
- portfolio/* — 銘柄選定、重み算出、ポジションサイズ計算、リスク調整
- research/* — ファクター計算（Momentum/Value/Volatility）、将来リターン、IC 等
- ai/* — ニュース NLP スコアリング、レジーム判定（OpenAI 使用）
- monitoring/* — 監視 DB（SQLite）アクセス、各種モニター、KillSwitch、アラート管理
- utils/* — ログ設定、プロセス優先度・CPU affinity ユーティリティ等

---

## 前提条件

- Python 3.10 以上（型ヒントで PEP 604 の `|` を使用）
- 必要な Python パッケージ（最小例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を行う場合）
- SQLite3 は標準ライブラリに含まれます

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai pyyaml
```

（プロジェクト配布に requirements.txt があればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 環境を準備（v3.10+ 推奨）

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuAPI パスワード等、主要な環境変数を対話で入力して `.env` を生成します。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 厳格モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じ）
   - デフォルト DuckDB: `data/kabusys.duckdb`
   - デフォルト SQLite (monitoring): `data/monitoring.db`
   - ペーパートレード DB: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
   - ログディレクトリ: `logs/`（ログ設定ユーティリティが自動作成します）

---

## 使い方

### 実行エンジン（ExecutionEngine）
- 標準実行:
  ```
  python -m kabusys.run_execution
  ```
- KABUSYS_ENV の値により挙動が変わります:
  - `development`：開発・テスト用（発注しない）
  - `paper_trading`：MockBrokerClient を使用し、ペーパートレード DB (`PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`) に記録します
  - `live`：本番（実際に発注が行われます。API キー等の設定に注意）

- ペーパーモード例:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  paper_trading 時は発注はモック化され、本番 DB と分離されます。

- 停止方法:
  - 外部から停止させたい場合はプロジェクトの `data/stop_requested.flag` を作成するとループが停止します。
  - ExecutionEngine に停止シグナル（Kill Switch）を送る場合は `data/kill.flag` が利用されます（KillSwitch 実装を参照）。

### 監視プロセス（Monitoring）
- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔を環境変数で上書き:
  ```
  export MONITOR_POLL_INTERVAL=30  # 30秒毎
  python -m kabusys.run_monitoring
  ```
  デフォルトは 60 秒です。

- 監視は本番 sqlite_path を環境にかかわらず使用します（設定次第）。

### .env の作成 / 更新
- 対話式ウィザード:
  ```
  python -m kabusys.config_setup
  ```

### 設定検証
```
python -m kabusys.validate_config
```

### ペーパートレード検証レポート
- DB を指定してレポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
- 環境変数 `PAPER_TRADING_SQLITE_PATH` を使うことも可能。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時に必須）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）

注意: `KABUSYS_ENV=live` を使う場合は設定とキーの扱いを十分に確認してください。`KILL_FLAG_CLEAR_ON_START` が 1 の場合、本番で Kill Flag を自動クリアする挙動になるため危険です（デフォルト 0 を推奨）。

---

## ログ・停止フラグについて

- ログ：logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring 内のループを安全に停止するためにチェックされます
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止シグナルを送るために使用されます
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（該当ファイル参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（kill.flag 書込）
    - monitoring_engine.py — 各 Monitor の統括（テスト用 / 実運用ループ）
    - alert_manager.py — アラート送信（LINE 等を想定）
  - execution/  (発注に関するコンポーネント群)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py — 統一ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/ ... （実行時に作成されるディレクトリ、DB / フラグファイルを格納）

---

## 開発者向けメモ / 注意事項

- AI 系機能（ai.news_nlp, ai.regime_detector）は OpenAI API を利用するため `OPENAI_API_KEY` が必要です。API エラー時はフェイルセーフで処理を継続する実装が多いですが、運用上の取り扱いに注意してください。
- `monitoring` 側は本番の monitoring DB（sqlite）を環境にかかわらず参照します。ペーパートレードは `run_execution` 側で DB を分離します。
- `config.py` はプロジェクトルート（.git または pyproject.toml）を探索して `.env` 自動読み込みを行います。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `process_priority.set_process_priority` は psutil による優先度変更を行いますが、権限不足や未対応 OS の場合は警告を出してスキップします。
- データベースマイグレーションは `init_monitoring_db` 内で簡易的に行われます（列追加などの処理あり）。

---

## サポート / 追加実行例

- ログレベル指定:
  ```
  export LOG_LEVEL=DEBUG
  python -m kabusys.run_monitoring
  ```

- 一時的にモニターのポーリング間隔を 10 秒に:
  ```
  export MONITOR_POLL_INTERVAL=10
  python -m kabusys.run_monitoring
  ```

---

README に記載のコマンドやパスはデフォルト設定に基づきます。実運用時は `.env` に必要な値を設定し、validate_config で検証したうえで `KABUSYS_ENV` を適切に設定して運用してください。