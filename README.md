# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはコードベース（src/kabusys/*.py）を元に作成されています。セットアップ、主要機能、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤です。以下の主要機能を含みます：

- 注文管理・発注エンジン（ExecutionEngine）  
  - 本番 / ペーパートレード（分離された DB）に対応
- 監視（Monitoring）  
  - システム状態（CPU・メモリ・ディスク）、プロセス存否、データ鮮度、注文滞留・約定異常、ドローダウン監視
- リスク管理（RiskManager、Kill Switch）  
  - ドローダウン・ポジション上限で停止シグナルを発行
- ポートフォリオ構築（選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析、IC計算）
- AI 支援（ニュースセンチメント、レジーム判定、OpenAI を利用）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

コードは原則として「DB 接続を受け取る純粋関数」と「永続化層（SQLite / DuckDB）」で分離されており、テストしやすい構成になっています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: python -m kabusys.validate_config
- Execution エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
- Monitoring（監視）起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- Kill Switch（data/kill.flag による停止）と KillSwitch クラスによる評価
- RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine による包括的監視と通知
- portfolio.*：銘柄選定、重み計算、セクター上限適用、ポジションサイズ計算
- research.*：ファクター計算（モメンタム・ボラティリティ・バリュー）、IC、統計サマリ
- ai.news_nlp：ニュース記事を OpenAI でスコアリングして ai_scores テーブルへ書き込み
- ai.regime_detector：MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- tools.paper_verification_report：ペーパートレードの検証レポート生成

---

## 前提・依存関係（推奨）

- Python 3.10+（標準ライブラリの型構文を使用）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML のパース検証を行う場合に必要）
- SQLite は Python 標準に含まれます

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install duckdb psutil openai pyyaml
```

※ 実際の requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローンしワークディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数設定
   - 対話的に .env を作る:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` を生成できます（.env は絶対に Git にコミットしないでください）。
   - 主要な必須変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - デフォルト値（設定がない場合の参照先/ファイル）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag

5. 設定検証（起動前に推奨）:
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

6. DB や data ディレクトリは自動作成される場合がありますが、権限等を事前に確認してください。

---

## 使い方（起動・運用）

基本はモジュール単位で起動します。

- ExecutionEngine 起動（発注エンジン）
  - 本番 / ペーパートレードは KABUSYS_ENV に依存:
    - paper_trading: Mock ブローカーを使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - 実行を停止させるにはプロセスに SIGINT（Ctrl+C）を送るか、停止フラグファイルを作成します：
      ```
      touch data/stop_requested.flag
      ```
    - 実行中は pid が data/execution.pid に書き込まれます。run_monitoring や SystemMonitor はこの pid を参照してプロセス生存を判断します。

- Monitoring（監視ループ）起動
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔（秒）を環境変数で変更:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。0 以下や不正な値は無視されデフォルトにフォールバックします。
  - 監視は Settings の sqlite_path（monitoring DB）を使って監視データを永続化します。Monitoring は KABUSYS_ENV に関係なく production sqlite_path を参照します（実装上の設計）。

- Kill Switch（外部から Execution を止める）
  - KillSwitch は条件（ドローダウン・ポジション上限など）を満たした際に `data/kill.flag` を書き込みます。ExecutionEngine は通常このファイルを検出して停止します。
  - 手動で Kill を解除する場合はファイルを削除します（もしくは設定で起動時に自動クリアするオプションを有効化できます）:
    ```
    rm -f data/kill.flag
    ```

- ペーパートレード検証レポート生成
  - ペーパートレード DB（デフォルト: data/paper_trading.db）を解析して PASS/FAIL 判定を行います:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - `--db` オプションで DB を指定するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を使えます。

- AI：ニューススコアリング / レジーム判定
  - news_nlp.score_news: DuckDB 接続と target_date を与えて実行。環境変数 OPENAI_API_KEY を設定するか、引数で API キーを与えます。
  - regime_detector.score_regime: DuckDB 接続と target_date を与えて実行。OpenAI を使うため OPENAI_API_KEY が必要です（API エラー時はフェイルセーフで継続します）。
  - 例（簡易的に Python から呼ぶ）:
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10))  # OPENAI_API_KEY を環境変数に設定しておく
    ```

---

## 主要な環境変数一覧（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- KILL_FLAG_PATH: Kill flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" にするとクリア、デフォルト "0"）

---

## DB / マイグレーションについて

- monitoring_db.init_monitoring_db(conn) によって必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）およびインデックスが冪等的に作成されます。
- 既存 DB への軽微なマイグレーション（例: dashboard に peak_value カラム追加、trade_logs に latency_ms カラム追加）も行われます。
- Paper Trading は本番監視 DB（monitoring.db）とは別ファイルに保存されます（PAPER_TRADING_SQLITE_PATH）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — レジーム判定（MA + マクロニュース + OpenAI）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           — （アラート送信はここで実装）
  - execution/                   — 発注関連（OrderManager, ExecutionEngine, BrokerFactory 等）
  - data/                        — データ取り扱い（DuckDB パイプライン等）
  - utils/
    - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ

※ 実際の細かい実装（execution.* や data.* の詳細）もリポジトリに含まれます。上記は主要な機能別のファイル名一覧です。

---

## 運用上の注意

- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにもその旨が明記されています）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch 関連設定を慎重に行ってください（validate_config が注意喚起します）。
- OpenAI を使う機能は API コスト・レート制限に注意してください。実行はバックオフやリトライが実装されていますが、費用は発生します。
- Monitoring は本番の monitoring DB を参照します。テスト用に分離したい場合はファイルパスを変更してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従って無限ループ動作します。停止はデフォルトで Ctrl+C または data/stop_requested.flag により可能です。

---

## よく使うコマンド一覧

- 環境ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追加したい具体的な運用手順（例: systemd ユニット例、Docker コンテナ化、CI/CD フロー、より詳細な設定例等）があれば教えてください。必要に応じて追記・テンプレート提供します。