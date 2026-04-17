# KabuSys — 日本株自動売買システム

このリポジトリは日本株向け自動売買システム「KabuSys」のコードベースです。  
本 README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意事項
- 本リポジトリは実際の発注・資金を扱う可能性があるため、`.env`（機密情報）を絶対に Git にコミットしないでください。
- Python 3.10+ を想定しています（PEP 604 の型表記などを使用）。

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究用ツール群を含むシステムです。主な機能は次のとおりです。

- 注文エンジン（ExecutionEngine）による発注・注文管理（kabuステーション等のブローカークライアントと連携）
- 監視（Monitoring）コンポーネント：システム状態・注文状況・リスク（ドローダウン等）を定期チェック、ログ永続化、Kill Switch の発動
- ポートフォリオ構築：候補選定・重み計算・リスク調整・株数決定（単元丸め等）
- リサーチ：ファクター計算（モメンタム／バリュー／ボラティリティ）、特徴量探索、IC 計算
- AI モジュール：ニュース記事を LLM（OpenAI）でスコアリング → ai_scores テーブルへ保存、レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ペーパートレード検証レポートなど

設計方針として、実取引ロジックと研究・解析ロジックを分離しており、ペーパートレード時は本番 DB と分離された SQLite を使用できます。

---

## 機能一覧（主要）

- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - interactive ウィザードで .env を生成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - ExecutionEngine の起動/停止監視（run_execution.py）
  - paper_trading 環境では MockBrokerClient を使用し、専用の SQLite（デフォルト: data/paper_trading.db）にログを記録
  - PID / stop フラグを使った安全な停止
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件成立で data/kill.flag を書き込み ExecutionEngine 停止信号を出す
  - MonitoringEngine: 各 Monitor を束ねてポーリング（run_monitoring.py）
- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額／スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ算出（リスクベース、単元丸め、集約上限）
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（スピアマン） / 統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM に渡し銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime: ma200 乖離＋マクロ NLP を合成して market_regime を判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

---

## 必要な依存パッケージ（主なもの）

以下は主要ランタイム依存です。実環境では requirements.txt を用意して pip 等で管理してください。

- Python 3.10+
- duckdb
- psutil
- openai (OpenAI SDK)
- PyYAML（config YAML 検証を行う場合、任意）

インストール例:
- pip install duckdb psutil openai PyYAML

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要 / よく使う:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

設定支援:
- .env をプロジェクトルートに置くことで環境変数が読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## セットアップ手順（推奨順）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の準備（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を生成します（.env はプロジェクトルートに保存されます）
   - 生成後、設定内容を検証:
     - python -m kabusys.validate_config
     - 必須項目の確認や config/*.yaml の存在チェックを行います

4. DB ファイルの用意
   - デフォルトでは必要なファイルは起動時に自動作成／マイグレーションされます（data/ 配下）。
   - ペーパートレードを行う場合は PAPER_TRADING_SQLITE_PATH に指定した DB が使われます。

5. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を .env に設定
   - AI 機能（news_nlp、regime_detector）は API キーが必須です

---

## 使い方（主なコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60秒）
    - run_monitoring は監視用 SQLite（Settings.sqlite_path）を常に本番パスで使用します
    - 停止: data/stop_requested.flag を作成するとループが安全に終了します

- Execution エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と分離）
    - 実行中の PID ファイルは data/execution.pid（デフォルト）に書き込まれます
    - 停止: data/stop_requested.flag を作成するとエンジンに停止要求が送られます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db PATH でデータベースを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（プログラム的に）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り DB のテーブル（raw_news, prices_daily 等）を参照します

注意: stop/kill フラグ
- 停止フラグ:
  - data/stop_requested.flag を作ると run_monitoring/run_execution が検知して安全に停止します
- Kill Switch:
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアされると危険）

---

## 監視関連の設定（ポイント）

- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- Monitoring は Settings.env にかかわらず本番 sqlite_path を使用してログを残す設計
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用（本番 DB と分離）

---

## 主要なファイル / ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
- src/kabusys/ai/
  - news_nlp.py                   — ニュース記事を OpenAI でスコアリング
  - regime_detector.py            — 市場レジーム判定（ma200 + マクロ NLP）
- src/kabusys/monitoring/
  - monitoring_db.py              — SQLite 永続化層（schema + MonitoringDB クラス）
  - system_monitor.py             — システム状態・データ鮮度チェック
  - trade_monitor.py              — 注文滞留・約定異常監視
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag 書き込みロジック
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - alert_manager.py              — （通知管理、実装あり）
- src/kabusys/execution/
  - execution_engine.py / order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py / order_record.py
    — 発注ロジック、ブローカ抽象、注文履歴等（実装は該当ディレクトリ参照）
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/tools/
  - paper_verification_report.py

data/ 配下（ランタイムに自動生成されることが多い）:
- data/kabusys.duckdb (DuckDB のデフォルト)
- data/monitoring.db (監視用 SQLite のデフォルト)
- data/paper_trading.db (ペーパートレード SQLite のデフォルト)
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 開発者向けヒント / 注意点

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出し箇所はリトライ・バックオフやレスポンス検証を実装していますが、API キーやレート制限には注意してください。
- MonitoringDB.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。
- 実運用での本番（KABUSYS_ENV=live）では LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の設定に注意してください（validate_config が警告を出します）。

---

もし README に追加したい内容（例えば API のより詳細な説明、ユニットテストの実行方法、運用フローやデプロイ手順など）があれば教えてください。必要に応じて追記・整備します。