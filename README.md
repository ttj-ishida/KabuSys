# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコア実装群を含みます。  
ここではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ・モニタリングを行うシステムです。  
主な役割は以下です。
- 戦略に基づく銘柄選定・ポジションサイズ計算（ポートフォリオ構築）
- 発注処理（ExecutionEngine） — 実際のブローカー or ペーパートレードの切り替え対応
- 監視（Monitoring） — システム健全性、注文/約定状態、リスク指標の監視とアラート
- 研究モジュール（DuckDB を使ったファクター計算・検証）
- AI 支援（ニュースセンチメント、レジーム判定：OpenAI API を利用）
- 各種ユーティリティ（設定ウィザード・設定検証・レポート生成など）

設計方針の一部：
- DuckDB / SQLite をデータ永続化に利用
- 環境毎に挙動を分ける（development / paper_trading / live）
- 本番 DB とペーパートレード DB は分離
- ログ・PID・フラグファイルによるプロセス制御と監視

## 主な機能一覧
- ExecutionEngine（発注ロジック、OrderManager、RiskManager、Reconciler 等）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- Portfolio construction（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール（ニュースセンチメント score_news、レジーム判定 score_regime）
- 設定関連（.env ウィザード、設定検証 CLI）
- ツール（Paper Trading 検証レポート生成等）

## 前提（依存関係）
最低限必要なパッケージ（主要なもの）：
- Python 3.10 以上（型注釈の union などを利用しているため）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイルの検証を行う場合。任意）

標準ライブラリ:
- sqlite3 等

インストール例（仮）:
```
python -m pip install duckdb psutil openai pyyaml
```

## セットアップ手順

1. リポジトリをクローン・チェックアウトする。
2. 仮想環境を作成して依存パッケージをインストールする。
3. .env を作成する（手動かウィザードを利用）。
   - サンプル: `.env.example` を参照（本リポジトリにある場合）。
   - 重要な環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 利用時）
4. データディレクトリ（data/）やログディレクトリ（logs/）が自動作成されるが、権限に注意。

.env の自動読み込み:
- デフォルトでプロジェクトルートの`.env`および`.env.local`を起動時に読み込みます（既存の OS 環境変数は保護されます）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

### .env を対話的に作る（推奨）
付属のウィザードで対話的に `.env` を作成できます:
```
python -m kabusys.config_setup
```
ウィザードは必須項目（J-Quants トークン、kabuAPI パスワード等）を促します。

### 設定の検証
作成した設定や config/*.yaml の簡易チェック:
```
python -m kabusys.validate_config
# 警告を fail として扱う場合:
python -m kabusys.validate_config --strict
```

## 使い方（実行方法）

主要なエントリポイント:
- ExecutionEngine の起動:
  - 実行スクリプト: `src/kabusys/run_execution.py`
  - 起動方法:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV による挙動:
    - `paper_trading` のときは MockBrokerClient を使用し、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可）に記録します（本番 DB と分離）。
    - `live` のときは本番 DB に対して発注が行われます。
  - PID ファイル: `data/execution.pid`（デフォルト）
  - 停止: `data/stop_requested.flag` があると起動を中止/停止します。

- Monitoring の起動:
  - 実行スクリプト: `src/kabusys/run_monitoring.py`
  - 起動方法:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず「本番 sqlite_path」を使用して監視テーブルを初期化します（監視 DB は Settings.sqlite_path）。
  - 停止フラグファイル: `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート:
  - スクリプト: `src/kabusys/tools/paper_verification_report.py`
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト `data/paper_trading.db`）。

- AI / 研究系 API はモジュール関数経由で呼び出します（例: news_nlp.score_news, regime_detector.score_regime）。これらは DuckDB 接続と target_date を受け取り、AI 呼び出しには `OPENAI_API_KEY`（または引数で api_key）を必要とします。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ポーリング秒間隔）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

## ログ
- ログは root ロガーへ StreamHandler（stdout）と日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
- デフォルトログディレクトリ: `logs/`
- setup は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に行われます。

## 停止/強制停止の仕組み
- 停止フラグ: `data/stop_requested.flag`（すべての起動スクリプトが検出して優雅に停止）
- Kill Switch（Execution 停止シグナル）: `data/kill.flag`（KillSwitch が書き込み、ExecutionEngine に停止シグナルを送る）
- `Settings.kill_flag_clear_on_start` が `1` のとき、起動時に kill.flag を自動クリアする（本番では `0` 推奨）。

## ディレクトリ構成（主要ファイル）
以下は主要モジュールの簡易説明付き構成です（`src/kabusys/` 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み（Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/               — 発注関連コンポーネント群（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文/約定監視（実装参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各モニターを束ねるエンジン
    - alert_manager.py       — 通知管理（LINE 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary 等
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + AI）
  - data/                    — 実行時に生成される（DB ファイル・フラグ・PID 等）

（具体的なサブファイルはソースを参照してください）

## 開発・デバッグのヒント
- 設定の検証: `python -m kabusys.validate_config`
- .env の初期化: `python -m kabusys.config_setup`
- 監視ループの単体テスト: MonitoringEngine は `run_once()` を提供しており、テスト用に各 Monitor を注入して1回だけ実行できます。
- AI 呼び出しは外部 API に依存するため、ユニットテストでは `_call_openai_api` 等をモックすることが想定されています。
- DuckDB のクエリは大量データを想定しているため、インデックスやクエリ範囲に注意してください。

## 注意事項 / 安全ガイド
- .env（シークレット）は Git に絶対にコミットしないでください。
- 本番モード（KABUSYS_ENV=live）での起動は慎重に：validate_config が警告を出す項目を必ず確認してください（特に LINE 通知設定や Kill Switch の設定）。
- Paper trading と本番 DB は分離されていますが、設定ミスで上書きしないよう DB パスの指定を確認してください。
- OpenAI やブローカー API のキーを外部へ漏らさないこと。

---

以上がこのコードベースの README です。詳細な実装や API の使い方は各モジュールの docstring とソースコメントを参照してください。必要であれば README にサンプル .env テンプレートや運用手順（デプロイ、systemd ユニット例等）を追加できます。どの情報を追記しますか？