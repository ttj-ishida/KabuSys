# KabuSys

日本株向け自動売買システムのコンポーネント集です（ライブラリ＋実行スクリプト）。  
この README はリポジトリ内の主要モジュールから生成された情報に基づき、セットアップと利用方法を日本語でまとめたものです。

注意: .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine）とそれを支えるブローカークライアント層
- 監視（Monitoring）機能：システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限など）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI を利用したニュース NLP（OpenAI API によるセンチメント評価）および市場レジーム検出
- 各種ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証など）
- Paper Trading（検証）用のレポート生成スクリプト

設計方針として、実運用での安全性（エラー時のフェイルセーフ、ログ・監視・Kill Switch）と、研究用途における DuckDB ベースのデータ処理を重視しています。

---

## 主な機能一覧

- 設定関連
  - .env 対話式作成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
  - 自動 .env ロード（プロジェクトルートを検出して `.env` / `.env.local` を読み込み、環境変数を設定）

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切替）
    - paper_trading 時は MockBrokerClient を用い、専用 SQLite（data/paper_trading.db など）へ書き込む
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可能）

- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス存在チェック
  - TradeMonitor: 注文滞留（stale）・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション数上限検出、ダッシュボード更新
  - KillSwitch: 条件達成時に data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite を用いた監視ログ永続化（テーブル作成・マイグレーションを含む）
  - MonitoringEngine: 上記を束ねてポーリング・通知（AlertManager 経由）

- ポートフォリオ構築（portfolio）
  - 候補選定（スコア順、signal_rank でタイブレーク）
  - 重み付け（等金額、スコア加重）
  - セクター上限適用
  - ポジションサイズ計算（単元丸め、リスクベース／重みベース、aggregate cap のスケールダウン）

- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー

- AI（openai）
  - ニュースセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API を利用（gpt-4o-mini を想定）

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等の指標）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてワークディレクトリへ移動。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # POSIX
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使用）
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML（config/ *.yaml のパース検証に使用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数を準備する
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に手動で `.env` を作成してください（`.env` は Git 管理外にすること）。

   自動ロード:
   - モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告もエラー扱い
   ```

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch が書き込むフラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1、デフォルト: 0）

（その他、monitoring 関連の閾値やパラメータも環境変数で上書き可能です）

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor 単体）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` が存在するとループは終了します。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENVに関わらず）。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ完全分離して記録します。
  - 起動時に `data/stop_requested.flag` があると起動せずに終了します。
  - 実行中に停止させたい場合は `data/stop_requested.flag` を作成（または Kill Switch により `data/kill.flag` が生成される）してください。
  - ExecutionEngine は起動時に PID を `data/execution.pid` に書きます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
  - レポートは稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を表示し PASS/FAIL を判定します。

- AI 関連（Python API）
  - ニュースセンチメント:
    ```python
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - 市場レジーム:
    ```python
    from kabusys.ai.regime_detector import score_regime
    count = score_regime(conn, target_date, api_key="sk-...")
    ```
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数でも指定可能。

---

## 実運用の注意点

- .env に機密情報（API キー等）を保存する場合は適切に管理し、絶対にリポジトリに含めないでください。
- KABUSYS_ENV=live の場合は特に慎重に設定を確認してください（validate_config は live 時に追加警告を出します）。
- Kill Switch（data/kill.flag）や stop flag（data/stop_requested.flag）による停止メカニズムを理解しておくこと。`KILL_FLAG_CLEAR_ON_START=1` は本番での自動クリアが行われるため危険です（デフォルトは 0）。
- OpenAI を利用する機能は API 利用料が発生します。API のエラーに対してはリトライやフォールバック（0 や空処理）を入れているため致命的にはなりにくい設計ですが、運用時にはレート制限やコストに留意してください。
- psutil を使ったプロセス優先度・CPU affinity 操作は OS 権限やプラットフォーム差異の影響を受けます。set_process_priority は失敗しても警告でスキップします。

---

## ディレクトリ構成

以下はリポジトリ内の主要なファイル・ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定（LLM + MA200 合成）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信処理をまとめる想定）
  - execution/                — Execution エンジン関連（OrderManager 等）
    - (order_manager.py, order_repository.py, execution_engine.py, broker_factory.py, ...)
  - data/ (実行時に生成される)
    - monitoring.db (default SQLite)
    - kabusys.duckdb (default DuckDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

（上記は抜粋です。実際のツリーはプロジェクト全体を確認してください）

---

## 開発・デバッグのヒント

- ログレベルは `LOG_LEVEL` 環境変数で変更できます（DEBUG/INFO/...）。
- config/ フォルダ内の YAML は PyYAML がインストールされていると validate_config によりパース検証されます。
- DuckDB による研究処理は外部 API に依存せず、prices_daily / raw_financials テーブルを前提に計算します（単体テストが容易）。
- OpenAI 呼び出しはテスト時にモックしやすいよう関数化（_call_openai_api）されています。ユニットテストでは該当関数をパッチしてください。

---

## よく使うコマンドまとめ

- 環境作成・依存インストール（例）
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML
  ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視の起動（デフォルト60秒間隔）
  ```
  python -m kabusys.run_monitoring
  # または間隔指定:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ExecutionEngine の起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート（例）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、各モジュール（ExecutionEngine の設定項目、OrderRepository API、AlertManager の実装例、DuckDB のテーブル定義など）について詳細なドキュメントやサンプルを別途作成します。どの部分を深掘りしたいか教えてください。