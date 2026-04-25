# KabuSys

日本株向け自動売買システムのコアライブラリ群です。  
このリポジトリには、実行エンジン（ExecutionEngine）／監視（Monitoring）／ポートフォリオ構築／因子計算／AI を用いたニュース解析など、運用に必要なコンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を組み合わせて日本株の自動売買を支援します。

- 実行エンジン（ExecutionEngine）：ブローカーと連携して注文発行・管理を行う。`paper_trading` モードでは MockBroker を使って本番 DB と分離された専用 SQLite に記録。
- 監視（Monitoring）：システム稼働状況、データ鮮度、注文ログ、リスク指標をポーリングして監視・ログ記録。Kill Switch によるエンジン停止機能を備える。
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群。
- 研究（Research）：DuckDB を用いた因子計算（モメンタム/バリュー/ボラティリティ）や将来リターン計算、IC 計算などの解析ツール。
- AI モジュール（AI）：OpenAI API を用いたニュースセンチメント計算（news_nlp）やマクロ＋ETF を用いた市場レジーム判定（regime_detector）。
- ユーティリティ：ログ設定、プロセス優先度設定、.env ウィザード、設定検証ツールなど。
- ツール：ペーパートレード検証レポート生成スクリプト等。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: `python -m kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、`data/paper_trading.db` に記録
- 監視ループ起動スクリプト（SystemMonitor）: `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）
- 監視 DB 層（SQLite）: テーブル作成・読み書きを行う `monitoring_db.py`
- Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送出
- ポートフォリオ構築: 候補選定・等重/スコア重み・リスクベースの株数決定
- 研究用関数: DuckDB を使った因子計算、forward returns、IC、統計サマリー
- AI 関連:
  - ニュースセンチメント（銘柄別）を OpenAI に問い合わせて `ai_scores` に保存
  - 市場レジーム判定（ETF MA + マクロニュース）を生成して `market_regime` に保存
- ツール: Paper Trading 検証レポート生成 `kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python 環境を準備（推奨: 3.10+）
   - 仮想環境を作成して有効化することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - このリポジトリに requirements.txt が無い場合は、最低限以下をインストールしてください:
     - pip install duckdb psutil openai
     - PyYAML は設定検証で任意に使われます（config/*.yaml を検証する場合）:
       - pip install pyyaml
   - 実際のプロジェクトでは requirements.txt を作成して管理してください。

3. .env を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
   - 重要な環境変数（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（例）
     - OPENAI_API_KEY: OpenAI を使う場合に設定
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリを作成（必要に応じて）
   - data/ や logs/ は自動で作られる場合がありますが、手動で準備しておくと権限問題を避けられます。

---

## 使い方

- 実行エンジン（バックテストではなく実行運用）
  - KABUSYS_ENV を設定した上で起動します。paper_trading の場合は MockBroker を使用し、paper 用 DB に記録されます。
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。終了させたい場合はこのファイルを作成するか、ExecutionEngine 内から Kill Switch を使って `data/kill.flag` を書き込ませます。

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - export MONITOR_POLL_INTERVAL=30

- .env の作成・変更
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB パスは `data/paper_trading.db`。`--db` で明示指定できます。

- AI モジュール（ライブラリ呼び出し例）
  - news_nlp のスコア付け（DuckDB 接続を渡す必要があります）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか OPENAI_API_KEY を env にセット
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 強制停止 / Kill Switch
  - `data/kill.flag` が存在すると ExecutionEngine の起動・継続に影響します。KillSwitch はリスク条件を評価し、フラグを書き込むことがあります。
  - 監視ループや実行スレッドを停止させたい場合は、`data/stop_requested.flag` を作成してください。スクリプトはループ中にこれを検知して安全にシャットダウンします。

---

## 主要な設定（抜粋）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使用する場合に必要
- PAPER_FILL_MODE — paper_trading 時の挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で参照）

（これらは `src/kabusys/config.py` に定義されています。詳細はソースを参照してください。）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・読み書きラッパ
    - system_monitor.py — システム稼働・データ鮮度チェック
    - trade_monitor.py — 注文ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（フラグファイル）
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - alert_manager.py — (アラート送信管理)
  - execution/
    - execution_engine.py — ExecutionEngine（主要ロジック）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — 因子計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - data/ (実行時に使用されるファイル)
    - monitoring.db (default SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - paper_trading.db (paper mode)
    - kill.flag, stop_requested.flag, execution.pid, ...

---

## ログと監視

- ログはデフォルトで `logs/` に日次ローテーションで保存されます（`kabusys.utils.logging_setup`）。
- コンソール出力は stdout に行われます（cron 等で stdout をまとめてリダイレクトする用途に配慮）。
- 監視データは SQLite（`monitoring.db`）に永続化され、`monitoring_db.py` に CRUD 操作を実装しています。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）の設定は慎重に扱ってください。`validate_config` は live の場合にいくつか警告を出します（LINE通知未設定や Kill Flag 自動クリア設定など）。
- OpenAI API を使用する箇所は API エラーやレート制限に対してリトライ・フェイルセーフ実装がありますが、API キーの漏洩などには注意してください。
- paper_trading は本番 DB から分離されますが、設定誤りで本番 DB にアクセスしないよう `.env` の内容をよく確認してください。
- kill.flag / stop_requested.flag による停止フローはファイルベースなので、適切なファイル権限管理を行ってください。

---

## 貢献・開発メモ

- 単体テストや CI は現状明示されていません。関数群は純粋関数や副作用を限定したクラスで構成されているため、ユニットテストの追加は比較的容易です。
- 外部依存（OpenAI / kabu API / J-Quants 等）は抽象化されており、モックやフェイク実装を利用してテスト可能です。

---

README に書かれている以上の細かい挙動や追加設定は、各モジュール（src/kabusys 以下の .py ファイル）内の docstring / コメントに詳述されています。実運用前には `python -m kabusys.validate_config` で設定を検証し、.env を生成/確認した上で起動してください。