# KabuSys

日本株向け自動売買システム（ライト版）  
このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注実行 → 監視・アラートまでのワークフローを想定したモジュール群を含みます。主要コンポーネントとして ExecutionEngine（発注エンジン）、Monitoring（監視/Kill Switch/アラート）、AI 支援（ニュース NLP / レジーム判定）、Research（ファクター計算）、Portfolio（選定・配分・サイズ決定）などを提供します。

Version: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 初期設定（.env ウィザード）
  - 設定検証
  - 実行エンジン（Execution）
  - 監視（Monitoring）
  - 各種ツール（レポート等）
- 主要環境変数（簡易一覧）
- 停止 / フラグファイル
- ディレクトリ構成（要約）

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。DuckDB/SQLite によるデータ保持、kabuステーション API（実取引）や MockBroker（ペーパートレード）に対する発注処理、監視ループでの健全性チェック・Kill Switch、OpenAI を用いたニュースセンチメント評価やレジーム検出等を備えています。

設計上のポイント:
- 環境変数 / .env による設定管理（自動ロード機能あり）
- production と paper_trading を明確に分離（Paper Trading は別 SQLite ファイルに記録）
- モジュールはできるだけ純粋関数 / 副作用を最小化する設計
- フェイルセーフ: APIや外部失敗時は例外で停止させずログを残して可能な限り継続

---

## 機能一覧

- Execution（発注）
  - BrokerClientFactory により本番 / モックブローカーを切替
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - Paper Trading（仮想発注）時は専用 DB に記録

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常などの検出（コード中に実装参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 重大リスク検知時に停止フラグを立てる
  - MonitoringEngine: 各 Monitor の定期実行とアラート発行

- AI（OpenAI）
  - news_nlp: raw_news から銘柄別センチメントを取得して ai_scores に保存
  - regime_detector: ETF MA とマクロニュースを組み合わせて市場レジーム判定

- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量解析（IC 等）
  - Portfolio コンストラクション（候補選定、等金額・スコア加重、リスク調整、ポジションサイズ計算）

- ユーティリティ
  - ログ設定（コンソール + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード & 設定検証 CLI
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順（ローカル開発用）

前提:
- Python 3.10 以上（typing の一部注釈に union | を使用）
- Git 等

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   本リポジトリに requirements.txt がない場合は最低限以下を入れてください:
   ```
   pip install duckdb psutil openai pyyaml
   ```
   - sqlite3 は標準ライブラリです。
   - PyYAML は設定ファイル（config/*.yaml）の検証に使用します（任意）。

4. .env 作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークンや KABU_API_PASSWORD 等を設定してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告もエラー扱いになります。

6. データディレクトリ作成（必要に応じて）
   デフォルトでは `data/` 下に DB や PID/flag を置きます。権限や配置を確認してください。

---

## 使い方

### 1) 初期設定（.env ウィザード）
```
python -m kabusys.config_setup
```
- .env を対話式に生成/更新します。秘密値（トークン等）はマスク表示されます。
- 生成後、`python -m kabusys.validate_config` で検証することを推奨します。

### 2) 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```
- 不足している必須環境変数や config/*.yaml の不足・パースエラーを検出します。

### 3) 実行エンジン（Execution）
本番 / ペーパートレードを切り替えるには環境変数 `KABUSYS_ENV` を設定します。例:
- ペーパートレード:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録され、本番 SQLite と分離されます。

- 本番:
  ```
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```
実行中は `data/execution.pid`（デフォルト）に PID を保存し、停止はフラグファイル経由で行います。

### 4) 監視（Monitoring）
監視ループを起動:
```
python -m kabusys.run_monitoring
```
- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
- system_monitor は DB のパスを Settings.sqlite_path（デフォルト: data/monitoring.db）で参照します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意。

### 5) Paper Trading 検証レポート
期間を指定してレポートを生成できます:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
- デフォルト DB は `data/paper_trading.db`。`--db` で別パス指定可能。

### 6) AI モジュール
- ニュースセンチメントやレジーム判定は OpenAI API を使用します。環境変数 `OPENAI_API_KEY` を設定してください。
- 関数呼び出し（モジュール内の public API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルト値含む）:
- KABUSYS_ENV: development | paper_trading | live （default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（例: DEBUG, INFO, WARNING）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動、default: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（注意: 本番での自動クリアは推奨されません）

自動ロードについて:
- プロジェクトルートに `.env` / `.env.local` があれば実行時に自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 停止 / フラグファイル

- Execution 停止シグナル:
  - data/kill.flag — KillSwitch により生成される停止フラグ。ExecutionEngine は起動中にこのファイルを検知して停止します。
  - KillSwitch は理由テキストをフラグに書き込みます。
- 手動による強制停止:
  - data/stop_requested.flag — run_monitoring / run_execution などのスクリプトはこのファイルの存在を確認してループを終了します。
- PID ファイル:
  - data/execution.pid — ExecutionEngine 起動時に書き込まれる PID（設定で変更可能）

---

## トラブルシューティング（簡易）

- PyYAML がインストールされていない場合、`validate_config` は YAML の検証をスキップして警告を出します。インストールは `pip install pyyaml`。
- ログディレクトリの作成に失敗するとコンソール出力のみになります（警告ログあり）。
- DuckDB/SQLite のパスの親ディレクトリが存在しない場合、検証は警告します。必要なディレクトリを作成してください。
- OpenAI API 呼び出しが失敗しても、AI モジュールはフェイルセーフ（多くのケースでスコアを 0 にフォールバック）を実装していますが、API キーの設定は必要です。

---

## ディレクトリ構成（概要）

以下は主要ファイル/モジュールの簡易ツリーと説明（src/kabusys を起点）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py        — Monitoring 起動スクリプト（ポーリングループ）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル/CRUD）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文監視（滞留/約定異常 等）※参照コードあり
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグファイルによる停止シグナル
    - monitoring_engine.py   — Monitor を束ねる実行ループ
    - alert_manager.py       —（通知管理、アラート送信）※コード参照
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — Broker クライアント生成（実/モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・簡易スコアソート
    - position_sizing.py     — 発注株数計算（単位丸め、キャップ）
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — IC / 将来リターン 等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄別センチメント算出
    - regime_detector.py     — レジーム判定（ETF MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py       — ロギング初期化（stdout + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

- data/                      — デフォルト DB / flag / pid が置かれる想定ディレクトリ（運用時に作成）
- logs/                      — ログ出力先（デフォルト）

---

この README は主要な利用方法と構成をまとめたものです。詳細な実装や各モジュールの使い方はソースコードの docstring / 関数コメントを参照してください。追加で README.md に追記したい内容や、特定機能の詳しい使い方（例: ExecutionEngine のパラメータ、RiskManager の設定方法など）があれば教えてください。