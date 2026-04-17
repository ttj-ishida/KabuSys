# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。  
本 README ではプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

注意：ここでの説明はソースコード（src/kabusys 以下）の挙動に基づき記載しています。実行前に必ず設定検証（validate_config）を行ってください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）の起動・運用（本番 / ペーパートレード切替対応）
- 監視（Monitoring）: システム状態・注文状況・リスク監視、Kill Switch による安全停止
- ポートフォリオ構築（候補選定、配分計算、ポジション決定）
- リサーチ（ファクター計算、将来リターン、IC計算など）
- AI 統合（OpenAI を使ったニュース NLP、マクロレジーム判定）
- ユーティリティ（プロセス優先度設定、.env 対話式セットアップ、設定検証、レポート出力など）

設計上の特徴：
- 環境変数 / .env による設定管理（自動ロード機能あり）
- 本番 DB とペーパートレード DB の分離（paper_trading モード）
- DuckDB を解析用 DB、SQLite を監視 / 履歴用 DB として併用
- OpenAI API 呼び出しは失敗時にフェイルセーフ動作（スコア=0やスキップ）する設計

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行 / 監視
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に出力（本番 DB と分離）
    - 停止制御は data/stop_requested.flag や data/kill.flag / data/execution.pid を利用
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用

- モニタリング詳細
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの存在チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: ルールに基づいて data/kill.flag を書き込み、ExecutionEngine 停止信号を出す
  - AlertManager（実装ファイル参照）を用いた通知（LINE 等に統合可能）

- ポートフォリオ / リスク
  - 候補選定（スコア順）、等重・スコア加重配分
  - セクター上限適用、レジーム乗数
  - 発注株数決定（リスクベース、等分配、スコア重み）、単元株丸め、aggregate cap 調整

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Spearman）計算、統計サマリ

- AI（OpenAI）
  - news_nlp: ニュースを集約し LLM で銘柄別センチメントを算出して ai_scores に保存
  - regime_detector: マクロニュース + ETF MA200 を組み合わせて市場レジーム判定と保存

- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## セットアップ手順（ローカル開発想定）

前提: Python 3.10+ を推奨（Union Types, 型注釈等を使用しています）。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（任意: config YAML 検証のため）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: sqlite3 は標準ライブラリです。requirements.txt は付属していない場合があるため、上記パッケージをプロジェクトの実装に合わせて用意してください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考に）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要に応じて作成・権限設定してください。
   - 例: mkdir -p data

---

## 使い方（主なコマンド）

- 環境変数自動ロードについて
  - 起動時、プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から .env を自動読み込みします。
  - OS 環境変数は保護され、.env によって上書きされません（ただし .env.local は override=True で読み込まれます）。
  - 自動ロードを無効化するには:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も failure 扱いになります。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV によって paper_trading モードであれば MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 実行中は data/execution.pid に PID を書く（設定で変更可能）
    - 停止フラグ: data/stop_requested.flag を置くと安全に停止します（存在時は起動しない/停止する）
    - Kill Switch（data/kill.flag）が存在すると ExecutionEngine を停止させる設計になっています

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - 監視は常に設定された本番 sqlite_path（SQLITE_PATH）を使用します（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能

- ライブラリ的な利用
  - 研究（research）や AI 機能はモジュール関数としても利用できます（例）:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - from kabusys.ai import score_news  # ニュース NLP の公開 API
    - kabusys.portfolio.* など

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB 関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

- ログ / 実行制御
  - LOG_LEVEL (default: INFO)
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

- 監視
  - MONITOR_POLL_INTERVAL（秒） — run_monitoring でのポーリング間隔（例: 30）

- OpenAI
  - OPENAI_API_KEY — AI モジュール（news_nlp, regime_detector）で使用

- その他
  - PAPER_FILL_MODE（paper_trading の MockBroker の fill モード: instant|partial|never|reject）

---

## 注意点・運用上のポイント

- 監視（run_monitoring）は監視用 SQLite（SQLITE_PATH）を使用します。監視は常に本番 sqlite_path を参照するので運用時は注意してください。
- ペーパートレードは paper_trading 用の専用 DB に分離され、本番 DB を汚すことはありません。
- Kill Switch（data/kill.flag）を利用することでリモートから実行を止められます。KILL_FLAG_CLEAR_ON_START が 1 だと起動時にこれを自動削除しますが、本番では危険です（推奨は 0）。
- OpenAI を使う機能は API キーが必要です。API 呼び出しはリトライやフォールバック（0.0 など）を組み込んでいますが、API 使用時のコスト・レイテンシには注意してください。
- config/*.yaml の存在やフォーマットは validate_config でチェックできます。PyYAML がないと YAML 内容検証はスキップされます（その場合は警告）。

---

## ディレクトリ構成（主なファイル / モジュール）

（ルート: src/kabusys/ 以下）

- __init__.py
- config.py — 環境変数/.env の読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（概略）:

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py — マクロ+MA200 でレジーム判定
- monitoring/
  - monitoring_db.py — SQLite を使った永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — 通知管理（実装ファイル参照）
- execution/ (発注ロジック関連)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム、バリュー、ボラティリティ計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（その他、config/*.yaml のテンプレートや data/ ディレクトリなどが想定されます）

---

## トラブルシュート（よくある事例）

- .env が自動ロードされない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が set されていないか確認
  - プロジェクトルート（.git または pyproject.toml）が見つからない場合、自動ロードはスキップされます

- validate_config が YAML をパースできない／スキップする:
  - PyYAML がインストールされていないと YAML 検証はスキップされ、警告が出ます。pip install PyYAML を検討してください

- OpenAI 呼び出しが失敗して処理が止まる:
  - 実装は 429 / タイムアウト / 5xx に対して指数バックオフとリトライを行い、最終的にフォールバック（0 またはスキップ）する設計です。API キーとレート制限を確認してください

- Execution 起動後すぐに停止する（stop flag）:
  - data/stop_requested.flag が存在するとエンジンは起動しません。不要なら削除してください

---

## ライセンス・貢献

- 本 README はソースコード（コメント）から作成したドキュメントです。実運用する場合はセキュリティ（秘密情報の管理）、バックアップ、監視、アラートの設計を十分に行ってください。
- 貢献・改修は各ファイルの設計方針コメントに従って行ってください。ユニットテストや手動検証を忘れずに。

---

必要であれば README.md に含めるサンプル .env のテンプレートや起動例（systemd ユニット例、Dockerfile 等）も作成します。どの情報を追記したいか教えてください。