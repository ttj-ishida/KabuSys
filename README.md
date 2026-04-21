# KabuSys

バージョン: 0.1.0

日本株自動売買および関連処理のためのモジュール群。発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュース NLP / レジーム判定、各種ユーティリティ・ツールを含みます。

以下はコードベースの README。プロジェクトを起動・運用する上で必要な概要／セットアップ／使い方をまとめています。

---

## プロジェクト概要

KabuSys は日本株自動売買に関するロジックをモジュール化したライブラリ兼実行スクリプト群です。主な機能は次の通りです。

- ExecutionEngine（発注実行）:
  - ブローカークライアントを通じた注文管理、リスク管理、オーダー対比（reconciler）等。
  - 本番/ペーパートレーディングを環境変数で切替可能（`KABUSYS_ENV`）。
- Monitoring:
  - システム稼働監視（CPU/メモリ/ディスク、Execution プロセス監視）、注文ログ監視、リスク監視（ドローダウン・ポジション上限）等。
  - Kill Switch（条件に達した場合に `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送る）。
- Portfolio construction:
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクター上限チェック、レジーム乗数などの純粋関数群。
- Research:
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）、将来リターン・IC 計算、統計サマリ。
- AI（OpenAI）:
  - ニュース記事のセンチメントスコアリング（news_nlp）、マクロ + ETF MA を統合した市場レジーム判定（regime_detector）。
- ツール:
  - paper_trading の検証レポート生成スクリプトなど。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（デーモンとしてスレッド実行）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - 対話式 .env 生成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- モジュール/API（プログラムから利用）
  - kabusys.portfolio.* : 候補選定・重み計算・ポジションサイズ計算・リスク調整
  - kabusys.research.* : ファクター計算 / forward returns / IC / summary
  - kabusys.ai.score_news : ニュース NLP スコア付与（OpenAI 必須）
  - kabusys.ai.score_regime : 市場レジーム判定（OpenAI 必須）
- ツール
  - python -m kabusys.tools.paper_verification_report : ペーパー取引検証レポート生成

---

## 前提・依存関係（最小限）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合、任意）
- OS: Linux / macOS / Windows（プロセス優先度設定等で差異あり）

必要なパッケージはプロジェクトの requirements ファイル（存在する場合）やドキュメントに従ってインストールしてください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の fill モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

注意: config.py は `.env` と `.env.local` を自動読み込みします（プロジェクトルートが検出可能な場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は duckdb, psutil, openai 等を個別インストール）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動作成: .env.example を参考にして `.env` を作成
5. 設定を検証
   - python -m kabusys.validate_config
   - 問題があれば修正。`--strict` を付けると警告も失敗扱いになります。
6. 必要に応じてデータディレクトリ（data/）やログディレクトリ（logs/）の権限を確認

注意: 実行スクリプト（run_execution / run_monitoring）は起動時に必要な DB テーブルを作成（マイグレーション含む）します。

---

## 実行方法（基本）

- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 動作: 設定に応じて本番 DB または paper_trading 用 DB を使用。プロセス優先度を high に設定し、ExecutionEngine.run_session() をデーモンスレッドで実行します。
  - 停止: 実行中にプロジェクトルートの data/stop_requested.flag を作成すると安全に停止します。Kill Switch により data/kill.flag が書かれると、次のチェックで停止されます。

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存しません）。
  - 停止: data/stop_requested.flag を作成するとループを終了します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI 関連（プログラムから呼ぶ場合）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.score_regime(conn, target_date, api_key=None)
  - いずれも `OpenAI` クライアント用 API キー（OPENAI_API_KEY）が必要（引数で直接渡すことも可）。

- Research / Portfolio（ライブラリ呼び出し）
  - 例: from kabusys.research import calc_momentum; 結果は DuckDB 接続を与えて呼び出す
  - ポートフォリオ関数は純粋関数で副作用なし（テストや別ワークフローで再利用しやすい）

---

## 運用上の注意

- Kill Switch と停止フラグ
  - KillSwitch（データ/kill.flag）: RiskMonitor 等が条件に達した場合に作成され、ExecutionEngine を停止させるために使います。
  - stop_requested.flag はローカル運用者がスクリプトを安全に停止したいときに使うフラグです。
- ログ
  - デフォルトは logs/ に日次ローテートで保存（TimedRotatingFileHandler）。`LOG_DIR` で変更可能。
- 権限
  - プロセス優先度 / CPU affinity の設定には管理者権限が必要な場合があります。設定失敗時は警告を出してスキップします。
- DB マイグレーション
  - run_* スクリプトは起動時に監視用テーブル（monitoring_db.init_monitoring_db）を冪等的に作成します。
- 本番環境の注意点
  - KABUSYS_ENV=live の場合、設定値を慎重に確認してください（LINE 通知や KILL_FLAG_CLEAR_ON_START 等に注意）。validate_config による事前チェックを推奨します。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート直下に `src/kabusys` 配下がある構成を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態/データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留注文 / 約定異常など）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag の作成/評価
    - alert_manager.py       — （アラート送信の抽象化・実装はここに）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — BrokerClient の生成（実/Mock の分岐）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に利用する data/（例: monitoring.db, paper_trading.db, kill.flag 等）
  - logs/                    — ログファイル出力先（デフォルト）

（上記は主要ファイルのみ抜粋。実際のファイル一覧はリポジトリ内を参照してください。）

---

## よく使うコマンドまとめ

- .env 作成（対話）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア（プログラム呼び出し例）:
  - from kabusys.ai import score_news
  - score_news(conn, date(2026,4,1), api_key="sk-...")

---

## テスト・開発に関する補足

- 多くの関数は純粋関数（副作用なし）として設計されています（portfolio, research 等）。単体テストが容易です。
- OpenAI 呼び出しや外部 API 呼び出し部分は内部で分離されており、テスト時はモックしやすい設計（例: news_nlp._call_openai_api をパッチ等で差替え）。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合スキップされます（パッケージ配布後の挙動に配慮）。

---

## ライセンス / 注意事項

- この README はコードベースの説明を目的としています。運用・自動発注システムの本番利用に際しては十分な検証、リスク管理、法令順守を行ってください。
- `.env` は機密情報を含むため絶対にリポジトリへコミットしないでください。

---

不明点や README に追記してほしい項目があれば教えてください。実行例や環境別の運用手順（systemd/cron/監視ダッシュボードへの接続など）も必要であれば追加で記載します。