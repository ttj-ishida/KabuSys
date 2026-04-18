# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
この README はリポジトリ内の主要スクリプト・モジュールの概要、セットアップ方法、起動/利用手順、ディレクトリ構成を説明します。

注意: 実行には外部ライブラリ（duckdb, psutil, openai など）が必要です。テスト環境・本番環境の差分に注意して運用してください。

---

## プロジェクト概要

KabuSys は日本株向け自動売買システムのライブラリ群です。主な機能は次の通りです。

- 戦略側（ファクター計算・特徴量探索・ポートフォリオ構築）
- Execution エンジン（発注管理、リスク制御、Order 管理）
- Monitoring（システム状態・取引ログ・リスク監視、Kill Switch）
- AI 統合（ニュースセンチメント / レジーム判定：OpenAI を利用）
- 研究用ツール（Paper Trading 検証レポート等）
- 設定管理 (.env ウィザード / 検証)

コードは Python パッケージとして整理され、スクリプト風に起動できるモジュールを含みます。

---

## 主な機能一覧

- config:
  - Settings クラスで環境変数／.env を読み込み・検証
  - 自動 .env 読み込み（プロジェクトルートが検出される場合）
- config_setup:
  - 対話式ウィザードで `.env` を作成・更新
- validate_config:
  - 起動前の環境変数・設定ファイル検証 CLI（--strict オプションあり）
- run_execution:
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper DB に記録（本番 DB と分離）
  - 停止フラグ（data/stop_requested.flag）で安全に停止
- run_monitoring:
  - SystemMonitor をポーリングして監視ログを記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）
- monitoring:
  - SystemMonitor, TradeMonitor, RiskMonitor をまとめる MonitoringEngine
  - MonitoringDB: SQLite に対する読み書きレイヤ
  - KillSwitch: リスク条件に基づく data/kill.flag の書き込み
  - AlertManager（通知ロジック）等（コード内に組み込み）
- ai:
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector: ETF (1321) の MA 乖離とマクロニュースで市場レジームを判定
- research:
  - factor_research, feature_exploration: DuckDB 上でファクター計算・IC 計算等
- portfolio:
  - 候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム乗数
- tools:
  - paper_verification_report: ペーパートレード DB を集計し Pass/Fail 判定のレポートを出力

---

## 前提・必要環境

- Python 3.9+
- 必要なサードパーティライブラリ（最低限）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML 検証で使用）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（OpenAI API を利用する場合）

推奨: 仮想環境を作成して依存をインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（リポジトリに requirements.txt があればそれを利用してください。）

---

## 重要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

よく使う / 推奨設定:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、発注は MockBroker により data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログファイル保存先（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API を利用する場合に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）

.env 作成は `python -m kabusys.config_setup` を推奨（対話式ウィザード）。

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb, psutil, openai, pyyaml 等）
4. 対話式で `.env` を作成:
   ```bash
   python -m kabusys.config_setup
   ```
5. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたい場合
   python -m kabusys.validate_config --strict
   ```
6. 必要に応じて data ディレクトリやログディレクトリの権限を確認

---

## 使い方

以下は主要な起動・利用例です。

1. ExecutionEngine（戦略の発注エンジン）を起動
   - デフォルト（環境変数経由で KABUSYS_ENV を設定）
   ```bash
   # 例: 本番モード
   export KABUSYS_ENV=live
   python -m kabusys.run_execution
   ```
   - Paper Trading（MockBroker、別 DB に記録）
   ```bash
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   - 停止は `data/stop_requested.flag` を作成することで安全終了（スクリプトはフラグを検知して停止します）。
   - 実行中の PID は `data/execution.pid` に書き込まれます。

2. Monitoring を起動
   ```bash
   # ポーリング間隔を 30 秒にしたい場合
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```
   - 監視は Settings に記載された sqlite_path を使用して永続化します（monitoring は環境にかかわらず本番 sqlite_path を使用する仕様）。
   - 停止は `data/stop_requested.flag` を作成します（実行スクリプトは検知してループを抜けます）。

3. Paper Trading 検証レポート
   ```bash
   # デフォルト DB: data/paper_trading.db を参照
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

   # または明示的に DB を指定
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

4. OpenAI を使った処理（プログラム内呼び出し）
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を与えて呼び出します。OpenAI キーは環境変数 OPENAI_API_KEY か引数で渡せます。
   - 例（簡易、動作には duckdb 接続・テーブル準備が必要）:
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   n = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
   print("wrote", n, "scores")
   ```

5. Kill Switch / kill.flag
   - KillSwitch はリスク基準（ドローダウン超過等）で `data/kill.flag` を作成します。ExecutionEngine は kill.flag の存在状況を参照して動作する実装になっています（設定に依存）。
   - 起動時に kill.flag を自動でクリアしたい場合は `.env` の `KILL_FLAG_CLEAR_ON_START=1` を設定できますが、本番では推奨されません。

---

## ロギング / ファイル配置

- ログはデフォルト `logs/<app_name>.log`（日次ローテーション、30 日保持）へ出力され、コンソールは stdout に出力されます。
- データファイル（デフォルト）:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / flags: data/execution.pid, data/stop_requested.flag, data/kill.flag

ログ／データディレクトリの作成に失敗した場合でもプログラムは可能な範囲で継続します（ファイル出力は無効化され、コンソールのみとなるなど）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルのツリー（`src/kabusys` 配下）。実際のリポジトリにはさらにファイルがあります。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py

（上のツリーはコードベースからの抜粋です。実装によって細部は変わる可能性があります。）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV を `live` にした状態は本番運用です。LINE 通知や Kill Switch の設定を十分に確認してください（validate_config は live 時の追加警告を出します）。
- Paper Trading モードは本番 DB と分離されます。paper_trading のデータは `PAPER_TRADING_SQLITE_PATH` で設定できます。
- OpenAI の呼び出しはネットワーク・API レートの影響を受けます。news_nlp / regime_detector にはリトライ／バックオフが実装されていますが、APIキーの保護やコスト管理に注意してください。
- process priority の設定（utils.process_priority.set_process_priority）は OS によっては権限が必要になる場合があります。ログに警告が出ますが致命的エラーにはなりません。
- データ鮮度チェックや監視は DuckDB / prices_daily の整備が前提です。研究・分析用途に DuckDB を用意してください。

---

## トラブルシューティング

- PyYAML が見つからない場合、`validate_config` の YAML 内容チェックはスキップされます。インストールするには `pip install pyyaml`。
- ログディレクトリ作成に失敗したときは権限やパスを確認してください。コンソールには警告が出ます。
- OpenAI 呼び出しで 401/429/5xx が発生した場合は API キー・レート制限・ネットワークを確認。news_nlp/regime_detector は一部リトライしていますが、頻繁な失敗は処理結果に影響します。

---

必要であれば、README に次の情報も追記できます：
- 依存パッケージの完全な一覧（requirements.txt から自動生成）
- CI / テスト実行コマンド
- 実行例のより詳細なワークフロー（systemd / supervisor 用の Unit ファイル例）
- 各設定ファイル（config/*.yaml）とその意味の詳細ドキュメント

追記希望があれば教えてください。