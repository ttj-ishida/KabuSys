# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
この README はリポジトリ内の主要スクリプト／モジュールから作成しています。起動方法や設定、主要コンポーネントの振る舞いを日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な役割は以下の通りです。

- 注文実行（ExecutionEngine）：ブローカークライアントを経由して注文を発行・管理
- 監視（Monitoring）：システム状態、注文状態、リスクを定期監視しアラートや停止フラグを発行
- ポートフォリオ構築：シグナルに基づく銘柄選定・重み付け・ポジションサイジング
- リサーチ（Research）：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：ニュースの NLP（OpenAI）を用いたセンチメント評価、レジーム判定
- 各種ユーティリティ：設定ウィザード、設定検証、ログ設定など

設計上のポイント：
- 本番用データベースは DuckDB（分析用）と SQLite（監視・履歴用）を使用
- Paper Trading（模擬発注）では本番 DB と分離した専用 SQLite ファイルを使用
- 環境変数／.env による設定管理（config_setup/wizard と validate_config を提供）
- Kill Switch（`data/kill.flag`）や stop flag（`data/stop_requested.flag`）による安全停止メカニズム

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine の起動（`python -m kabusys.run_execution`）
  - KABUSYS_ENV=`paper_trading` の場合は MockBroker を使用して `data/paper_trading.db` に記録
  - プロセス優先度を `high` に設定
  - 停止フラグ検出で安全停止

- run_monitoring.py
  - SystemMonitor ポーリングループ起動（`python -m kabusys.run_monitoring`）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き（デフォルト 60 秒）
  - 監視ログは SQLite（`SQLITE_PATH`）へ永続化

- monitoring モジュール
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出
  - trade_monitor: 発注ログの監視（滞留注文・約定異常など）
  - risk_monitor: ドローダウン・ポジション上限監視（ダッシュボード更新／risk_logs へ記録）
  - kill_switch: 条件を満たすと `data/kill.flag` を書き込み実行エンジン停止をトリガー
  - monitoring_db: 必要テーブルの初期化・マイグレーション・読み書き API

- portfolio モジュール
  - 銘柄選定、等重／スコア加重の重み計算、セクター制約適用、ポジションサイズ算出（単元株丸め等）

- research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー等（DuckDB を利用）

- ai モジュール
  - news_nlp: OpenAI を使ったニュースセンチメントスコア算出と ai_scores テーブルへの書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を算出・永続化

- tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定の検証レポートを生成

- 設定・ユーティリティ
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: .env および config/*.yaml の起動前検証
  - utils.logging_setup: 統一的なログ設定（コンソール + 日次ローテーションファイル）
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定（psutil 使用）

---

## 動作要件（推奨）

- Python 3.10+
- SQLite（標準ライブラリに含まれます）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の内容検証を行う場合）
- ネットワーク接続（OpenAI を使用する場合）

依存はプロジェクトに requirements.txt があればそれを使ってください。無い場合の最低インストール例:

pip install duckdb psutil openai PyYAML

（バージョンは用途や環境に合わせて指定してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または最低限:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（例は下記）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必須環境変数が整っているか、DB パスの親ディレクトリが存在するか等をチェックします。
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリ作成（自動で作られることも多いですが念のため）
   - mkdir -p data logs

7. OpenAI や Broker など外部サービス用の設定
   - OpenAI を使う機能を動かすには `OPENAI_API_KEY` を .env に設定してください
   - ブローカー連携は `KABU_API_PASSWORD` 等を設定してください

---

### 代表的な .env の例

（config_setup を使うと自動生成されます。セキュリティのため .env は Git にコミットしないでください）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development          # development | paper_trading | live
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

必要なもの:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）

Paper Trading の専用 DB を使う場合:
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant | partial | never | reject

監視ポーリング間隔（秒）:
- MONITOR_POLL_INTERVAL（default: 60）

---

## 使い方（起動方法と主要コマンド）

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- ExecutionEngine（注文実行エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）へ記録
    - プロセス優先度を High に設定
    - 起動時に `data/stop_requested.flag` が既に存在する場合は起動せず終了
    - 実行中に `data/stop_requested.flag` を検知すると Engine.stop() を呼んで安全停止

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() をポーリング（デフォルト 60 秒）
    - 監視ログは `SQLITE_PATH` （デフォルト `data/monitoring.db`）へ永続化
    - `data/stop_requested.flag` を検出するとループを抜けて終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: コンソールに集計レポートと PASS/FAIL 判定を表示

- AI 機能（ニュース NLP / レジーム判定）
  - ai モジュールは OpenAI API を利用します。`OPENAI_API_KEY` を環境変数または引数で指定して実行します。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す（スクリプトは提供されていないため、スクリプト化は任意）

---

## 停止・安全装置（Kill Switch / stop flag）

- stop flag
  - 実行スクリプト（run_execution / run_monitoring）は `data/stop_requested.flag` を監視します。
  - このファイルを作成すると（中身は任意）実行中のプロセスは検知して安全に停止します。

- kill.flag（Kill Switch）
  - 監視モジュール（KillSwitch）は条件（例: ドローダウン超過、ポジション上限超過）を満たすと `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時や監視時にこのフラグをチェックし、存在する場合は起動抑止または停止します。
  - 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアしない）です。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要なディレクトリ／ファイル構成例（`src/kabusys` 配下）：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env ローダーと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (実装があれば)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に生成されることが多い（logs, sqlite, duckdb 等）

注：上記はコードベースから抽出した主要モジュールです。実際のファイル数はリポジトリ内の全ファイルに依存します。

---

## 注意点 / 運用時の留意事項

- 環境変数の管理
  - .env は機密情報（API キーやパスワード）を含むため Git にコミットしないでください。
  - validate_config により未設定の必須変数を起動前に検出できます。

- Paper Trading の分離
  - Paper Trading（`KABUSYS_ENV=paper_trading`）では `paper_sqlite_path` を使用して本番監視 DB から分離して動作します。実データと混ざらないよう設計されています。

- OpenAI API 呼び出し
  - AI モジュールは OpenAI の呼び出しでリトライやエラー処理を行いますが、API キーの料金やレート制限に注意してください。
  - レスポンスのバリデーションを行い、不正な出力は安全にスキップします。

- ロギング
  - logs/<app_name>.log に日次ローテーションでログが保存されます（デフォルト `logs/`、30 日保持）
  - ログディレクトリ作成に失敗した場合はコンソールのみの出力になります

- 権限・優先度設定
  - process_priority は psutil を使います。OS や権限により設定に失敗する場合があるため、警告ログが出ますがそこからの自動回復はありません。

---

## 付録：よく使うコマンドまとめ

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に「セットアップのより詳細な手順」「運用フロー（デプロイ・再起動・監視体制）」「config/*.yaml のフォーマット例」などを追記できます。どの項目を詳しく書きたいか教えてください。