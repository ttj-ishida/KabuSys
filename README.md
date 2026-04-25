# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・分析・AI 補助モジュールを含むモジュール群で構成されています。設計方針として、実運用で必要なフェイルセーフ（データ分離、Kill Switch、ログ・監視、リトライなど）を備えつつ、研究用の DuckDB ベース分析と発注ロジックを明確に分離しています。

主な設計ポイント
- 環境変数 / .env による設定（Settings クラス）
- paper_trading モード時は本番 DB と分離（paper_trading 用 SQLite）
- 監視は本番の monitoring DB（monitoring.db）を使用（環境に依らず）
- ロギングは stdout + 日次ローテートファイル（logs/）で統一

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数一覧（主要なもの）
- ディレクトリ構成

---

プロジェクト概要
- 自動売買の核となる ExecutionEngine（発注・注文管理・リスク管理・再整合）を起動するスクリプト（run_execution.py）を備えています。
- System / Trade / Risk を監視し、Kill Switch を書き込む監視機能（run_monitoring.py / monitoring パッケージ）を提供します。
- DuckDB を用いた研究用ファクター計算・特徴量解析（research パッケージ）。
- OpenAI を使ったニュース NLP（ai.news_nlp）や市場レジーム判定（ai.regime_detector）。
- ポートフォリオ構築・サイズ決定ロジックを純粋関数群として提供（portfolio パッケージ）。
- 環境設定ウィザード（config_setup.py）と設定検証ツール（validate_config.py）。
- ペーパートレーディング結果の検証レポート出力ツール（tools.paper_verification_report）。

機能一覧
- 環境設定ウィザード（.env の対話生成 / 更新）
- 設定検証 CLI（必須環境変数や config/*.yaml のチェック）
- 実売・ペーパートレード両対応の Execution 起動（ブローカーファクトリ、リスク管理、order repository）
- 監視サービス（SystemMonitor / TradeMonitor / RiskMonitor）とアラート連携（Kill Switch）
- DuckDB を利用したファクター計算（Momentum / Volatility / Value 等）
- ニュースを LLM に投げるニュース NLP（OpenAI、レスポンスバリデーション・リトライ）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ポートフォリオ構築（候補選定・等重/スコア重み・ポジションサイジング、セクター制限）
- ログ出力（stdout + 日次ローテーション）

セットアップ手順（開発環境向け）
1. リポジトリをクローンし、プロジェクトルートに移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 最低限: duckdb, psutil, openai
   - optional: PyYAML（validate_config の YAML 検証用）
   例:
   - pip install duckdb psutil openai
   - pip install pyyaml   # 任意
4. データディレクトリを作成（必要に応じて）
   - mkdir -p data logs
5. .env を作成
   - python -m kabusys.config_setup
   このウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）。
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番環境でのみ警告も失敗にしたい場合: python -m kabusys.validate_config --strict

使い方（コマンド例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動（実行エンジン）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切り替え:
    - development, paper_trading, live
  - paper_trading の場合、MockBrokerClient が使われ、デフォルトで data/paper_trading.db を使用します
- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は環境に関係なく本番 sqlite_path（デフォルト data/monitoring.db）を使用します
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite
- AI モジュール呼び出し（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定

重要な挙動メモ
- run_execution.py:
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
  - PID ファイルを data/execution.pid に書く（設定で変更可能）
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に settings.sqlite_path（本番 monitoring.db）を使用
  - data/stop_requested.flag が存在すると監視ループを終了
- Kill Switch:
  - RiskMonitor が DRAWDOWN または POSITION_LIMIT を検知すると data/kill.flag を書き込み、ExecutionEngine に停止信号を送る設計
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリア（本番では 0 推奨）

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- データパス / ログ
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト data/paper_trading.db）
  - LOG_DIR — ログファイル出力先（デフォルト logs/）
  - LOG_LEVEL — ログ出力レベル（DEBUG/INFO/…）
- モニタリング・制御
  - MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
  - PID_FILE_PATH, KILL_FLAG_PATH — Settings 経由でカスタム可能
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- Paper trading ふるまい
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                — Settings クラス、.env 自動読み込みロジック
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングスクリプト
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（LLM + MA）
      - __init__.py
    - monitoring/
      - monitoring_db.py       — SQLite テーブル初期化と CRUD ヘルパー
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （発注ログ監視：ソース参照）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - monitoring_engine.py   — 複数モニタを束ねるエンジン
      - kill_switch.py         — kill.flag 書き込みユーティリティ
      - alert_manager.py       — （アラート管理）
    - execution/
      - execution_engine.py    — 実行エンジン（セッション管理）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - research/
      - factor_research.py     — ファクター計算
      - feature_exploration.py — 将来リターン / IC / サマリ
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

補足・運用上の注意
- .env は機密情報を含むため絶対にリポジトリに含めないこと（config_setup の冒頭にも注意書きが入っています）。
- Production（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 時に警告を出します。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみになります。logs/ に書き込み権限が必要です。
- OpenAI API 呼び出しはレート制限・ネットワーク障害対策のためリトライ付き。API キーは環境変数 OPENAI_API_KEY で管理してください。
- モジュールは可能な限り DuckDB / SQLite / Broker を分離しています。研究・検証は DuckDB（ローカルファイル）だけで完結させることができます。

開発者向け
- 各モジュールの関数は docstring に設計意図・入力・出力を明記しています。まずは kabusys/research、kabusys/portfolio の純粋関数群を読むとロジック把握が早いです。
- テストは含まれていませんが、run と同等の機能を単体で呼べる設計になっています（例: MonitoringEngine.run_once を使ったユニットテストが容易）。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

---

README はここまでです。必要であれば以下を追加で作成できます:
- 開発者向けアーキテクチャ図（プロセス間通信 / DB 分離の図）
- 運用手順（デプロイ / systemd / cron 用サンプル unit）
- 追加の environment variable 全リスト表
- 各 CLI の exit code とログ出力サンプル

どれを優先して追加しますか？