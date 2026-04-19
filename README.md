# KabuSys

日本株向け自動売買・リサーチ基盤のコアライブラリ / スクリプト群です。  
このリポジトリはバックテストやペーパートレード、本番実行のためのコンポーネント（ExecutionEngine、Monitoring、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析など）を含みます。

## 概要
- 自動売買エンジン（ExecutionEngine）起動スクリプト
- システム監視（Monitoring）・Kill Switch（停止フラグ）機構
- ポートフォリオ候補選定・重み付け・ポジションサイジング・セクター制約などの純粋関数群
- DuckDB / SQLite を用いたデータ処理・ログ
- OpenAI を用いたニュース NLP（センチメント）／レジーム判定
- ペーパートレード検証レポート出力ツール
- .env ウィザード / 設定検証ツール

※ セキュリティ上の理由から .env はリポジトリに含めないでください。

## 主な機能
- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレード分離（ペーパートレードは mock broker を使用し専用 SQLite に記録）
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/MEM/DISK）、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）監視
  - Kill Switch（data/kill.flag）による ExecutionEngine 強制停止
  - アラート送信（LINE 等）用のフック（AlertManager）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重配分、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数
- 研究・分析（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL 実装）
  - 将来リターン、IC 計算、ファクター統計
- AI 周り（kabusys.ai）
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF + LLM のハイブリッド）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証ツール（validate_config.py）
  - ログ設定ユーティリティ、プロセス優先度 / CPU アフィニティ設定

## 要件（推奨）
- Python 3.10+
- 必要な Python パッケージ（代表）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を使う場合）
- SQLite は標準ライブラリで利用
- （任意）LINE 通知を使う場合は LINE Messaging API の設定

インストール例:
```
python -m pip install duckdb psutil openai PyYAML
```
（requirements ファイルがある場合はそちらを利用してください）

## セットアップ手順
1. リポジトリをクローンして、仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. 環境変数設定
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（.env.example を参考に）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` をつけると警告も失敗として扱います
5. データディレクトリ等を作成（通常スクリプトで自動作成されますが、手動で用意しておくと確実です）
   - data/
   - logs/

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant / partial / never / reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログディレクトリ、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 を推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60 秒）

自動 .env ロードはデフォルトで行われます。無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

## 使い方（主なコマンド）
- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/execution.pid（PID ファイル）が作成され、data/stop_requested.flag または data/kill.flag の存在で停止や起動制御を行います。
  - ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
- Monitoring 起動（ポーリングで監視を行う）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（秒）
  - 監視は常に本番用の sqlite_path を使用してログを保存します
- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可）
- AI / 研究機能はライブラリ関数として使用
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - 研究用関数: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns など

## 停止・強制停止
- 通常停止: 実行プロセスに対して Ctrl+C（KeyboardInterrupt）で安全に停止します。
- 強制停止（Kill Switch）:
  - 監視ロジックがトリガー条件を満たすと data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 手動で停止フラグを立てる場合は data/kill.flag に理由を記述して置くか、監視が書き込みます。
  - run_execution / run_monitoring は data/stop_requested.flag の存在でもループを抜けます（運用側停止用）。
- 起動時に kill flag を自動クリアさせたくない場合は KILL_FLAG_CLEAR_ON_START を 0 にしてください（本番推奨）。

## ログ
- 共通ロギングユーティリティ (kabusys.utils.logging_setup) を使用し、stdout とログファイル（logs/<app_name>.log、日次ローテーション）に出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用します。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等） ※詳細実装は各ファイルへ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - data/                     — 実行時に使用するファイル（data/*.db, *.pid, kill.flag など）
  - tools/
    - paper_verification_report.py

（実際のサブファイルはリポジトリ内のソースを参照してください）

## 開発・運用上の注意
- .env は Git 管理下に置かないこと（秘密情報を含む）。config_setup.py は .env を生成します。
- KABUSYS_ENV を `live` に設定する場合、LINE の通知設定や Kill Switch の挙動など本番向けガードの確認を必ず行ってください（validate_config ではいくつかの注意警告を出します）。
- DuckDB / SQLite のパスは環境変数で簡単に切り替えられるため、テスト時は別 DB を指定して本番データと分離してください。
- OpenAI API 呼び出しはコスト・レート制限に注意してください。失敗耐性は組み込まれていますが、API キーの管理は慎重に。

---

README に記載のない内部 API を利用する場合は、該当モジュールの docstring を参照してください。必要であれば、特定モジュールの使い方や API 仕様を別途ドキュメント化できます。