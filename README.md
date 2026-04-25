KabuSys
======

日本株向けの自動売買・分析プラットフォームの軽量実装（内部モジュール群の抜粋）。
このリポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine：注文発行・注文管理・リスク管理の実装（ペーパートレードモードあり）
- Monitoring：システム状態・注文状態・リスク監視、Kill Switch による停止制御
- Portfolio：銘柄選定・重み計算・ポジションサイズ算出などのポートフォリオ構築ロジック
- Research：ファクター計算・将来リターン・IC 計算などの研究用ユーティリティ（DuckDB ベース）
- AI：ニュースのセンチメント評価・市場レジーム判定（OpenAI を使用するモジュール）
- CLI ツール群：.env ウィザード・設定検証・Paper Trading の検証レポート生成 等
- utils：ログ設定・プロセス優先度設定など運用ユーティリティ

プロジェクト概要
---------------
KabuSys は日本株の自動売買システムのコアロジック（信号 → ポートフォリオ構築 → 発注 → 監視）をモジュール化した実装です。  
設計上の特徴：

- 実行系（Execution）は本番・ペーパートレードを分離（PAPER_TRADING 用 DB を使用）
- 監視系（Monitoring）は独立したプロセスでポーリング・アラート・Kill Switch を担う
- DuckDB を利用したオンディスク分析（Research / AI モジュール）
- OpenAI を用いたニュース NLP / レジーム検出（APIキーが必要）
- 設定は .env で管理し、対話式ウィザードや検証ツールを提供

主な機能一覧
-------------
- run_execution: ExecutionEngine を起動（KABUSYS_ENV が paper_trading の場合は MockBroker）
- run_monitoring: SystemMonitor をポーリングして system_status / risk / trade を監視
- config_setup: .env を対話式生成・更新するウィザード
- validate_config: .env と config/*.yaml の整合性チェック（--strict 指定で警告も失敗扱い）
- portfolio:
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes（リスクベース／等配分等）
  - apply_sector_cap / calc_regime_multiplier（セクター上限・レジーム補正）
- research:
  - calc_momentum / calc_volatility / calc_value（DuckDB の prices_daily/raw_financials を基に計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量評価）
- ai:
  - score_news: raw_news を LLM で評価して ai_scores に書き込む（OpenAI 必須）
  - score_regime: ETF MA とマクロニュースを合成して market_regime を判定
- tools:
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを出力

セットアップ手順
----------------
前提
- Python 3.9+（厳密なバージョン要件はプロジェクト内で管理してください）
- 必要な外部ライブラリ: duckdb, psutil, openai, （任意）PyYAML

例（最小）:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意で設定検証の YAML 検査を行う場合: pip install PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を推奨）

3. ディレクトリ準備（data / logs 等）
   - mkdir -p data logs

4. .env の作成
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - または手動で .env を作成（最低限の必須環境変数）:
       JQUANTS_REFRESH_TOKEN=your_token
       KABU_API_PASSWORD=your_password
       KABUSYS_ENV=development
       LOG_LEVEL=INFO
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db

   注意:
   - .env は Git にコミットしてはいけません。
   - 自動ロードはデフォルトで有効（プロジェクトルートに .env を配置すると自動読み込みされます）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. OpenAI を使う場合
   - OPENAI_API_KEY 環境変数を設定（ai.news_nlp / ai.regime_detector が使用）
   - 例: export OPENAI_API_KEY="sk-..."

使い方
------
主要スクリプトの起動例:

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（ローカル開発 / 本番）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切替:
    - development / paper_trading / live
  - paper_trading を使うと MockBrokerClient が利用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- Monitoring を起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視ループを外部から終了するにはプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring と run_execution は stop_requested.flag を監視して安全に停止します）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

運用メモ / 重要な環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV ∈ {development, paper_trading, live}
- DB パス:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト data/paper_trading.db）
- ログ:
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- Monitoring:
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - Kill Switch フラグ: data/kill.flag（KillSwitch により作成され、ExecutionEngine に停止シグナルを送る）
  - stop_requested.flag: data/stop_requested.flag（監視/実行プロセスを安全に停止させるためのフラグ）
- Paper Trading 動作:
  - PAPER_FILL_MODE ∈ {"instant","partial","never","reject"}（デフォルト "instant"）
- OpenAI:
  - OPENAI_API_KEY（ai モジュール利用時必須）

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込み / Settings クラス（環境変数管理）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（ペーパートレード分離）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager など（発注ロジック）
- monitoring/
  - monitoring_db.py（SQLite 永続化レイヤ）
  - system_monitor.py（システム状態・データ鮮度監視）
  - trade_monitor.py（注文滞留・約定異常検出）
  - risk_monitor.py（ドローダウン・ポジション監視）
  - kill_switch.py（Kill Switch）
  - monitoring_engine.py（各モニタの統合）
  - alert_manager.py（通知管理、LINE 等）
- portfolio/
  - portfolio_builder.py（候補選定・重み）
  - position_sizing.py（株数計算）
  - risk_adjustment.py（セクター制限・レジーム乗数）
- research/
  - factor_research.py（ファクター計算）
  - feature_exploration.py（IC・統計解析）
- ai/
  - news_nlp.py（ニュースセンチメント）
  - regime_detector.py（レジーム判定）
- monitoring/monitoring_db.py（監視用 DB スキーマ・API）
- data/（ランタイムで作成されることを想定）
  - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等
- tools/
  - paper_verification_report.py（ペーパートレード検証レポート）
- utils/
  - logging_setup.py（統一ログ設定）
  - process_priority.py（プロセス優先度 / affinity 設定）

サンプル .env（最小）
-------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

運用上の注意
-------------
- .env をリポジトリにコミットしないこと（機密情報が含まれる）。
- KABUSYS_ENV=live の場合は特に設定を慎重に確認すること（validate_config で警告あり）。
- run_execution / run_monitoring は stop_requested.flag を監視しているため、手動停止時はこのフラグを使うかプロセスを適切に終了してください。
- OpenAI を利用するモジュールは API の呼び出し回数・速度制限に注意し、API キーの課金に配慮してください。
- DuckDB や SQLite のファイルパスは .env で適切に分離（特に paper_trading 用 DB）すること。

サポート / 開発フロー
--------------------
- 設定を変更したら python -m kabusys.validate_config で必ず検証してください。
- 開発中は KABUSYS_ENV=development を使い、実際の発注は行わないモードで動作確認を行ってください。
- ログは logs/<app_name>.log にローテーションで出力されます（デフォルト 30 日保持）。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。  
ライセンスはリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

---
この README はソースコード（src/kabusys 以下）の記述に基づいて作成しています。より詳細な実装や追加の設定は各モジュールのドキュメント（ソース内 docstring）を参照してください。必要であれば README に含める実行例やトラブルシューティング項目を追加しますのでお知らせください。