# KabuSys

日本株自動売買システムのパッケージ（README）。このドキュメントはリポジトリ内の主要スクリプト・モジュールの使い方、設定、ディレクトリ構成を日本語でまとめたものです。

注意: 実行前に必ず .env を作成し、`python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主要な機能群は以下の通りです。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理の実装
- 監視（Monitoring）：プロセス・システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio）：候補選定、重み算出、ポジションサイズ計算、セクター制限
- 研究（Research）：ファクター計算・特徴量探索
- AI 支援（AI）：ニュースの NLP によるセンチメントスコアリング、レジーム判定（OpenAI）
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定、DB 初期化など
- ツール：ペーパートレード検証レポート生成等

設計方針の例:
- 本番データとペーパートレード用 DB を分離する設計
- ルックアヘッドバイアスを避ける（日付参照の扱いに配慮）
- フェイルセーフ（外部 API 失敗時は安全なフォールバック動作）
- ログは統一的に設定（コンソール + 日次ローテートファイル）

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み・対話式ウィザード（config_setup）
  - 設定の事前検証 CLI（validate_config）
- 実行
  - ExecutionEngine を起動する run_execution.py（本番 / paper_trading に対応）
  - paper_trading の場合は MockBrokerClient を使用し、専用 DB に記録
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行する run_monitoring.py
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - stop_requested.flag による安全停止
- ポートフォリオ構築
  - 候補選別、等配分 / スコア加重配分、リスクベース発注量計算、セクター制限
- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュース記事を OpenAI でスコアリングして ai_scores に書き込む（news_nlp.score_news）
  - マクロニュース + ETF MA を使った市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順

1. リポジトリをチェックアウトし、必要な Python 環境を作成してください（Python 3.9+ を想定）。

2. 依存パッケージをインストール（例: pip）  
   requirements.txt が無い場合は、使用されるライブラリに合わせてインストールしてください。主な外部依存:
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（config の検証や生成を行う場合）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成する  
   対話式ウィザードを使うと簡単です（プロジェクトルートで実行）:
   ```
   python -m kabusys.config_setup
   ```
   手動で作成する場合は `.env.example` を参考に必要な環境変数（特に必須の `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）を設定してください。

4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / フラグパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / Kill フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   これらは起動時に自動作成されることもありますが、事前にディレクトリを作ると権限問題を回避できます:
   ```
   mkdir -p data logs
   ```

6. ログディレクトリ  
   デフォルトは `logs/`。環境変数 `LOG_DIR` で変更可。ログレベルは `LOG_LEVEL`（DEBUG/INFO/...）で制御。

---

## 使い方

### 基本的な起動

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - 監視プロセスは常に本番用の sqlite (`Settings.sqlite_path`, デフォルト `data/monitoring.db`) を使用します（KABUSYS_ENV に関わらず）。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するとループを終了します。

- 実行エンジンを起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すればエンジンは起動せず終了します。
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するか、監視側の Kill Switch で `data/kill.flag` が作成されるとエンジンに停止シグナルを送ります。
  - 実行時 PID は `data/execution.pid` に記録されます。

### .env・設定関連の主な環境変数（要確認）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルト値あり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（default: INFO）
- LOG_DIR — ログ出力ディレクトリ（default: logs）
- OPENAI_API_KEY — OpenAI を利用する機能に必要
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）

Kill Switch / フラグ:
- KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効。production では推奨しない）

### AI 機能の利用

- ニュース NLP スコアリング:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数 or 環境変数 `OPENAI_API_KEY` から取得
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

API 呼び出しはレート制限や一時障害に対してリトライ処理がありますが、API キーが未設定だと例外になります。

### ツール

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db` を参照します。

---

## 動作停止・フラグの取り扱い

- Graceful stop for monitors/engines:
  - `data/stop_requested.flag` を作成すると、run_monitoring / run_execution のループは検知して終了します。
- Kill Switch:
  - Monitoring の各チェック（ドローダウン・ポジション上限等）で条件該当すると `data/kill.flag` に理由を書き込みます。
  - ExecutionEngine はこの `kill.flag` を検知して安全に停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に `kill.flag` を自動クリアします（本番では通常 0 を推奨）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env 読み込み）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ (stdout + 日次ローテート)
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （省略されたが）注文監視
    - risk_monitor.py       — ドローダウン / ポジション数監視
    - kill_switch.py        — kill.flag の管理
    - monitoring_engine.py  — モニターの統合と通知
    - alert_manager.py      — （アラート送信：LINE 等）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py     — BrokerClient の生成（Mock 本番切替）
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
    - news_nlp.py           — OpenAI を使ったニュースセンチメント
    - regime_detector.py    — 市場レジーム判定

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 設計上の注意・運用上の注意

- 本番用 DB とペーパートレード DB は設計上分離されています。paper_trading 環境で誤って本番 DB を上書きしないよう設定を確認してください。
- KABUSYS_ENV=live のときは特に注意して設定を行ってください（validate_config はいくつかのガードを出します）。
- OpenAI や外部 API の利用には API キーとコスト管理が必要です。API 失敗時のフォールバック動作は設計されていますが、頻繁な失敗はシステム性能に影響します。
- ログは logs/<app_name>.log に日次ローテート保存されます。ログディレクトリの権限・ディスク容量を監視してください。
- プロセス優先度設定（set_process_priority）は OS の権限に依存します。権限不足時は警告のみで継続します。

---

## よく使うコマンドまとめ

- .env の対話式作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README は随時更新してください。ソースコード内のドキュメンテーション文字列（docstring）にも多くの実装注記が含まれています。開発・運用時は該当モジュールの docstring を参照することを推奨します。