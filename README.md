# KabuSys

日本株向け自動売買システム（ライブラリ／運用スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ユーティリティ、OpenAI を用いたニュース NLP／レジーム判定、ペーパートレード検証ツールなどを含む自動売買基盤です。

---

## プロジェクト概要

- モジュール群は src/kabusys 以下に配置されています。  
- 実行用スクリプト（プロセス）は Monitoring（監視）と Execution（発注エンジン）があり、ファイルシステム上のフラグや PID ファイルで起動・停止を制御します。  
- 設定は環境変数（.env）で管理。対話式ウィザードと検証ツールが用意されています。  
- データ永続化は SQLite（監視・履歴等）と DuckDB（価格・財務データ・分析）を使用します。  
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントやマクロセンチメント評価の機能を持ち、結果は ai_scores / market_regime 等に格納されます。

---

## 主な機能一覧

- 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループを起動
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可（デフォルト 60 秒）
    - 監視テーブルは常に本番 sqlite_path を使用
  - run_execution.py — ExecutionEngine を起動
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker（ペーパートレード）を使用し、paper_trading 用 DB に記録

- 設定管理
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI

- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine
  - KillSwitch（kill.flag による ExecutionEngine 停止）
  - MonitoringDB: SQLite に対する永続化層（system_status、trade_logs、positions、risk_logs、dashboard）

- 発注・実行（execution） — 実装ファイル群（broker, engine, order_manager, risk_manager 等）

- ポートフォリオ構築（portfolio）
  - 銘柄選定、重み計算、セクター制約、ポジションサイズ計算（単元株丸め含む）

- 研究（research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ

- AI（ai）
  - news_nlp.score_news — raw_news を集約して OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime — ETF の MA 乖離 + マクロセンチメントで市場レジーム判定

- ツール
  - tools.paper_verification_report — ペーパートレード DB を集計して検証レポートを出力

- ユーティリティ
  - utils.logging_setup — 統一ログ設定（stdout + 日次ローテートファイル）
  - utils.process_priority — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

1. Python と依存ライブラリのインストール（例）:
   - 推奨: Python 3.9+
   - 必要パッケージの代表例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - インストール例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

2. プロジェクトルートで .env を作成（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   - 出力された .env は絶対に Git にコミットしないでください（機密情報を含みます）。
   - 自動ロードはデフォルトで有効。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの作成（必要に応じて）:
   - デフォルト DB / ログパスは以下（環境変数で上書き可）:
     - DuckDB: data/kabusys.duckdb (`DUCKDB_PATH`)
     - SQLite (監視): data/monitoring.db (`SQLITE_PATH`)
     - ペーパートレード SQLite: data/paper_trading.db (`PAPER_TRADING_SQLITE_PATH`)
     - ログディレクトリ: logs/ (`LOG_DIR`)
   - 必要な親ディレクトリは自動作成されますが、権限等に注意してください。

---

## 使い方

- 環境変数の主なキー（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - その他（任意・デフォルトあり）:
    - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - LOG_LEVEL / LOG_DIR
    - OPENAI_API_KEY — AI 機能利用時に必要
    - PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
    - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（デフォルト 0。本番では 0 推奨）

- 実行例
  - 監視プロセスを起動:
    ```
    python -m kabusys.run_monitoring
    # MONITOR_POLL_INTERVAL を上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    - 監視ループは data/stop_requested.flag の存在で終了します。

  - 実行エンジンを起動:
    ```
    python -m kabusys.run_execution
    # ペーパートレードで起動（MockBroker を使用、Paper DB に記録される）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
    - 実行中は data/execution.pid 等を利用してプロセスを管理します。

  - Paper Trading 検証レポート:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

  - AI 機能（プログラムから呼ぶ例）
    ```python
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, date(2026, 4, 20), api_key="sk-...")
    ```
    - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用します。
    - AI 呼び出しは失敗時に安全側でフォールバックする設計です（例: score_news は失敗時 0 件返却）。

- 停止／Kill Switch
  - KillSwitch はリスク条件到達時に `data/kill.flag` を書き込み、ExecutionEngine 停止シグナルを送ります。
  - 手動でプロセスを止めたい場合は `data/stop_requested.flag` を作成します（run_monitoring/run_execution はこれを見て終了します）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- ログ
  - デフォルトで stdout と日次ローテートされるファイル（logs/<app_name>.log）に出力します。
  - ログレベルは `LOG_LEVEL` または setup_logging の引数で制御します。

---

## ディレクトリ構成（主要ファイル）

（src 以下をプロジェクトとして想定）

- src/kabusys/
  - __init__.py
  - config.py — Settings クラス（環境変数／.env の読み込み・検証）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — 監視ループ起動スクリプト
  - run_execution.py — 実行エンジン起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — 注文滞留や約定異常検出（実装あり）
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - alert_manager.py — 通知（LINE など）管理（存在）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...（発注・エンジン関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

- data/ (実行時に使用するファイル群)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
  - ...（ログや PID・フラグファイル）

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - （生成スクリプトあり / PyYAML があると内容検証を行う）

---

## 注意事項 / 運用上のポイント

- .env は機密情報を含むため絶対にバージョン管理に含めないでください。
- `KABUSYS_ENV=live` の場合は本番挙動になります。validate_config の警告を必ず確認してください。`KILL_FLAG_CLEAR_ON_START=1` は本番で危険です（推奨: 0）。
- Paper trading は本番 DB と分離されます（`KABUSYS_ENV=paper_trading` で paper_trading 用 SQLite を使用）。
- OpenAI を使用する機能は API キー（`OPENAI_API_KEY`）が必須です。呼び出しは外部 API に依存するため、コストやレート制限に注意してください。
- ログディレクトリや DB 保存先のパーミッションに注意してください。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 自動ロードされる .env はプロジェクトルート（.git か pyproject.toml を基準）で探索されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要ならば、README にコマンド例や CI 設定、システムアーキテクチャ図などを追加できます。追記したい内容（例: 実行エンジンの詳しい構成、order lifecycle、API の仕様など）があれば教えてください。