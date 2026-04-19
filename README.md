# KabuSys

日本株向けの自動売買システム（ライブラリ & ランタイムスクリプト群）。

このリポジトリは、シグナル計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI（ニュース/NLP）連携、調査用ユーティリティなどを含む一連のコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。以下の主要責務を持ちます。

- ファクター計算・特徴量生成（research）
- ポートフォリオ構築（候補選定・重みづけ・株数算定）
- 発注エンジン（ExecutionEngine / ブローカー抽象化: 本番 / ペーパートレード切替）
- 監視（システム／発注／リスクのポーリング、Kill Switch）
- AI連携（OpenAI を用いたニュースセンチメント、レジーム検出）
- 運用ツール（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部:
- 設定は環境変数（.env）で管理。`.env` の自動読み込み機能あり。
- paper_trading と live を明確に分離（paper_trading は専用 SQLite DB に記録）。
- 実行スクリプトはプロセス優先度やログ設定などを統一的に行う。

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 発注 / 実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの切替（本番 / MockPaperTrading）
  - 発注ログ（SQLite: trade_logs）保存
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（MonitoringEngine）
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
  - Kill Switch（データ/kill.flag）によるエンジン停止シグナル
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ算出
  - セクターキャップ適用、レジーム乗数
- 研究・調査
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC・統計サマリー
- AI
  - ニュース NLP による銘柄別センチメント算出（OpenAI）
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- ツール
  - ペーパートレード検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境向け）

※ 以下は一般的な手順です。requirements テキストが別途ある場合はそちらに従ってください。

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作る:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存ライブラリのインストール（例）
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で使用）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

3. プロジェクトルートで初期ディレクトリを作成
   ```
   mkdir -p data logs
   ```

4. .env の作成
   - 対話式ウィザードを使うのが簡単です:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を作成し、必要な値を設定してください（下記「環境変数一覧」参照）。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主要なもの）

主に `kabusys.config.Settings` で使用される代表的な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
  - paper_trading の場合は発注がモックになり、data/paper_trading.db に記録される
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能を利用する場合必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知に使用する場合)

その他、MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）などは個別に参照されます。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動（本番 / paper_trading は KABUSYS_ENV で切替）
  ```
  # 本番モードなら
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  注意:
  - paper_trading の場合、MockBrokerClient を使い、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離して記録されます。
  - 実行は別プロセスで行い、Process PID は `data/execution.pid` に保存されます。

- 監視ループ起動
  ```
  # デフォルトは 60 秒間隔。環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視は常に Settings.sqlite_path（monitoring.db）を使用します（KABUSYS_ENV に依存しません）。
  - 停止はプロジェクトの data/stop_requested.flag を作ることで行えます（run スクリプトはこのフラグを監視します）。

- ペーパートレード検証レポート生成
  ```
  # デフォルトは data/paper_trading.db を参照
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 機能（コードから利用）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定する必要があります。
  - 例（Python REPL / スクリプト内）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    date = datetime.date(2026, 4, 1)
    n_written = score_news(conn, date)  # ai_scores テーブルへ書き込み
    ```

---

## ログとDB

- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル名はアプリケーション名（例: execution.log, monitoring.log）で日次ローテーションされます。
  - ログレベルは `LOG_LEVEL` 環境変数で設定。

- データベース:
  - DuckDB: 分析用（デフォルト: data/kabusys.duckdb）
  - SQLite (監視): data/monitoring.db（Monitoring 用）
  - SQLite (paper_trading): data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

---

## 停止 / Kill Switch

- run_execution と run_monitoring はプロジェクト直下の `data/stop_requested.flag` を監視しており、これが存在すると安全にループを終了します（run_execution はエンジン停止をトリガー）。
- Kill Switch:
  - RiskMonitor などが条件を満たした場合、`data/kill.flag` を書き込みます。
  - kill.flag が書かれると ExecutionEngine 側で検出してシャットダウンする想定です。
  - 本番で `KILL_FLAG_CLEAR_ON_START=1` にするのは危険です（自動で Kill Flag をクリアしてしまうため）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数 / Settings
    - config_setup.py           -- .env 作成ウィザード
    - validate_config.py        -- 設定検証 CLI
    - run_execution.py          -- ExecutionEngine 起動スクリプト
    - run_monitoring.py         -- SystemMonitor ポーリングスクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (想定)
    - execution/
      - execution_engine.py (想定)
      - broker_factory.py (想定)
      - order_manager.py (想定)
      - order_repository.py (想定)
      - reconciler.py (想定)
      - risk_manager.py (想定)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                      -- 実行時に利用するフォルダ（logs/ と同様に作成推奨）

※ 実際のリポジトリでは上記に加えてさらに多くのファイルが存在します（コメントや docstring を参照してください）。

---

## 開発・運用上の注意点

- データベースファイル（特に .env 中のパス）は本番と開発で分離してください。paper_trading 用の DB は別ファイルにしてあるため、本番データと混ざりにくい設計です。
- OpenAI を利用する機能は API コストやレイテンシに注意して運用してください。API エラー時はフェイルセーフでスコアをスキップまたは中立値にフォールバックする実装になっていますが、キーの管理は厳重に。
- ログはデフォルトで日次ローテーション・30日分保持です。運用ニーズに合わせて LOG_DIR / LOG_LEVEL を調整してください。
- run_execution/run_monitoring はそれぞれ専用の PID / stop フラグを使って安全に制御します。手動で停止する場合は stop_requested.flag を作成するか、プロセスに SIGINT を送ってください。

---

## 参考コマンドまとめ

- 仮想環境作成 / 依存インストール（例）
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML
  ```

- .env 作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループ起動
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている内容で不明点や、実際の運用向けの追加ドキュメント（デプロイ手順、systemd / supervisor 用ユニット例、監視ダッシュボード等）が必要であれば教えてください。必要に応じて追記・テンプレート作成します。