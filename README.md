KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: 発注・オーダー管理・リスク管理
- 監視（Monitoring）: システム稼働・注文状態・リスクの定期チェック、必要時に Kill Switch を発動
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ算出
- リサーチ機能: ファクター計算、特徴量探索（DuckDB を使用）
- AI 補助機能: ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI）
- ユーティリティ: .env ウィザード、設定検証、ペーパートレード用レポート生成 等

主な特徴
---------
- 開発 / ペーパートレード / 本番（live）を切り替えられる KABUSYS_ENV 設定
- Paper Trading 時は本番 DB と完全分離された SQLite を使用
- DuckDB を用いたオンデマンドなリサーチ処理（prices_daily / raw_financials 等）
- OpenAI を使ったニュースセンチメント（news_nlp）およびレジーム判定（regime_detector）
- ログは標準出力と日次ローテーションファイル（logs/*.log）で管理
- 監視は SQLite に永続化（system_status / trade_logs / risk_logs / positions / dashboard）
- Kill Switch（data/kill.flag）を用いた安全停止シグナル

必要条件
--------
- Python 3.10+
- pip パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - （任意）PyYAML（config/*.yaml の検証を行う場合）

例:
  pip install duckdb psutil openai

セットアップ手順（簡易）
----------------------
1. リポジトリをクローン / ソースを配置
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install duckdb psutil openai
   （PyYAML を検証に使いたい場合: pip install pyyaml）
4. .env の作成（対話式ウィザード）
   python -m kabusys.config_setup
   → ウィザードに従って J-Quants / kabu API などを設定します。
5. 設定検証（任意）
   python -m kabusys.validate_config
   厳密モード（警告も失敗扱い）:
   python -m kabusys.validate_config --strict

環境変数 / .env（主な項目）
-------------------------
以下は主要な環境変数（.env に設定可能）。() 内はデフォルトまたは備考。

- KABUSYS_ENV: 実行環境（development | paper_trading | live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject） default: instant
- LOG_LEVEL: ログレベル（DEBUG|INFO|...） default: INFO
- LOG_DIR: ログ格納ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI を使う場合は設定
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、default 0）
- PID_FILE_PATH / KILL_FLAG_PATH: それぞれ書き換え可能（default: data/execution.pid / data/kill.flag）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を検出し、
  .env → .env.local を自動読み込みします（OS 環境変数を上書きしません）。
- 自動読み込みを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

実行方法（主要コマンド）
-----------------------

- 実行エンジン（ExecutionEngine）起動:
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db を利用（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んで安全終了
  - PID は data/execution.pid（設定で変更可）に記述

- 監視プロセス起動:
  python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番用 sqlite_path を使用（監視データは本番 DB に記録される）
  - data/stop_requested.flag が存在すると監視ループを終了

- 設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB パスを指定可能

AI（OpenAI）関連機能
-------------------
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols から記事を集約して OpenAI に送信、ai_scores テーブルへ書き込み
  - OPENAI_API_KEY または api_key 引数が必要

- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離とマクロ記事の LLM スコアを合成して market_regime に書き込み
  - OPENAI_API_KEY または api_key 引数が必要

これらはライブラリ関数として呼び出す形です（直接の CLI は提供していませんが、簡単にスクリプト化できます）。

データファイル・フラグ
--------------------
- デフォルト DB / ファイル:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視 SQLite)
  - data/paper_trading.db (ペーパートレード SQLite)
  - data/execution.pid (PID ファイル)
  - data/kill.flag (Kill Switch)
  - data/stop_requested.flag (監視／実行停止リクエスト用)

- Kill Switch:
  - kill.flag が書かれると ExecutionEngine に停止シグナルを送る仕組みがあります（監視が判断して書き込むこともあります）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリア（本番では 0 推奨）。

ログ
----
- ログは stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次、30日保持）に出力されます。
- ログディレクトリを変更する場合は LOG_DIR を設定します。

注意点 / 運用メモ
-----------------
- KABUSYS_ENV が live の場合は特に注意して設定を確認してください（validate_config に guard チェックあり）。
- Paper Trading は本番 DB と分離されますが、monitoring は常に本番 sqlite_path を参照します（監視ログは本番側に残るため注意）。
- .env 内の機密情報（API キー等）は絶対に Git にコミットしないでください（config_setup.py でも注意書きがあります）。
- OpenAI の API 呼び出しは外部ネットワークと課金を伴うため、本番運用時の制御・レート管理やエラーハンドリング方針を確認してください。

主要ディレクトリ構成
-------------------
（src/kabusys をルートとした要約）

- kabusys/
  - __init__.py                      — パッケージ定義（バージョン等）
  - config.py                        — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py                  — .env 対話ウィザード
  - validate_config.py               — 起動前の設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

  - execution/                       — 発注・注文管理周り（BrokerFactory, ExecutionEngine 等）
  - monitoring/
    - monitoring_db.py               — 監視用 SQLite 永続層（テーブル定義・永続化 API）
    - system_monitor.py              — システム稼働・データ鮮度チェック
    - trade_monitor.py               — 注文滞留・約定異常検出（※実装ファイルあり）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - monitoring_engine.py           — 複数モニタを束ねるエンジン
    - alert_manager.py               — アラート送信（LINE 等）（※実装ファイルあり）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定・資金配分ロジック
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — IC・将来リターン・統計要約
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成
  - data/                             — 実行時に使われる SQLite/DuckDB/logs/flag 等（生成される）

ドキュメント参照・拡張
---------------------
- PortfolioConstruction.md / StrategyModel.md 等の設計資料に基づく関数が多く含まれます（リポジトリに含めている場合は参照してください）。
- DuckDB スキーマ（prices_daily / raw_financials / raw_news 等）に合わせてデータ投入を行うことでリサーチ・AI 機能が利用可能です。

サンプル実行フロー（ローカル開発向け）
-----------------------------------
1. .env を作成（python -m kabusys.config_setup）
2. validate_config で問題がないか確認（python -m kabusys.validate_config）
3. まずは監視を試す（別ターミナルで）
   python -m kabusys.run_monitoring
4. 実行エンジンを paper_trading モードで起動して挙動を確認
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
5. ペーパートレード検証レポートを生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
この README はコードベースからの抜粋説明です。実際のライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ / 開発者向けノート
----------------------------
- 開発者は config.py の自動 .env 読み込みや Settings クラスを活用してください。
- テスト時に自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI API 呼び出し部分は再試行・フォールバックロジックを含みますが、利用状況に応じてレート制御やエラーハンドリングの強化を検討してください。

以上。必要であれば各モジュールの API 使用例や詳細な運用手順（systemd/cron での起動、Docker 化、監視ダッシュボード利用方法等）を追記します。どの情報を優先して追記しましょうか？