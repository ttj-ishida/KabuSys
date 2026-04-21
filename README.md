# KabuSys

日本株向けの自動売買・分析プラットフォームの一部実装です。  
本リポジトリは以下の主要コンポーネントを含みます：監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、ファクター計算、AI ベースのニュース解析など。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を提供します。

- 実行エンジン（ExecutionEngine）：発注・リスク管理・オーダー処理の実行ループを担います（paper_trading モードであれば MockBroker を使用）。
- 監視（Monitoring）：システム稼働状況、トレードログ、リスク指標をポーリングして永続化・アラート発生・Kill Switch を制御します。
- 研究・リサーチ：DuckDB を使ったファクター計算・特徴量探索（momentum, value, volatility 等）。
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む機能。
- ツール群：ペーパートレード検証レポート生成などユーティリティ。

設計上のポイント：
- 環境変数 / .env による設定管理（自動ロード機能あり）。
- 本番・ペーパートレードの DB 分離（Execution 起動時に切替）。
- DuckDB をデータ分析用、SQLite を監視・履歴用に使用。
- ロギングは統一的に設定（ログ回転・コンソール出力）。

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - RiskManager、OrderManager、Reconciler 等の組み立てと Engine の起動
  - PID ファイル管理と stop フラグ検出による安全停止

- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存・データ鮮度監視
  - TradeMonitor：トレード滞留 / 約定異常等の検出（TradeCheckResult）
  - RiskMonitor：ドローダウン・ポジション上限監視（KillSwitch と連携）
  - MonitoringEngine：上記モニタを束ねポーリング、アラート・Kill Switch 書込

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重・スコア重みによる配分、リスク制約（セクター上限・レジーム乗数）
  - position sizing（ロット丸め、利用可能資金に基づくスケーリング）

- リサーチ（research パッケージ）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー

- AI（ai パッケージ）
  - news_nlp: OpenAI を利用したニュースセンチメント解析・ai_scores 書き込み
  - regime_detector: ma200 乖離 + マクロニュースの LLM 結果から市場レジーム判定

- 設定支援・検証
  - config_setup.py：.env の対話式作成ウィザード
  - validate_config.py：.env / config/*.yaml の事前検証
  - Settings クラス（kabusys.config）でアプリ設定を集中管理

- ツール
  - tools/paper_verification_report.py：ペーパートレード DB から検証レポート生成

---

## セットアップ手順（開発用）

以下は本リポジトリをローカルで起動・実行するための基本手順です。

1. Python 環境の準備
   - 推奨: Python 3.9+（コードは型ヒントを使用しています）
   - 仮想環境を作る:
     - python -m venv .venv
     - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要なライブラリをインストール
   - 代表的な依存パッケージ（requirements.txt がない場合は手動で）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照して必要な値を設定）
   - 最低必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番モードで実行する場合は KABUSYS_ENV=live を設定（注意: 本番設定は慎重に）

4. 自動 .env ロードの挙動
   - デフォルトでプロジェクトルートの `.env` と `.env.local` を自動で読み込みます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ログディレクトリ
   - デフォルトは `logs/`。環境変数 `LOG_DIR` で変更可能。
   - ログレベルは `LOG_LEVEL`（例: DEBUG, INFO）で指定。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モードで使用）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: (0/1) Execution 起動時に kill flag を自動クリアするか

---

## 使い方（実行例）

- .env の作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
  - 注: run_monitoring は KABUSYS_ENV にかかわらず monitoring 用の sqlite_path を使用します（監視は常に本番 DB を参照）。

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録され、本番 DB と分離されます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（例）
  - OpenAI API キーが必要:
    - export OPENAI_API_KEY=sk-...
  - news_nlp を利用してスコアを生成する関数は kabusys.ai.score_news（プログラム内から呼び出す）。

- 停止制御（Kill Switch / stop フラグ）
  - ExecutionEngine 停止: `data/kill.flag` を作成すると ExecutionEngine が停止されます（KillSwitch が write する仕組み）。
  - run_monitoring / run_execution の外部停止: `data/stop_requested.flag` を作成するとループが検知して終了します。
  - 起動時の kill.flag 自動クリアは `KILL_FLAG_CLEAR_ON_START=1`（本番では推奨されません）。

---

## ロギング

- setup_logging 関数によりコンソール（stdout）と日次ローテートファイルに出力されます。
- デフォルトログディレクトリ: logs/
- ファイル名: <app_name>.log（例: execution.log, monitoring.log）
- 環境変数 LOG_DIR / LOG_LEVEL で上書き可能。

---

## ディレクトリ構成（概要）

以下は主要なソースツリー（src/kabusys 以下）を抜粋した構成例です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込み
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_monitoring.py          — Monitoring ポーリングスクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照されるがここでは割愛)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるがここでは割愛)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                      — 実行時生成される (logs/ と同様)

（実際のリポジトリにはさらに細かいファイル・モジュールが含まれます）

---

## 運用上の注意点

- KABUSYS_ENV を `live` にする場合は、外部 API キー・パスワード・LINE 通知等の設定を十分に確認してください。validate_config の `--strict` でチェックできます。
- ペーパートレードは本番データベースと分離されるよう設計されていますが、環境変数設定ミスにより上書きされると混在する恐れがあります（特に SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI を使う機能は API コストが発生します。API 呼び出し回数・バッチサイズの制御に注意してください。
- プロセス優先度設定や CPU affinity は psutil を使います。権限不足で警告が出ることがありますが、処理自体は継続されます。
- ログディレクトリ作成失敗時はコンソールのみで動作します。

---

## 開発・拡張のヒント

- DuckDB 接続をテスト用にモックすることで、ファクター計算や AI モジュールの単体テストが容易になります。
- OpenAI 呼び出し部分は個別のヘルパをモック可能な形で実装しているため、ユニットテストは容易です（コード中にモック用の patch 指定箇所あり）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると安全です。

---

この README はコードベースの主要点をまとめた抜粋ドキュメントです。各モジュールの詳しい仕様・API はソース内の docstring やコメントを参照してください。必要であれば、特定モジュール（例: ExecutionEngine の起動要件、AI モジュールのレスポンス仕様、DB スキーマ等）について追記できます。