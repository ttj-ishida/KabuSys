README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための軽量なフレームワークです。
主に次の責務を持ちます。

- データ加工・ファクター計算（DuckDB を利用）
- ポートフォリオ構築、ポジションサイジング
- 注文発行 / 発注管理（本番・ペーパートレード切替可）
- システム監視・リスク監視・Kill Switch（異常検知で発注を停止）
- ニュースの NLP によるセンチメント評価（OpenAI）
- 各種運用用ユーティリティ（設定ウィザード / 設定検証 / レポート生成）

主要な設計方針
- 環境変数（.env）中心の構成管理（config モジュール）
- production / paper_trading / development を切り替え可能（KABUSYS_ENV）
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- ログはコンソールと日次ローテーションファイル（logs/*.log）に出力

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）
  - .env を対話式に作成・更新
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数・config/*.yaml 等のチェック
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - Broker クライアント生成（本番 / mock）
  - ExecutionEngine の起動・PID管理・停止フラグ処理
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループ
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能
- 監視永続化（kabusys.monitoring.monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを管理
- リスク監視（kabusys.monitoring.risk_monitor）
  - ドローダウンや保有銘柄数の監視と alert / kill フラグ出力
- Kill Switch（kabusys.monitoring.kill_switch）
  - data/kill.flag による ExecutionEngine 停止制御
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を判定
- ニュース NLP（kabusys.ai.news_nlp）、市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI（gpt-4o-mini）を使ったセンチメント評価・レジーム算出
- Research（kabusys.research.*）
  - ファクター計算（momentum / volatility / value）や IC 計算、forward return 計算
- ポートフォリオ構築（kabusys.portfolio.*）
  - 候補選定、等金額/スコア加重、セクターキャップ、ポジションサイズ計算

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトポリシーに合わせて適切なバージョンを選択）
- OS により追加のネイティブ依存（psutil など）をビルドする必要がある場合あり

1. リポジトリをチェックアウト
   - git clone ... （またはダウンロード）

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 必須パッケージの例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config の YAML 検証で任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動作成:
     - .env.example を参考に .env を作成
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY —（AI 機能を使う場合）OpenAI API キー
   - よく使うオプション:
     - KABUSYS_ENV (development|paper_trading|live) — 実行モード
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）

5. DB・ログディレクトリの用意
   - デフォルトで data/ と logs/ は自動作成されることが多いですが、権限等で失敗する場合は手動で作成してください。

使い方（主なコマンド）
--------------------

- 環境設定ウィザード（.env を作成/更新）
  - python -m kabusys.config_setup

- 設定検証（起動前に実行することを推奨）
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする（CI 用）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番の SQLite は分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません。
    - PID ファイル: data/execution.pid（Settings で変更可）

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 停止:
    - data/stop_requested.flag を作成するとループが終了します
    - または Ctrl+C（KeyboardInterrupt）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定した上で、対応モジュールの公開関数を呼ぶことで実行されます。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - 失敗時はフェイルセーフで処理を継続する設計（スコアを 0 にフォールバック等）

重要な挙動・運用上の注意
-----------------------
- KABUSYS_ENV
  - development: 開発用（通常は発注なし）
  - paper_trading: ペーパートレード（Mock Broker、発注は DB に模擬的に記録）
  - live: 本番（実際に発注するため、設定には細心の注意を払ってください）

- Kill Switch / stop フラグ
  - data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナルを送る運用フラグ（Settings.kill_flag_path でパスを変更可）
  - data/stop_requested.flag: run_execution / run_monitoring のポーリングループを終了させるための停止フラグ
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険（自動クリアされるため意図せず再起動される可能性あり）

- ログ
  - logs/<app_name>.log に日次ローテートで出力（デフォルト 30 日保管）
  - setup_logging() を全エントリポイントで呼ぶことで統一的なログ出力を実現

- DB 初期化
  - monitoring 側は init_monitoring_db() で必要なテーブル・インデックスを冪等に作成します。起動スクリプトが接続時にこれを呼びます。

- ペーパートレードの分離
  - paper_trading モードでは専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番データと完全に分離します。

ディレクトリ構成（抜粋）
-----------------------
以下は主要モジュールと役割の一覧です（src/kabusys 以下）。

- kabusys/
  - __init__.py                     — パッケージ定義（__version__ 等）
  - config.py                       — 環境変数 / Settings
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                   — ニュースセンチメント評価（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py              — SQLite のスキーマ + 永続化ラッパー
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — 発注ログ監視（stale order 等）
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag の管理
    - monitoring_engine.py          — 複数 Monitor の束ね・ポーリング

  - execution/                      — 発注系（Engine / OrderManager / BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数計算・aggregate cap 等
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py        — forward returns / IC / statistics
  - data/                            — （データパイプライン・DB 置き場・スクリプト想定）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

主要な設定（環境変数）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を利用する場合必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、デフォルト 60)
- KILL_FLAG_PATH / PID_FILE_PATH / KILL_FLAG_CLEAR_ON_START — 運用上重要

開発・拡張のヒント
------------------
- DuckDB 接続を受ける研究 / AI モジュールは外部 API を直接叩かない設計（テスト容易）
- OpenAI 呼び出しは個所ごとにラップされており、テスト時の差し替え（patch）が容易
- monitoring_db の init はマイグレーションを簡易的に扱う（カラム追加の互換処理あり）
- ログ・DB パスは Settings 経由で集中管理されるため、環境変数から容易に切替可能

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報は別途 LICENSE ファイルを参照してください。
- バグ報告・機能要望は Issue にお願いします。

お問い合わせ
------------
- 開発に関する質問や運用上の相談はリポジトリの issue または開発チームのルールに従ってください。

以上。README の内容はコードベースの現状に基づく要約です。さらに詳しい実装・API の利用方法（ExecutionEngine の設定項目、Broker の実装仕様、DuckDB のスキーマ、strategy 設定ファイル等）について追記が必要であれば知らせてください。