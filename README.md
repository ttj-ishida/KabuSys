# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ用 README（日本語）

この README は、提供されたコードベースに基づいて作成したドキュメントです。プロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。主な機能には以下が含まれます。

- 発注エンジン（ExecutionEngine）と発注管理（OrderManager / RiskManager / Reconciler）
- 監視サブシステム（System/Trade/Risk Monitor）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析
- Paper Trading 用のレポート生成ツール
- AI を使ったニュースの NLP スコアリング／市場レジーム判定（OpenAI API 利用）
- 環境設定ウィザード、設定検証ツール、監視用データ永続化（SQLite）

設計方針として、実運用時の安全性（ペーパートレードと本番 DB 分離、Kill Switch、フェイルセーフ）やルックアヘッドバイアス防止（日時の扱い）などに配慮されています。

---

## 主な機能一覧

- 実行・監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切り替え）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - AlertManager: LINE Messaging API による通知（設定がなければ送信はスキップ）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- 研究用
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュース記事から銘柄別センチメントを算出して ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して市場レジームを判定
- ユーティリティ
  - tools/paper_verification_report.py: Paper Trading DB を使った通し検証レポート生成

---

## 前提・依存関係

- Python 3.10 以上（型ヒントに `X | Y` 形式を使用）
- 必須パッケージ（一部は実行する機能に応じて必要）:
  - duckdb
  - psutil
  - requests
  - openai
- 任意（YAML の検証を行う場合）:
  - PyYAML
- SQLite（標準ライブラリ）を使用
- ネットワークアクセスが必要な機能:
  - OpenAI API を使う機能（news_nlp / regime_detector）: 環境変数 OPENAI_API_KEY または引数で API キーを指定
  - LINE 通知: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai
# YAML 検証をするなら:
pip install pyyaml
```

---

## セットアップ手順

1. リポジトリを取得しプロジェクトルートへ移動。

2. 仮想環境の作成（推奨）と依存ライブラリのインストール（上記参照）。

3. .env ファイルの作成
   - 対話式ウィザードを実行して .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信を有効にする場合）
     - LOG_LEVEL（DEBUG/INFO/...）

   - 自動ロード:
     - プロジェクトルートに .env を置くと、モジュール読み込み時に `.env` / `.env.local` が自動で環境変数に反映されます。
     - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする:
   python -m kabusys.validate_config --strict
   ```

5. データフォルダの準備
   - デフォルトで使用されるファイルは `data/` 配下に作成されます。必要に応じてディレクトリを作っておいてください（多くのコードは起動時に自動作成します）。

---

## 使い方（起動 / 実行コマンド例）

- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - run_execution は `data/stop_requested.flag` の存在を確認し、フラグがあると起動を中止します。実行中もフラグを監視して安全に停止します。
  - 起動時に `data/execution.pid` が作成され、プロセスの存在を SystemMonitor がチェックします。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` を設定すると上書き可能（例: `MONITOR_POLL_INTERVAL=30`）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は `data/stop_requested.flag` を作成することで行います。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連
  - news_nlp（銘柄別ニュースセンチメント）や regime_detector（市場レジーム判定）は OpenAI API を利用します。環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡してください。
  - 失敗時のフェイルセーフが組み込まれており、API エラー時は安全なデフォルト（例: 0.0）で続行します。

- .env 生成・検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 主要な挙動の注意点

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、発注系は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用する設計です。本番 DB とデータを混ぜないようになっています。

- Kill Switch / Stop フラグ
  - KillSwitch は `data/kill.flag`（Settings.kill_flag_path）を書き込むことで ExecutionEngine 停止を指示します。run_execution / monitoring はフラグファイルや stop_requested.flag を見て停止動作を行います。
  - Settings で `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なため `0` を推奨します。

- process priority / CPU affinity
  - 起動時にプロセス優先度を "high" に設定します（psutil を利用）。権限不足や未対応 OS の場合は警告を出してスキップします。

- DuckDB / SQLite
  - 分析用に DuckDB を使用（DUCKDB_PATH）。監視ログは SQLite（SQLITE_PATH）に記録されます。必要に応じてパスを .env で変更してください。

- 自動環境読み込み
  - モジュール import 時にプロジェクトルートから `.env` / `.env.local` を自動読み込みします（既存 OS 環境変数は保護）。この挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` 配下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（OrderManager 等）※詳細実装は省略
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化と永続化ラッパ
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (上記はテンプレート/生成スクリプトで用意。validate_config が存在チェックを行います)

- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用デフォルト)
  - execution.pid / stop_requested.flag / kill.flag などのランタイムファイル

---

## 主要テーブル（監視用 SQLite の概要）

monitoring_db.init_monitoring_db によるテーブル（主なもの）

- system_status: CPU/メモリ/ディスク/プロセス状態の時系列
- trade_logs: 発注・約定ログ（latency_ms カラムあり）
- positions: 現在のポジション
- risk_logs: リスク関連のイベント（DRAWDOWN_ALERT, STALE_ORDER 等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

---

## トラブルシューティング / よくある質問

- 起動中にプロセス優先度の設定で警告が出る
  - OS 権限やプラットフォームの制約により設定ができない場合は警告が出力されますが処理自体は継続します。

- OpenAI 関連が動作しない
  - `OPENAI_API_KEY` を設定してください。ネットワークエラーや API レート制限は内蔵のリトライ処理で対応しますが、完全に停止する場合はログを確認してください。

- LINE 通知が来ない
  - `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` が設定されていることを確認してください。設定が空の場合、AlertManager は送信をスキップします。

- Paper Trading のレポートで DB が見つからない
  - `PAPER_TRADING_SQLITE_PATH` か `--db` オプションで正しいパスを指定してください。

---

## 開発メモ / 補足

- 設定ファイル（.env）には機密情報が含まれます。絶対に Git などにコミットしないでください（config_setup でもその旨を注意書きしています）。
- YAML のパース確認は PyYAML がインストールされている場合のみ行われます。インストールされていない場合は警告が出て検証をスキップします。
- DuckDB を利用した研究/ファクター計算モジュールは、prices_daily / raw_financials / raw_news 等のテーブルが前提です。これらのデータ投入は別途実装が必要です。

---

README の内容はコードベースの主要箇所を参照してまとめています。より詳細な開発者向け情報（ExecutionEngine の内部、Broker クライアント実装、データインジェストパイプライン等）は該当ソースを参照してください。必要であれば各サブモジュールごとの詳細ドキュメント（API、設定例、シーケンス図など）を追加で作成します。