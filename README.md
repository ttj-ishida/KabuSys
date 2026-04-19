# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ用 README。  
このドキュメントはリポジトリ内の主要コンポーネント・使い方・セットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主な役割は次のとおりです。

- 発注処理を実行する ExecutionEngine（本番 / ペーパートレード）
- システム稼働・注文状態・リスクを監視する Monitoring（Kill Switch を含む）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限 等）
- リサーチ向けファクター計算・特徴量解析（DuckDB を利用したオフライン解析）
- AI モジュール（OpenAI を用いたニュース NLP や市場レジーム判定）
- ユーティリティ群（ログ設定、プロセス優先度設定、設定管理 CLI 等）

設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（日時参照の扱い）」「外部 API 失敗時のフェイルセーフ」を重視しています。

---

## 機能一覧（抜粋）

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading なら MockBroker を用い、専用の paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を制御。
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：監視の中心ロジック。
  - KillSwitch：ドローダウンやポジション上限で kill.flag を書き込み ExecutionEngine を停止させる。
  - monitoring_db.py：SQLite に監視ログを永続化する層（スキーマ定義・マイグレーション含む）。
- 発注関連
  - ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler（実装場所: src/kabusys/execution）
- ポートフォリオ構築（純粋関数）
  - candidate 選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数等（src/kabusys/portfolio）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン、IC 計算、統計サマリー（src/kabusys/research）
- AI
  - news_nlp: raw_news をまとめて OpenAI に送信し、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- CLI / ツール
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env / config/*.yaml の起動前検査
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 必要条件（推奨）

- Python 3.10+
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config の YAML 検査を行う場合）
- ネットワークアクセス（本番で OpenAI/Kabu API/J-Quants 等を使用する場合）

例（venv を作って pip インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
実際の requirements ファイルはリポジトリに応じて用意してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 仮想環境を作成して依存をインストール（上記参照）。

3. .env の作成:
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または手動でプロジェクトルートに `.env` を作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - その他（任意または環境に応じて）:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB)
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE など

   - 自動読み込みの挙動:
     - 起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（既存の OS 環境を上書きしません）。
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定の検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. 初期 DB は起動スクリプトで必要に応じて作成/マイグレーションされます（monitoring は init_monitoring_db を呼び出します）。`data/` 以下や `logs/` は自動で作られますが、権限等に注意してください。

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動（本番/ペーパートレード共通エントリ）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading をセットすると MockBroker を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中に停止指示を出す方法:
    - KillSwitch が動作して `data/kill.flag` を書き込む（自動）
    - 管理者が `data/stop_requested.flag` を作成すると run_execution は起動せず/停止します（スクリプトで使用）。
  - 実行時、`data/execution.pid` に PID が書き込まれます（設定: Settings.pid_file_path）。

- Monitoring を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    ```
  - 監視は常に本番用の sqlite_path を使用します（環境に関係なく監視 DB は同じパスに記録）。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH`、なければ `data/paper_trading.db` を参照します。

- AI モジュール（Python API として呼ぶ例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, date(2026, 4, 10), api_key="sk-...")
  r = score_regime(conn, date(2026, 4, 10), api_key="sk-...")
  ```

- ログ:
  - setup_logging を通じてコンソール出力と日次ローテートファイルが `logs/<app_name>.log` に保存されます。LOG_DIR で変更可能。

---

## 設定（主要な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)

- DB / ファイルパス
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (監視DB、例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB)
  - PID_FILE_PATH (例: data/execution.pid)
  - KILL_FLAG_PATH (例: data/kill.flag)

- AI / API
  - OPENAI_API_KEY (news_nlp / regime_detector 用)
  - KABU_API_BASE_URL (kabuステーション API のベース URL)
  - PAPER_FILL_MODE (ペーパートレード時の約定挙動: instant | partial | never | reject)

- ログ・運用
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR
  - MONITOR_POLL_INTERVAL (run_monitoring の秒間隔)

---

## 運用上の注意点

- Monitoring は監視データを常に本番用 sqlite_path に保存します（KABUSYS_ENV に依存しない）。
- ExecutionEngine は KABUSYS_ENV=paper_trading のときに専用の paper_trading DB を使用します（本番 DB と区別）。
- Kill Switch（kill.flag）は冪等に書き込まれるため、存在確認・クリアの扱いに注意してください。`KILL_FLAG_CLEAR_ON_START` を 1 にすると起動時に自動で kill.flag をクリアしますが、これは本番では推奨されません。
- OpenAI / ネットワーク API 呼び出しはリトライやフォールバックを備えていますが、API キーやレート制限に注意してください。
- .env やシークレットは Git に絶対にコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照ファイル)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照ファイル)
  - execution/                 — Execution 関連（Engine, order_manager など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に作成される可能性あり)
    - *.db, kill.flag, stop_requested.flag, execution.pid
  - logs/ (ログ出力先)

（リストはリポジトリの抜粋です。実際のファイル・モジュールは更に存在する可能性があります。）

---

## 開発 / テストのヒント

- unit テストを作成する際は、環境変数の自動ロードを抑止するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると便利です。
- OpenAI 呼び出しなど外部 API はモック化してテストすることを推奨します（コード内でもモックしやすい設計になっています）。
- DuckDB 接続を渡すことでリサーチ系機能をローカルで容易にテストできます。

---

必要であれば、この README に以下を追加できます：
- 依存関係の厳密な requirements.txt（パッケージ名と推奨バージョン）
- デプロイ / systemd / Docker の例
- 主要コンポーネント（ExecutionEngine、MonitoringEngine、OrderManager 等）の詳細なアーキテクチャ図やフロー説明

どの追加情報が必要か教えてください。