README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下を含むモジュール群を提供します。

- 注文実行エンジン（ExecutionEngine）とブローカ抽象化（paper/live 切替）
- 監視システム（System / Trade / Risk のポーリングおよび Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースセンチメント、レジーム判定：OpenAI 利用）
- ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成 など）

主な設計方針
- 環境変数（.env）ベースの設定管理
- Paper Trading と Live は DB/クライアントを完全分離
- 監視は SQLite（monitoring.db）にログを永続化
- DuckDB を分析・リサーチ用の時系列データ格納先として利用
- OpenAI API 呼び出しは明示的にキーを渡すか OPENAI_API_KEY を参照

機能一覧
--------
- 実行系
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ブローカーファクトリ：KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading.db に記録
  - PID 管理（data/execution.pid）・停止フラグ監視（data/stop_requested.flag）
- 監視系
  - System / Trade / Risk のモニタリング（python -m kabusys.run_monitoring）
  - 監視ログの永続化（SQLite: data/monitoring.db）
  - Kill Switch（data/kill.flag）によるエンジン強制停止
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- ポートフォリオ構築
  - 候補選定（スコア順）、等重／スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- リサーチ
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB を参照）
  - 将来リターン、IC（情報係数）、ファクター統計サマリ
- AI
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores テーブルに保存
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定（market_regime テーブルへ永続化）
- 開発／運用支援ツール
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.10+（typing| union 表記などを利用）
- 仮想環境を推奨

1. リポジトリを取得
   - git clone ... など

2. 仮想環境作成・依存パッケージインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install duckdb psutil openai
     - 追加で PyYAML（config 検証用）やテスト用パッケージが必要なら別途インストール

   ※ requirements.txt は本コード断片に含まれていません。必要なパッケージは上記参照ください。

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 画面の指示に従って J-Quants トークン、kabu API パスワード 等を設定
   - 生成された .env は絶対に Git にコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従い .env や config/*.yaml を修正
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリ（任意）作成
   - デフォルトの DB / ファイルは data/ 以下を参照します。必要に応じて作成されますが、権限の確認を行ってください。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション／設定:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI 呼び出しに使用する API キー
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）※ run_monitoring が参照

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag を検出したら起動せず終了
    - 実行中は data/stop_requested.flag の生成で安全停止
    - PID ファイル: data/execution.pid（Settings.pid_file_path）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き（秒）
  - 監視は常に production sqlite_path（settings.sqlite_path）を使用してログを記録します
  - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ
---
- setup_logging を通じてルートロガーが設定されます
- コンソール出力は stdout（StreamHandler）
- ファイル出力は logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）
- LOG_DIR 環境変数で変更可能

停止・Kill Switch
----------------
- 実行エンジンの外部停止（強制停止）は data/kill.flag（Settings.kill_flag_path）を書き込むことで行います。KillSwitch クラスがこのファイルを作成します（監視側が判定して自動で書き込み）。
- run_execution / run_monitoring を安全に止めるためのフラグ:
  - data/stop_requested.flag を作るとループが検出して優雅に終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）

ディレクトリ構成（主なファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                      -- 環境変数・設定取得ロジック
    config_setup.py                -- .env 対話ウィザード
    validate_config.py             -- 設定検証 CLI
    run_execution.py               -- ExecutionEngine 起動スクリプト
    run_monitoring.py              -- SystemMonitor ポーリング起動スクリプト

    execution/                      -- 発注周り（OrderManager, RiskManager, Reconciler 等）
      (実装詳細は該当モジュール参照)

    monitoring/
      monitoring_db.py             -- SQLite テーブル定義・永続化 API
      monitoring_engine.py         -- 各 Monitor を束ねるランナー
      system_monitor.py            -- システム／データ鮮度監視
      trade_monitor.py             -- 取引ログ監視（滞留注文・約定異常等）
      risk_monitor.py              -- ドローダウン／ポジション監視
      kill_switch.py               -- kill.flag の作成／評価
      alert_manager.py             -- 通知（LINE 等）管理（詳細は実装）

    portfolio/
      portfolio_builder.py         -- 候補選定・重み計算
      position_sizing.py           -- 株数決定・資金配分
      risk_adjustment.py           -- セクター制限・レジーム乗数

    research/
      factor_research.py           -- モメンタム／ボラティリティ／バリュー等
      feature_exploration.py       -- 将来リターン・IC・統計
      __init__.py

    ai/
      news_nlp.py                  -- ニュース→センチメント（OpenAI 経由）
      regime_detector.py           -- マクロ＋ETF MA200 でレジーム判定

    tools/
      paper_verification_report.py -- Paper Trading 検証レポート生成

    utils/
      logging_setup.py             -- ログ初期化ユーティリティ
      process_priority.py          -- プロセス優先度・CPU affinity 設定
      (その他ユーティリティ)

データ・ログの既定パス
---------------------
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で上書き可能)
- 監視 SQLite: data/monitoring.db (SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- PID / フラグ / ログ:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
  - logs/<app_name>.log

注意事項 / 運用メモ
------------------
- .env には機密情報（API キー・パスワードなど）を含みます。絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live のときは設定を慎重に確認してください（validate_config は live の場合に警告を出します）。
- OpenAI 関連は API 利用料が発生します。テスト・開発時はキーの扱いに注意してください。
- psutil によるプロセス優先度設定や CPU affinity は権限の制約で失敗することがあり、例外はログに変換されスキップされます。

開発者向け情報
---------------
- DuckDB 接続を利用する分析系関数は副作用を持たず、テストがしやすいよう設計されています。
- OpenAI API 呼び出しは専用の _call_openai_api を介しており、テスト時にモック可能です（unittest.mock.patch 推奨）。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB へ必要カラムを自動追加する軽微なマイグレーションを行います。

問い合わせ / 貢献
-----------------
バグ報告・機能提案・プルリクエストはリポジトリの Issue / PR を利用してください。README にない運用質問はコード中ドキュメント（docstring）を参照ください。

以上。ご不明点があれば用途（開発／運用）に応じて具体的に教えてください。導入手順や .env のサンプルなど、必要に応じて追加で用意します。