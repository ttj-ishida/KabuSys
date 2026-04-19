# KabuSys — README

このリポジトリは日本株自動売買システム (KabuSys) の一部実装を含みます。  
README ではプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

## プロジェクト概要
KabuSys は日本株向けの自動売買・リサーチ・監視基盤です。  
主に次を提供します。
- 市場データ / ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 実行エンジン（ExecutionEngine）と発注管理（paper/live を分離）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- AI を使ったニュース NLP（OpenAI）によるセンチメント評価・レジーム判定
- 運用・検証用ツール（設定ウィザード、設定検証、Paper Trading レポート生成など）

設計方針の一部：
- 設定は .env と環境変数で管理（自動ロード機能あり）
- DuckDB（分析用）と SQLite（監視／発注ログ用）を併用
- 本番とペーパートレードは DB を分離（paper_trading モード）

## 主な機能一覧
- 環境設定ウィザード（`kabusys.config_setup`）
- 設定検証 CLI（`kabusys.validate_config`）
- 実行エンジン起動スクリプト（`kabusys.run_execution`）
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し `data/paper_trading.db` を利用
- 監視ループ起動スクリプト（`kabusys.run_monitoring`）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- Kill Switch（`data/kill.flag`）生成・評価（`KillSwitch`）
- AI モジュール：ニュース NLP（`kabusys.ai.news_nlp`）・レジーム検出（`kabusys.ai.regime_detector`）
- リサーチ：ファクター計算 / 将来リターン / IC 等（`kabusys.research`）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ）
- ユーティリティ：ロギング設定（ログローテート）、プロセス優先度設定 等
- 運用ツール：Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）

## 前提条件（依存）
最低限の依存ライブラリ（抜粋）：
- Python 3.8+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML を検証する場合。なくても動作するが検証はスキップ）
その他、実行環境に合わせて追加パッケージや OS 権限（プロセス優先度設定など）が必要になる場合があります。

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意/設定項目（代表例）:
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化 ("1")

.env 自動ロードの優先順位: OS 環境変数 > .env.local > .env  
（プロジェクトルートが自動検出できない場合は読み込みスキップ）

## セットアップ手順（ローカルでの例）
1. リポジトリをクローン、作業ディレクトリをプロジェクトルートにする。
2. Python 仮想環境を作成して依存をインストール（例: pip install -r requirements.txt）。
   - requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストール。
3. 初期設定（.env）の作成
   - 対話式ウィザードを実行して .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（下記の例参照）。
4. 設定検証を実行:
   ```
   python -m kabusys.validate_config
   ```
   警告も含めて厳密にチェックしたい場合は `--strict` を付ける。
5. データディレクトリ作成（必要に応じて）:
   - デフォルトの DB/ログディレクトリは `data/` と `logs/`。
   - 実行時に自動作成される場合もありますが、権限等で失敗したら手動で作成。

例: 最低限の .env（参考）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

## 使い方（主なコマンド）
- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` を使用して本番 DB と分離します。
  - 実行エンジンは `data/stop_requested.flag`（あるいはプロジェクトの data 配下 stop flag）を検出すると停止シグナルを受け取ります。
  - 実行中は `data/execution.pid` に PID を書きます。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は Settings に基づき sqlite_path（監視 DB）と duckdb_path を使用します。監視は環境に関係なく本番 sqlite_path を参照します。
  - 停止フラグファイル（stop_requested.flag）を置くことでループを終了できます。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能。

- AI 機能（ライブラリ関数として使用）
  - ニュースのスコア付け:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - DuckDB 接続と target_date を用いて ai_scores テーブルを更新します。
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意: OpenAI を使う API 呼び出し機能を利用する場合、`OPENAI_API_KEY` を設定してください。API 呼び出しはリトライ・フェイルセーフロジックを含みますが、キー未設定時は例外を投げます。

## 運用上の注意
- Kill Switch:
  - 内部ロジック（`KillSwitch`）はリスク監視結果（ドローダウン／ポジション上限）に応じて `data/kill.flag` を書き、ExecutionEngine に停止指示を出します。ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` が設定されていると kill.flag を自動クリアできます（安全のため本番では `0` 推奨）。
- 停止方法:
  - ExecutionEngine や Monitoring のループは `data/stop_requested.flag`（またはそれぞれの実装パス）を作ると終了します。
- ログ:
  - ログは標準出力（stdout）と日次ローテートファイル（`logs/<app_name>.log`）に出力します。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度:
  - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。権限不足などで失敗する場合はワーニングが出ます。

## ディレクトリ構成（主なファイル）
下記はリポジトリ内 `src/kabusys/` 以下の主要ファイル・モジュールです（本 README の作成時点で提供されているものを抜粋）。

- __init__.py
  - パッケージの基本情報（バージョンなど）
- config.py
  - Settings クラス: 環境変数 / .env の読み込み・アクセスラッパー
- config_setup.py
  - .env を対話式に作成するウィザード
- validate_config.py
  - .env と config/*.yaml の簡易検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の DB 分離、PID/STOP 管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- monitoring/
  - monitoring_db.py : SQLite 用のテーブル初期化 + 永続化層（MonitoringDB）
  - system_monitor.py : CPU/メモリ/ディスク/データ鮮度・プロセス監視
  - trade_monitor.py（参照実装あり）: 発注／約定の監視（コードベースに存在）
  - risk_monitor.py : ドローダウン・ポジション数の監視
  - monitoring_engine.py : 各 Monitor を束ねてポーリングするエンジン
  - kill_switch.py : kill.flag 書き込み・評価ロジック
  - alert_manager.py : アラート送信管理（LINE など、実装参照）
- ai/
  - news_nlp.py : OpenAI を使ったニュースセンチメント評価（ai_scores への書き込み）
  - regime_detector.py : MA + マクロニュースで市場レジーム判定
- research/
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py : 将来リターン、IC、統計サマリ等
- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数計算（単元丸め・リスク制限・集計スケールダウン）
  - risk_adjustment.py : セクター制限、レジーム乗数
- tools/
  - paper_verification_report.py : Paper Trading データから検証レポート生成
- utils/
  - logging_setup.py : ロギング（コンソール + 日次ローテーション）
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

（実行エンジン本体やブローカークライアント等は別ファイル群に分かれており、上記は主要なユーティリティ・監視・リサーチ領域の抜粋です）

## 開発者向けメモ
- DuckDB 接続は分析処理（research / ai）で使用します。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- SQLite（監視 DB / paper_trading DB）は軽量永続層として使用。`monitoring_db.init_monitoring_db` で必要テーブルが自動作成されます（マイグレーションロジックあり）。
- AI 呼び出し部分は外部 API（OpenAI）に依存します。テスト時は内部の呼び出し関数をモックしてください（モジュール内に差し替え可能なヘルパー実装あり）。
- 設定周りは .env のパース実装がやや堅牢化されています（クォート、エクスポート形式、コメント処理などを考慮）。

---

以上がこのコードベースの概要と使い方です。運用やデプロイの際は本 README をベースに .env の値（特に API トークン・本番フラグ・kill flag の取り扱い）を慎重に設定してください。必要であれば README に追加したいコマンドや設定例の要望を教えてください。