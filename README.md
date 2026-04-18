KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買・研究・監視を目的としたモジュール群です。
README はこのコードベース（src/kabusys 以下）を前提に、概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
KabuSys は以下の責務を持つサブシステムで構成されています。

- ExecutionEngine: 発注ロジック、注文管理、リスク管理（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文・リスクの定期監視、Kill Switch によるエンジン停止
- Portfolio: 銘柄選定・配分・株数計算・リスク調整などの純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI: ニュース NLP（OpenAI）によるセンチメント評価・レジーム判定
- Utilities: ロギング設定、プロセス優先度設定、設定管理（.env の読み書き/検証）

主な特徴
--------
- 環境変数ベースの設定管理（.env、.env.local、自動読み込み。ただし無効化可能）
- KABUSYS_ENV による実行モード切替: development / paper_trading / live
  - paper_trading 時は MockBroker を使い、データを data/paper_trading.db に記録（本番 DB と分離）
- 監視コンポーネントは独立した polling ループを持ち、kill.flag による停止やアラート送出を行う
- DuckDB を分析用 DB（prices_daily, raw_financials など）として利用
- OpenAI を使ったニュース NLP / レジーム判定機能（API キー必要）
- ロギングは統一的にセットアップ（コンソール + 日次ローテーションファイル）
- 各種 CLI: 環境設定ウィザード、設定検証、ペーパートレード検証レポートなど

セットアップ手順
----------------

1. リポジトリをチェックアウト
   - 例: git clone ...

2. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - duckdb, psutil, openai, （PyYAML は config 検証時に利用されるオプション）
   - 例:
     - pip install duckdb psutil openai
     - pip install PyYAML   # config/.yaml の厳密検査を行う場合

4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を作成
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml が検出される場所）から行われます。
   - 自動読み込みを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 監視 DB / データディレクトリの作成（通常は自動作成されますが手動で作ることも可能）
   - logs/ ディレクトリはログ出力用に使用されます

重要な環境変数（抜粋）
---------------------
下記は主な環境変数とデフォルト値の一覧です（.env で設定）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用 SQLite（監視は常に本番 sqlite_path を参照）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading の場合はこちらを使用
- PAPER_FILL_MODE (instant | partial | never | reject) — MockBroker の約定挙動（デフォルト: instant）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル
- KILL_FLAG_CLEAR_ON_START (0 | 1) — ExecutionEngine 起動時の kill.flag 自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

使い方（主要スクリプト）
-----------------------

- 環境ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) にします。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB を利用します。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - 実行中に data/stop_requested.flag が作成されるとエンジンに停止を要求します。
    - PID ファイル: data/execution.pid（Settings により変更可）
    - プロセス優先度を "high" に設定しようとします（権限や OS に依存）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 特徴:
    - 環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して monitoring DB を初期化します。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
    - data/stop_requested.flag を検知すると監視ループを終了します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db を使用）
  - 出力: 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API を利用するため、OPENAI_API_KEY が必要です。API 呼び出し失敗時はフェイルセーフ（多くのケースで 0.0 を用いる）になっています。
  - これらは DuckDB の raw_news / prices_daily 等のテーブルを参照します。

停止フラグ / Kill Switch
------------------------
- data/kill.flag: KillSwitch により ExecutionEngine の停止を決定するために書き込まれるファイル。KillSwitch は監視結果（ドローダウン等）に基づきここへ理由を書きます。
- data/stop_requested.flag: run_execution / run_monitoring の外部停止用フラグ（存在すれば起動抑止・ループ終了）。

ログ
---
- ログはコンソール（stdout）とファイル（logs/<app_name>.log）へ出力されます。
- ローテーション: 日次、30 世代保持。
- 環境変数 LOG_DIR や LOG_LEVEL で挙動を変更可能。

ディレクトリ構成（主要ファイルの説明）
-------------------------------------
src/kabusys/
- __init__.py                        -- パッケージ定義、バージョン
- config.py                          -- Settings クラス（環境変数読み取り・自動 .env ロード）
- config_setup.py                    -- .env 対話ウィザード CLI
- validate_config.py                 -- .env / config/*.yaml の起動前検証 CLI
- run_execution.py                   -- ExecutionEngine 起動スクリプト
- run_monitoring.py                  -- Monitoring ポーリング起動スクリプト

src/kabusys/execution/
- broker_factory.py                  -- ブローカークライアント生成（Mock / 実ブローカー分岐）
- execution_engine.py                -- 発注エンジン本体（run_session 等）
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py
                                     -- 発注・注文管理・リコンシリエーション・リスク管理など

src/kabusys/monitoring/
- monitoring_db.py                   -- SQLite スキーマ初期化 + 永続化層
- system_monitor.py                  -- CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py                   -- 注文滞留/約定異常検出（実装ファイルあり）
- risk_monitor.py                     -- ドローダウン/ポジション上限監視
- kill_switch.py                      -- kill.flag の作成/削除
- alert_manager.py                    -- アラート通知（LINE など） — 実装に依存

src/kabusys/portfolio/
- portfolio_builder.py               -- 候補選定・重み計算
- position_sizing.py                 -- 株数計算・集約キャップ・単元丸め
- risk_adjustment.py                 -- セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py                 -- momentum, volatility, value 等のファクター計算（DuckDB）
- feature_exploration.py             -- 将来リターン計算、IC、統計要約

src/kabusys/ai/
- news_nlp.py                        -- ニュースを OpenAI でスコアリングし ai_scores に書き込む
- regime_detector.py                 -- ETF MA + マクロ NLP を組み合わせて市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py       -- ペーパートレード検証レポート生成スクリプト

src/kabusys/utils/
- logging_setup.py                   -- ロギング初期化ユーティリティ
- process_priority.py                -- プロセス優先度・CPU affinity 設定
- その他ユーティリティ群

データ / ファイル（プロジェクトルート）
- data/kabusys.duckdb                 -- DuckDB（デフォルト）
- data/monitoring.db                  -- Monitoring SQLite（デフォルト）
- data/paper_trading.db               -- Paper trading 用 SQLite（paper_trading モード）
- data/execution.pid                  -- ExecutionEngine PID ファイル（デフォルト）
- data/kill.flag                       -- Kill Switch が書き込む停止フラグ
- data/stop_requested.flag             -- run_* スクリプトの外部停止フラグ

注意事項 / 運用上のヒント
------------------------
- 本番モード (KABUSYS_ENV=live) では設定・アラート周り（LINE トークン等）を必ず確認してください。validate_config は live 向けの追加チェックも行います。
- Monitoring は run_monitoring の実装上「環境にかかわらず」Settings.sqlite_path（本番用 sqlite_path）を使って DB を初期化します。監視対象 DB の扱いに注意してください。
- paper_trading モードは本番 DB と完全分離されるよう設計されていますが、.env の PAPER_TRADING_SQLITE_PATH を必ず確認してください。
- OpenAI を用いる機能は API コストが発生します。テスト時はモック化するか API キーをセットしないでください（未設定なら明示的例外/フォールバックがあります）。
- ログディレクトリ作成に失敗するケースがあるため、ログ出力先 (LOG_DIR) のパーミッションを事前に確認してください。
- プロセス優先度・CPU affinity の変更は OS 権限に依存します。権限不足時は警告になりスキップされます。

例: よく使うコマンド
-------------------
- .env を作る:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution (本番/ペーパートレード):
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

最後に
------
この README はコードベースの現状（src/kabusys 内のファイル群）に基づいてまとめています。実際の運用では各モジュールの詳細実装（risk_manager、execution_engine、alert_manager 等）や外部インテグレーションに応じた追加設定が必要です。質問や README に追記したい点があれば教えてください。