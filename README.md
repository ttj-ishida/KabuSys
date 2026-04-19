KabuSys
=======
バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。  
主な機能は以下の通りです。

- 実行エンジン (ExecutionEngine)
  - ブローカークライアントを用いた発注管理（本番 / ペーパートレード切替対応）
  - リスク管理・注文再調整・約定ログ記録
- 監視 (Monitoring)
  - システム健全性（CPU/メモリ/ディスク・プロセス生存）やデータ鮮度監視
  - 注文滞留・約定異常・ドローダウン監視、Kill Switch（フラグファイルによる停止）
  - 監視ログは SQLite（monitoring.db）に永続化
- ポートフォリオ構築
  - 候補選定、重み計算（等分／スコア加重）、位置サイズ計算、セクター制約など
- 研究（Research）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）計算など
- AI（ニュース NLP / レジーム判定）
  - OpenAI を利用したニュースセンチメント評価、日次レジーム判定
- ツール
  - ペーパートレード検証レポート生成スクリプト等
- 開発者ユーティリティ
  - .env 対話式ウィザード、設定検証 CLI、共通ログ設定、プロセス優先度設定 など

特徴
----
- 本番用/ペーパー用の DB を分離（KABUSYS_ENV により切替）
- DuckDB を用いた分析用テーブル（prices_daily, raw_financials 等）を前提
- OpenAI を用いた自然言語処理（ニュース）連携を組み込み可能
- ログはコンソール + 日次ローテートファイル出力（logs/*.log）
- 設定の自動読み込み（.env / .env.local）機能あり（環境変数優先）
- 監視→Kill Switch→Execution 停止（フラグファイル）という安全回路

必要条件
--------
- Python 3.10 以上（type hint の構文および動作検証に基づく推奨）
- SQLite（Python 標準ライブラリ sqlite3 を使用）
- 追加パッケージ（少なくとも以下をプロジェクトにインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config/*.yaml の検証を行う場合は任意)
- ネットワーク接続（本番 API / OpenAI 利用時）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install pip --upgrade
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. データ / ログディレクトリ作成
   - mkdir -p data logs

5. 初期設定（対話式ウィザード）
   - python -m kabusys.config_setup
     - .env を生成・更新します。
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - KABUSYS_ENV は development / paper_trading / live のいずれか

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

使い方
------
環境変数について（主要なもの）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 利用時の API キー
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）

主要コマンド
- 実行エンジン起動（本番 / ペーパー切替自動）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると停止します。
  - paper_trading 環境では MockBrokerClient を使用し、paper_trading.db に記録します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は monitoring.db（Settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を使用）。

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告でエラー終了します。

- ペーパートレード検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も参照します（オプション: --db が優先）。

ファイルベースの停止 / Kill Switch
- 停止フラグ:
  - data/stop_requested.flag — run_execution/run_monitoring がこれを検出すると停止
- Kill Switch:
  - monitoring がリスク閾値を検出すると data/kill.flag を作成し、ExecutionEngine を停止させます。
  - Settings.kill_flag_clear_on_start=1 により起動時に自動クリア可能（本番では推奨しません）。

ロギング
- setup_logging() によりコンソール出力（stdout）と logs/<app_name>.log（日次ローテート）を設定します。
- ログディレクトリは LOG_DIR 環境変数、引数、またはデフォルト logs/ を使用します。

注意点 / 運用メモ
- 実行時にプロセス優先度設定（高）が行われます（psutil を使用）。権限不足の場合は警告を出してスキップします。
- OpenAI を使う機能（ニュース NLP / レジーム判定）は API キーが必須です。API エラーはリトライやフォールバックの挙動が実装されていますが、鍵がない場合は明示的に失敗します。
- .env の自動読み込みはデフォルトで有効です。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の DB 初期化やマイグレーションは init_monitoring_db() が自動で行います。

ディレクトリ構成（抜粋）
--------------------
（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/               — 発注・実行関連コンポーネント（Engine, Broker, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite ラッパー・マイグレーション
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文監視（滞留・約定異常）
    - risk_monitor.py        — ドローダウン/ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       —（通知管理: LINE 等）
  - portfolio/
    - portfolio_builder.py   — 候補・重み付け
    - position_sizing.py     — 株数決定（lot 単位丸め、aggregate cap）
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - data/                    — 実行時生成される（例: monitoring.db / paper_trading.db / kill.flag 等）
  - logs/                    — ログファイル（出力先）
  - utils/
    - logging_setup.py       — ログ共通設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

ライセンス / 貢献
----------------
（README にライセンス記述が無ければ、プロジェクトのルートにある LICENSE を参照してください。）

問い合わせ / 開発
-----------------
- 新機能やバグ修正は issue / PR で管理してください。
- ローカルでの動作確認には .env を適切に設定し（config_setup を利用）、validate_config で検証してから実行してください。

以上がこのコードベースの概要・セットアップ・使い方です。README に追記してほしい操作手順や、個別モジュールの詳細な API ドキュメントが必要であれば指定してください。