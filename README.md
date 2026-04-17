KabuSys — 日本株自動売買システム
=================================

本ドキュメントはリポジトリ内のコードベース（src/kabusys 以下）を前提とした簡易 README です。
開発・運用時に必要な概略、セットアップ手順、主要コマンド、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 支援）です。  
主な機能をモジュールに分割して実装しており、ローカル開発／ペーパートレード／本番（live）を切り替えて実行できます。

特徴（主な機能一覧）
------------------
- execution
  - ExecutionEngine（発注エンジン）／OrderManager／RiskManager／Reconciler（発注・約定管理、リスク制御）
  - paper_trading モードでは MockBrokerClient を使い、本番 DB と分離して data/paper_trading.db に記録
- monitoring
  - SystemMonitor：プロセス状態・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、KillSwitch による自動停止
  - MonitoringEngine：上記モニタを束ねて定期実行・アラート送出
  - 永続化用 SQLite 層（monitoring_db.py）
- portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- research（リサーチ）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC 計算、特徴量サマリ
- ai（LLM を用いた補助）
  - news_nlp：ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込み
  - regime_detector：ETF MA とマクロニュースを組合せて市場レジーム判定
- tools
  - paper_verification_report：ペーパートレード DB から検証レポートを生成
- config / ユーティリティ
  - 環境変数自動ロード（.env / .env.local）、設定ウィザード、設定検証 CLI
  - プロセス優先度・CPU affinity 設定ユーティリティ

前提（推奨）
-------------
- Python 3.10 以上（PEP 604 の | 型・構文を使用）
- SQLite は標準ライブラリで利用
- 外部ライブラリ（必要に応じて）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
  - （必要に応じてその他ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. 初期設定（.env の作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参照のこと（.env は Git にコミットしない）

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
   - OPENAI_API_KEY（AI 機能を使う場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト instant）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   注意:
   - .env 自動ロード: パッケージロード時にプロジェクトルートに .env / .env.local があると自動で読み込まれます。
     自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 実行時の KABUSYS_ENV により挙動が変わります:
    - development: 実発注は行わない（開発用）
    - paper_trading: MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）に記録
    - live: 実際にブローカー API へ発注
  - 実行中は data/execution.pid に PID が書き込まれる想定（設定により変更可）
  - 停止方法:
    - run_execution はプロジェクトルート/data/stop_requested.flag を監視しており、ファイル存在で停止処理を行います。
    - KillSwitch により data/kill.flag が書かれると ExecutionEngine 側で検知して停止する仕組みがあります（KillSwitch の実装は monitoring 側）。
  - 注意: KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする設定になり、production では 0 を推奨。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番の sqlite_path を参照（KABUSYS_ENV に依存せず本番監視 DB を使う設計）。
  - 停止方法:
    - プロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成・更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム・ニュース処理（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）

運用に関する補足
----------------
- データファイル類は data/ 以下に保存することを想定しています（.env で上書き可能）。
- kill.flag / stop_requested.flag:
  - monitoring/run scripts は stop_requested.flag を見て安全にループを終了します（手動停止用）。
  - KillSwitch はリスク条件（大きなドローダウン等）発生時に kill.flag を書き込み、ExecutionEngine 側がそれを検知して停止する仕組みです。
- ログレベルやパスは .env で調整してください（LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH 等）。

テスト・開発メモ
----------------
- research / portfolio / ai モジュールは DuckDB 接続を受け取る純関数中心の設計です。実 DB に書き込まずにユニットテスト可能です。
- validate_config は config/*.yaml の存在チェック・YAML パース確認を行いますが、PyYAML 未インストール時は YAML 検証をスキップします。
- OpenAI など外部 API 呼び出しを伴うコード（news_nlp, regime_detector）はテストで _call_openai_api をパッチしてスタブ化可能な設計になっています。

ディレクトリ構成（主なファイルと役割）
-------------------------------------
- src/kabusys/
  - __init__.py                    — パッケージ定義
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - config.py                      — Settings: 環境変数読み込みとラッパ
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite 監視 DB レイヤ（スキーマ作成・CRUD）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag の書き込み・管理
    - monitoring_engine.py         — 各 Monitor を束ねる実行エンジン
    - alert_manager.py             — （アラート送信管理 — 実装ファイル存在想定）
  - execution/                      — 発注関連（OrderRepository, ExecutionEngine 等）
    - (order_manager, order_repository, reconciler, risk_manager, broker_factory...)
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・資金制限
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py       — 将来リターン・IC・統計まとめ
  - ai/
    - news_nlp.py                  — ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py           — マクロ + ETF MA でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

ライセンス・貢献
----------------
- 本 README 内の運用手順はリポジトリの実装に基づいた説明です。実際の運用では .env の秘匿情報管理（Git へコミットしない）、テスト・ステージング環境での十分な検証を行ってください。

トラブルシューティング（よくある注意点）
---------------------------------------
- .env を Git にコミットしない: .env ファイルには API キー等の秘匿情報が含まれます。必ず .gitignore に入れて管理してください。
- 権限エラー: process_priority の設定は権限が必要な場合があります（psutil.AccessDenied を取り扱いスキップする実装です）。
- DuckDB / SQLite のパス: デフォルトは data 以下。親ディレクトリが存在しない場合はスクリプト実行時に警告されます（validate_config 参照）。
- OpenAI API: 呼び出し回数や料金に注意してください。テスト時はモック化を推奨します。

以上。必要であれば README に追記する具体的な起動例（systemd ユニットや Dockerfile のサンプル）、CI 向けのテスト手順、詳細な設定項目一覧（.env.example の生成）なども作成できます。どの情報を追加したいか教えてください。