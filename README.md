プロジェクト: KabuSys — 日本株自動売買システム
======================================

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム向けのライブラリ/ツール群です。  
主な目的は以下です。

- 日次・リアルタイムでの市場データ解析（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 発注実行エンジン（本番 / ペーパートレード対応）
- 監視（システム状態・注文状態・リスク監視）と Kill Switch
- AI を使ったニュースセンチメント / レジーム検出（OpenAI）
- ペーパートレード検証レポート作成ツール

機能一覧
--------
- 環境設定管理 (.env 自動読み込み、対話型ウィザード)
  - kabusys.config_setup: .env を対話的に生成/更新
  - 自動読み込みの仕組みはプロジェクトルート（.git / pyproject.toml）を探索
- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml の事前チェック（--strict オプションあり）
- Execution Engine 起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定、pid ファイル管理、stop フラグ検出
- Monitoring 起動スクリプト
  - python -m kabusys.run_monitoring
  - 監視ループ（デフォルト 60 秒）で System / Trade / Risk の監視を実施
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
  - 停止は data/stop_requested.flag により検知
- 監視基盤（SQLite）
  - monitoring_db モジュールで必要テーブルを冪等に初期化・操作
  - system_status / trade_logs / positions / risk_logs / dashboard 等を保持
- Kill Switch
  - リスク閾値超過（ドローダウン、ポジション上限等）で data/kill.flag を書き込む
  - Execution 停止のトリガーとして機能
- ポートフォリオ生成
  - 候補選定、等金額・スコア重み、ポジションサイズ計算、セクター制約、レジーム乗数など
- 研究用モジュール（DuckDB 前提）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリ
- AI モジュール（OpenAI）
  - news_nlp: ニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に書込
  - regime_detector: ETF(1321) の MA とマクロニュースを組合せて市場レジーム判定
  - API 呼び出し失敗や安全性（フェイルセーフ）を考慮した実装
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定レポートを出力

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型ヒントや recent 機能を使用しています）
- DuckDB, sqlite3 は Python パッケージ（duckdb）で利用
- OpenAI を使う場合は openai SDK と API キーが必要
- system の監視機能で psutil を使用

1. リポジトリをクローン / 配置
   - プロジェクトルートには src/、data/、logs/ 等を想定

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 必須: duckdb, psutil
   - OpenAI 機能を使う場合: openai
   - YAML 検証を使う場合: PyYAML（なくても動作するが警告を出す）

3. .env を作成
   - 推奨: 対話ウィザードで作成
     - python -m kabusys.config_setup
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使うときに必要
     - KILL_FLAG_CLEAR_ON_START — 本番で注意: 1 にすると起動時に kill.flag を自動クリア

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

5. データディレクトリ / ログディレクトリの確認
   - デフォルト DB 等は data/ 以下に置かれます。必要に応じて .env でパスを変更してください。
   - ログは logs/<app_name>.log（日時ローテーション、デフォルト30日保持）

基本的な使い方
-------------

.env の作成・更新
- python -m kabusys.config_setup
  - 対話形式で .env を生成します。

設定の検証
- python -m kabusys.validate_config
  - 必須環境変数やファイルパス、YAML のパース確認等を行います。

Execution エンジン起動
- 本番/ペーパートレードを区別して起動します。
- 起動:
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用（data/paper_trading.db）
    - 起動前に data/stop_requested.flag が既にある場合は起動せず終了
    - _EXECUTION_PID を書く / 使用
    - ExecutionEngine は別スレッドで実行され、stop フラグで停止

Monitoring 起動
- python -m kabusys.run_monitoring
  - 監視ループを定期実行（デフォルト 60 秒）
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
  - 停止:
    - data/stop_requested.flag を作成すると監視ループが終了
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用

Kill Switch / 手動停止
- Kill Switch が発動すると data/kill.flag に理由を書き込みます。Execution は kill.flag を検知して停止します。
- kill.flag の自動クリアは危険（本番では KILL_FLAG_CLEAR_ON_START=0 を推奨）
- KillFlag を手動でクリア:
  - rm data/kill.flag またはスクリプトから KillSwitch.clear() を呼ぶ

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）
  - 稼働率・注文成功率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力

AI 機能（news_nlp / regime_detector）
- OPENAI_API_KEY を .env に設定してください。CLI 呼び出し/関数から key を渡すことも可能。
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news と news_symbols を集約して LLM に投げ、ai_scores に保存します。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF(1321) の MA と LLM によるマクロセンチメントを合成して market_regime に保存

ログ設定
- 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を使います
  - ログファイル: logs/<app_name>.log、日次ローテーション、30日保持
  - LOG_DIR 環境変数でログディレクトリを変更可能

ディレクトリ構成
----------------
（主要なファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース→センチメント（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
    - monitoring_engine.py   — 各 Monitor を束ねるランナー
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — （注文関連の監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み / 管理
    - alert_manager.py       — （LINE 等への通知管理）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・資金配分制約
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value の計算
    - feature_exploration.py — 将来リターン・IC・統計
  - utils/
    - logging_setup.py       — ログ共通設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリアや設定ミスが致命傷になります。validate_config での確認を必ず行ってください。
- OpenAI を使う機能は API コストが発生します。API 呼び出し頻度やバッチサイズは設定済みの定数で制御されていますが、運用前に確認してください。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログディレクトリ / DB の親ディレクトリが存在しない場合、validate_config が警告します。起動時に自動作成される場合もありますが、適切なパーミッションを事前に確認してください。

トラブルシュート（よくある質問）
---------------------------------
- ポーリング間隔を変えたい:
  - export MONITOR_POLL_INTERVAL=30 を設定して run_monitoring を再起動
- Execution が停止しているが PID ファイルが残っている:
  - data/stop_requested.flag や data/kill.flag を確認。必要に応じて clear（手動削除）する
- OpenAI キーがない / 足りない:
  - news_nlp や regime_detector を呼ぶ前に OPENAI_API_KEY を設定してください。未設定だと例外またはスキップ方針の関数があります（関数説明に依存）。

ライセンス・貢献
----------------
- 本 README では明示的なライセンス表記は含めていません。実際のリポジトリでは LICENSE を確認してください。  
- 貢献は Pull Request / Issue を通して行ってください。

付録: よく使うコマンド例
-----------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要なら README を Markdown 形式で整形したり、環境変数一覧やサンプル .env（.env.example 相当）を追記します。どの形式がよいか指示してください。