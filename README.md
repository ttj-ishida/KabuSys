# KabuSys

日本株向け自動売買システムのパッケージ（ドキュメント版）。このリポジトリはバックテスト/リサーチ/ポートフォリオ構築/Execution および監視周りのユーティリティを含みます。

以下は本コードベースの概要、機能、セットアップ手順、使い方、および主要ディレクトリ構成の説明です。

注意：.env は機密情報（API トークン・パスワード等）を含むため、絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を支援するモジュール群です。主な責務は次のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- 実行エンジン（ExecutionEngine）を通じた注文管理（本番／ペーパー）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- ニュースの NLP（OpenAI を使ったセンチメントスコアリング）と市場レジーム判定
- 構成ウィザード・設定検証・検証レポート等の運用ツール

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行と監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV に応じて実ブローカー／MockBroker を切替
    - paper_trading モードは専用 SQLite（デフォルト: data/paper_trading.db）を使用
  - System / Trade / Risk Monitor（monitoring package）
  - Monitoring 用ループ起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - stop_requested.flag による安全停止

- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 重み算出（等配分 / スコア加重）
  - ポジションサイジング（リスクベース等）
  - セクター上限、レジーム倍率の適用

- 研究・ファクター計算（research package）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（ai.regime_detector）
  - API 呼び出しは冪等、リトライ・バックオフ等の堅牢化

- 運用ツール
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）

---

## 前提・依存関係

- Python 3.10+（typing の | 演算子等を使用）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - PyYAML（config 検証で任意）
- これらは requirements.txt を作成している場合はそこから、なければ手動でインストールしてください。

例（最低限）:
pip install duckdb psutil requests openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または templates を参考に手動で .env を作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトで data/ 以下に DB が配置されます。必要に応じてディレクトリ作成
     - mkdir -p data

7. DB 初期化
   - run_monitoring または run_execution を起動すると内部で監視用 SQLite のスキーマが作成されます（init_monitoring_db により冪等実行されます）。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBroker を使い、本番 DB と分離して data/paper_trading.db を使用
    - live: 本番動作（発注実行）

- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)

- OpenAI
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector が参照）

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- その他
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数。デフォルト 60）
  - PAPER_FILL_MODE（paper_trading 時の模擬約定モード: instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは推奨されません。0/1）

---

## 使い方（主要コマンド例）

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実行エンジン）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は Settings に依らず本番 sqlite_path を使用して監視ログを書きます。
    - 停止は data/stop_requested.flag を作成することで安全に行えます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも参照。

- AI 関連（ニューススコア・レジーム判定）
  - ai.score_news / ai.regime_detector score_regime はコード上の関数呼び出しで利用（CLI は提供されていません）。OPENAI_API_KEY をセットして使います。

---

## 停止・Kill Switch について

- 実行中の ExecutionEngine を外部から停止したい場合:
  - Kill Switch: data/kill.flag に理由テキストを書き込むと評価により Execution を停止する仕組み（KillSwitch）。
  - run_monitoring / monitoring_engine はリスク条件（ドローダウン・ポジション上限など）を評価し、必要に応じて kill.flag を書きます。
  - run_execution / ExecutionEngine は pid ファイルや stop_requested.flag を監視して停止処理を行います。

- stop フラグ
  - run_execution / run_monitoring は data/stop_requested.flag の存在を見てループ終了します（安全なシャットダウン手段）。

- 本番注意
  - KILL_FLAG_CLEAR_ON_START=1 を本番で有効にすると起動時に kill.flag を自動でクリアするため危険です（デフォルト 0 を推奨）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み、自動ロード、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - （ExecutionEngine / OrderManager / BrokerFactory 等 — 発注系ロジック）
  - monitoring/
    - monitoring_db.py (SQLite スキーマ + MonitoringDB)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (LINE 通知)
  - portfolio/
    - portfolio_builder.py (候補選定 / 重み)
    - position_sizing.py (株数計算 / スケールダウン)
    - risk_adjustment.py (セクターキャップ / レジーム乗数)
  - research/
    - factor_research.py (モメンタム・ボラティリティ・バリュー)
    - feature_exploration.py (将来リターン・IC・統計)
  - ai/
    - news_nlp.py (ニュースの NLP スコアリング)
    - regime_detector.py (マクロ + MA を使ったレジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading レポート生成)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity)

---

## 開発者向けメモ / 実装上の注意点

- Settings は .env と OS 環境変数を統合して提供します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードでは本番 DB と切り離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- init_monitoring_db はスキーマを冪等に作るため、運用中の DB へ安全に繰り返し実行できます。既存カラムの簡単なマイグレーション（ALTER TABLE ADD COLUMN）が含まれます。
- OpenAI API を利用する機能はネットワーク／429 等を考慮したリトライロジックと結果のバリデーションを含みますが、API キーは必ず安全な形で設定してください。
- process_priority.set_process_priority はプラットフォーム差（Windows / POSIX）を吸収しますが、権限不足で失敗することがあります（警告ログ）。

---

## トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの特定は .git または pyproject.toml を基準に行います。パッケージ配布後や別パスで実行する場合は環境変数を直接エクスポートしてください。
- run_execution が起動直後に終了する
  - data/stop_requested.flag が既に存在していないか確認してください。
- Monitoring が期待通りのテーブルを書いていない
  - init_monitoring_db は run_monitoring/run_execution の起動時に自動で呼ばれます。DB パスやパーミッションを確認してください。
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY の設定を確認。API エラーはログに出力されます。ローカルではテスト用に呼び出し関数をモックできます（コード上に注釈あり）。

---

必要であれば README に含める具体的な例（.env テンプレート、systemd 用 Unit サンプル、docker-compose 例など）を追記できます。どの情報を追加しますか？