# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視機能を提供するモジュール群です。  
README はプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を主な目的とする Python ベースのシステムです。

- 戦略に基づく銘柄選定・ポジション構築（ポートフォリオ構築）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 実行・注文・システム状態の監視（アラート / Kill Switch）
- リサーチ（ファクター計算・特徴量解析）
- ニュースを用いた LLM（OpenAI）によるセンチメント評価（AI モジュール）
- ペーパートレード検証レポート生成ツール

設計方針の一部：
- DB（DuckDB / SQLite）を用いたデータ管理
- 実行環境（本番 / ペーパートレード / 開発）に応じた挙動
- フラグファイルによるプロセス制御（停止 / Kill Switch）
- ログはコンソールと日次ローテートファイルで出力

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` の場合は MockBroker を利用して専用 DB に記録。
- 監視（ポーリング）起動スクリプト
  - `run_monitoring.py`：SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL で間隔指定可（デフォルト 60 秒）。
- 設定関連 CLI
  - `config_setup.py`：対話式で `.env` を生成 / 更新するウィザード。
  - `validate_config.py`：環境変数や config/*.yaml の検証ツール。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、重み算出、リスク調整、ポジションサイズ決定（等金額、スコア重み、リスクベース等）。
- 監視サブシステム
  - system / trade / risk 各 Monitor、MonitoringDB（SQLite）への永続化、KillSwitch、MonitoringEngine。
- AI & リサーチ
  - `ai/news_nlp.py`：OpenAI を用いたニュースセンチメントスコアリング（ai_scores への書き込み）。
  - `ai/regime_detector.py`：ETF MA200 とマクロニュースを組み合わせた市場レジーム判定。
  - `research/*`：ファクター計算・将来リターン計算・IC（情報係数）など。
- ツール
  - `tools/paper_verification_report.py`：ペーパートレードの検証レポート生成（稼働率、約定率、レイテンシなど）。

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法に | 演算子などを使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite は標準ライブラリで利用

インストール例（仮の requirements を想定）:
```
pip install duckdb psutil openai PyYAML
```

---

## 設定（.env）と環境変数

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な環境変数（デフォルトや説明）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（SQLite）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード用）。デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- OPENAI_API_KEY: OpenAI を使う機能（news/regime）で必要
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒）。デフォルト: 60
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）。デフォルト: 0

.env を手動で作成してもよいですが、対話式ウィザードを推奨します（下記セットアップ参照）。

注意:
- `.env` は絶対にリポジトリにコミットしないでください（機密情報含む）。

---

## セットアップ手順

1. リポジトリをクローン、Python 仮想環境を作成・有効化
2. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
3. .env を作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは既存 `.env` を読み込み、対話で編集できます。
4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` をつけると警告も失敗扱いになります。
5. 必要に応じて data/ ディレクトリやログディレクトリを作成（多くのスクリプトで自動作成されますが、権限などのため手動で作ることも推奨）：
   ```
   mkdir -p data logs
   ```

---

## 実行方法（基本）

- ExecutionEngine（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。
  - プロセス優先度は `high` に設定されます（可能な場合）。
  - 起動前に `data/stop_requested.flag` が存在すると起動しません。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 監視ループは MONITOR_POLL_INTERVAL（秒）で動作（デフォルト 60 秒）。
  - 監視は本番の `sqlite_path` を使用（環境に依存しません）。
  - `data/stop_requested.flag` を作成するとループを終了します。

- 停止 / Kill:
  - 即時停止（起動ループ停止）: プロジェクトルートの `data/stop_requested.flag` を作成（touch）します。実行中の run_monitoring / run_execution はフラグを検知して停止します。
  - Trading 停止のための Kill Switch: `KillSwitch` は `Settings.kill_flag_path`（デフォルト `data/kill.flag`）へ理由を書き込み、ExecutionEngine 側で検知して発注停止を行う設計です。Kill Switch はリスク条件（ドローダウン超過等）で自動作成されます。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると `kill.flag` を自動でクリアします（本番では通常 0 を推奨）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite DB パス指定、または環境変数 `PAPER_TRADING_SQLITE_PATH` を使用します。

---

## 使い方（例）

1. 環境をセット
   ```
   python -m kabusys.config_setup
   python -m kabusys.validate_config
   ```
2. データが揃っていることを確認（DuckDB の prices_daily 等）
3. 監視サービスを起動（本番監視）
   ```
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   ```
4. 実行エンジンを起動（発注）
   ```
   python -m kabusys.run_execution
   ```
5. ペーパートレード検証
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

---

## ログ

- ログ出力は `kabusys.utils.logging_setup.setup_logging` で統一管理されます。
- コンソール（stdout）出力 + 日次ローテートのファイル出力（デフォルトディレクトリ `logs/`）を使用します。
- 各アプリケーション（`execution` / `monitoring` など）は `logs/<app_name>.log` に出力され、30 日分保持されます。

---

## 注意事項 / 運用上のポイント

- Monitoring はどの KABUSYS_ENV のときも監視用 SQLite（Settings.sqlite_path）を使用します。Execution は `paper_trading` のとき専用 DB に切り替えます（本番 DB と分離）。
- `.env` に機密情報（API キー等）が含まれるため、絶対に Git にコミットしないでください。
- OpenAI を使う機能（ニュース NLP / レジーム判定）は別途 `OPENAI_API_KEY` の設定と API 利用料が発生します。API エラーはフェイルセーフでスコア 0.0 等にフォールバックする実装になっていますが、運用方針は注意してください。
- `PAPER_FILL_MODE` の設定によってペーパートレードでの約定挙動が変わります（instant / partial / never / reject）。
- `KILL_FLAG_CLEAR_ON_START=1` の使用は本番では危険です（自動で Kill Flag を消してしまい、意図せず発注を再開する恐れがあるため本番環境では `0` 推奨）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py — 将来リターン / IC /統計サマリ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・上限・丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（※実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成 / 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等、実装参照）
  - execution/
    - execution_engine.py — 発注エンジン（EngineConfig / run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注周りの実装
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (ランタイム)
    - stop_requested.flag — ループ停止用フラグ（作成で監視・実行を停止）
    - kill.flag — Kill Switch 理由書き込み先（Execution 側で検知）
    - execution.pid — ExecutionEngine の PID（起動時に書き込み想定）
  - logs/ (ランタイム)
    - execution.log, monitoring.log, ... — 日次ローテートされるログ

（上記は主要モジュールのみを抜粋しています。詳細はソースコードを参照してください。）

---

もし README の追加項目（API ドキュメント、設定ファイルテンプレート、運用手順書、docker-compose など）を生成したい場合は、その要望を教えてください。必要に応じてサンプル `.env.example` や systemd / supervisor の起動設定例も作成できます。