# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の実装を含みます。戦略計算、ポートフォリオ構築、発注エンジン、監視・アラート、ニュース NLP / レジーム判定、検証ツールなどの主要コンポーネントを備えています。

---

## プロジェクト概要

KabuSys は次のような責務を持つコンポーネント群で構成されます。

- ExecutionEngine：ブローカークライアントを通じた発注実行（本番／ペーパートレード対応）
- Monitoring：システム稼働状況・注文ログ・リスク監視・Kill Switch（停止フラグ）管理
- Portfolio：候補選定・重み付け・ポジションサイズ計算・セクター制約などの純粋関数
- Research：DuckDB 上の価格・財務データに基づくファクター計算・解析ツール
- AI：ニュースのセンチメントスコアリング（OpenAI API を利用）と市場レジーム判定
- Tools：ペーパートレード検証レポートや設定ウィザード等のユーティリティ

設計上のポイント：
- 設定は .env ファイルまたは環境変数から読み込む（自動ロード機能あり）。
- DuckDB（分析用）と SQLite（監視・発注履歴用）を使用。
- 本番・ペーパートレードを分離（paper_trading モードは専用 SQLite を使用）。
- OpenAI を使った NLP 機能は API キーを環境変数で供給。

---

## 主な機能一覧

- システム監視（CPU/メモリ/Disk、Execution プロセス死活、データ鮮度）
- 監視ログ永続化（SQLite）
- リスク監視（ドローダウン検出、ポジション上限監視）と Kill Switch（flag による停止）
- 発注エンジン（ブローカーファクトリ、OrderManager、RiskManager、Reconciler 等）
- ポートフォリオ構築（候補選定、等重/スコア重み、リスクベース位置決定、単元丸め）
- ファクター計算（モメンタム、バリュー、ボラティリティ等、DuckDB 利用）
- ニュース NLP（OpenAI による銘柄別センチメントスコア）
- レジーム判定（ETF MA とマクロ NLP を合成）
- ペーパートレード検証レポート生成ツール

---

## 要件（概要）

- Python 3.10+
- ライブラリ（代表）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の詳細検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム差を吸収）

※ requirements.txt はこのリポジトリに含まれていない想定ですが、上記パッケージをインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を生成できます（デフォルトはプロジェクトルートの .env）。
   - あるいは .env を手動で作成（.env.example を参考に）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要なディレクトリ作成（自動でも作られますが事前作成しておくことも可能）
   - data/（SQLite 等の DB、フラグファイル置き場）
   - logs/（ログファイル出力先）

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（主なもの）:
- KABUSYS_ENV — 実行モード：development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合に必要）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログを出力するディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

Kill / Stop 関連:
- デフォルトでフラグファイルはプロジェクト内の data/ 以下に置かれます:
  - data/kill.flag — Kill Switch（監視が条件を満たすとここに理由を書き込む）
  - data/stop_requested.flag — run_* スクリプトが検出して停止する外部ストップフラグ
  - data/execution.pid — ExecutionEngine の PID（run_execution が書き込む）

その他:
- PAPER_FILL_MODE — paper_trading の MockBroker の挙動（instant/partial/never/reject）

---

## 使い方（実行例）

- 環境作成済みか確認したら、.env を用意してから下記コマンドを実行します。

1. 監視プロセス（Monitoring）
   - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
     - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（monitoring は本番 DB を参照する仕様）。
     - 終了方法: Ctrl+C または data/stop_requested.flag を作成しておくとスクリプトが検知して終了します。

2. 発注エンジン（ExecutionEngine）
   - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（data/paper_trading.db）に記録します（本番 DB と完全分離）。
     - run_execution は data/stop_requested.flag を監視し、検知時に Engine.stop() を呼びます。
     - PID ファイル（data/execution.pid）を保持します。

3. 設定検証
   - python -m kabusys.validate_config
     - 警告やエラーを出力し、--strict を付けると警告も失敗扱いで exit(1) になります。

4. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD
     - --db PATH で SQLite DB を明示指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

6. AI 機能（スクリプトから呼び出される想定）
   - OPENAI_API_KEY を設定して、kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使用

---

## ロギング

- 共通の logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定します。
  - ログディレクトリ：LOG_DIR 環境変数またはデフォルト logs/
  - ログファイル名は起動アプリ名（例: execution → logs/execution.log）

---

## ファイルベースの制御フロー

- 停止要求（停止フラグ）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全に停止します。
- Kill Switch:
  - 監視中にリスク条件（ドローダウンやポジション上限）が満たされると、data/kill.flag に理由を書き込みます。Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていると自動クリアしますが、本番では 0 を推奨します。
- PID 管理:
  - run_execution は data/execution.pid を使います。

---

## ディレクトリ構成（主要部分）

以下は主要モジュールの概観です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py       — CPU/メモリ/Disk / データ鮮度 / Execution プロセス監視
    - trade_monitor.py        — （発注ログの監視）※実装ファイルあり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各モニタの統合ポーリング / アラート評価
    - kill_switch.py          — kill.flag の書き込み・管理
    - alert_manager.py        — （通知管理）※実装ファイルあり
  - execution/
    - execution_engine.py     — 発注エンジン本体
    - broker_factory.py       — BrokerClient の生成（本番/Mock）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文履歴 DB レイヤ
    - reconciler.py           — 注文整合処理
    - risk_manager.py         — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・集約制約処理
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC/統計解析ユーティリティ
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）と ai_scores 書き込み
    - regime_detector.py      — レジーム判定（ETF MA + マクロ NLP）
  - data/                      — 実行時生成: DB, flags, pid など（not tracked 推奨）
  - logs/                      — ログ出力先（デフォルト）

（上記は主要ファイルの抜粋です。各サブモジュールに詳細な実装があります。）

---

## 開発・運用上の注意点

- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注記あり）。
- KABUSYS_ENV を `live` にする際は十分に設定を確認してください（LINE 通知設定など）。
- Monitoring は指定された monitoring DB（SQLite）に書き込みを行います。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照する仕様です。
- OpenAI API 呼び出しは外部 API 依存であり、失敗時はフェイルセーフ（0.0 等のフォールバック）する設計ですが、APIキー管理・コストに注意してください。
- プロセス優先度や CPU affinity の設定は OS に依存するため、権限不足時は警告ログを出してスキップします。

---

## よく使うコマンドまとめ

- .env 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 発注エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要であれば README に「環境変数の完全一覧」や「データベーススキーマの詳細」「API の利用手順（OpenAI のレスポンス期待値）」等を追記できます。どの情報をさらに追加しますか？