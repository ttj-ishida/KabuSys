# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買およびそれを支える監視・リサーチ・ツール群をまとめたパッケージです。  
以下はコードベースから抽出したREADME（日本語）です。

> 注意: 本READMEは src/kabusys 以下の実装に基づいて作成しています。実行前に .env を適切に設定し、依存パッケージをインストールしてください。

---

目次
- プロジェクト概要
- 機能一覧
- 前提 / 必要な依存
- セットアップ手順
- 使い方（主要コマンド / 実行例）
- 環境変数（主なもの）
- 停止/Kill スイッチについて
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システムと、それを支える監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI ベースのニュース評価などのユーティリティを含むパッケージです。
- コア設計方針:
  - 本番/ペーパートレードを環境変数 KABUSYS_ENV で切り替え（development / paper_trading / live）。
  - DB は DuckDB（分析用）と SQLite（監視 / 発注履歴）を使用。
  - .env ファイルの対話式作成・検証ツールを提供。

---

機能一覧
- 実行エンジン起動（ExecutionEngine 起動スクリプト: run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録（本番 DB と分離）。
- 監視ループ起動（SystemMonitor をポーリング: run_monitoring.py）
  - システム稼働状態、データ鮮度、プロセス存在チェックを記録。
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
- Monitoring 層
  - SystemMonitor: CPU/メモリ/ディスク、プロセス・データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常チェック
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 危険時に kill.flag を書き込み停止シグナルを送出
  - MonitoringDB: SQLite に対する永続化レイヤ（schema 初期化・マイグレーション含む）
- Portfolio モジュール
  - 候補選定（select_candidates）
  - 重み計算（等配分・スコア加重）
  - セクターキャップ、レジーム乗数適用
  - ポジションサイズ計算（lot 単位・コストバッファ・スケールダウン）
- Research（DuckDB ベース）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI モジュール
  - news_nlp: ニュース記事を OpenAI に送信して銘柄ごとのセンチメント（ai_score）を算出・保存
  - regime_detector: ETF の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: .env と config/*.yaml の起動前チェック
  - tools/paper_verification_report.py: ペーパートレード検証用レポート生成

---

前提 / 必要な依存
- Python 3.9+（typing のアノテーションや一部の記法より推奨）
- 必要ライブラリ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行いたい場合。なくても動作する）
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（OpenAI API を使用する機能を使う場合）
- システム上でのファイル作成権限（data ディレクトリ等）

インストール（例）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
- 必要パッケージのインストール（例）
  - pip install duckdb psutil openai PyYAML

---

セットアップ手順
1. リポジトリをクローン／配置
2. 仮想環境を作成し、依存パッケージをインストール
3. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が作られます（Git にコミットしないでください）。
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
5. 必要に応じてデータベース初期化（監視 DB 等は各スクリプト起動時に自動で初期化されます）。

---

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu api の base url（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの fill 動作（instant|partial|never|reject）（デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

.env 自動読み込み
- パッケージ起動時、プロジェクトルートが検出できれば .env を自動的に読み込みます（.env.local は上書き）。テスト時などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

使い方（主要コマンド / 実行例）

注意: パッケージはモジュール実行を想定しています。プロジェクトルートで以下を実行してください。

1) 環境設定ウィザード（.env を作成）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

3) ExecutionEngine を起動（トレード実行プロセス）
- python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません（停止フラグ）。
  - 実行中は data/execution.pid に PID が書き込まれます。SystemMonitor はこの PID ファイルをチェックします。

4) 監視ループを起動（SystemMonitor を定期実行）
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）。
- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使って監視ログを保存します（KABUSYS_ENV に依らず）。

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6) AI / レジーム判定・ニューススコア（プログラム API）
- kabusys.ai.score_news(conn, target_date, api_key=...) などの関数を使う（OpenAI API キーが必要）。
- score_regime（regime_detector）も同様に OpenAI API を使用。

ログレベル
- LOG_LEVEL 環境変数でログ出力レベルを設定可能（例: LOG_LEVEL=DEBUG）。

停止（手動）
- ExecutionEngine / 監視ループを安全に止めるにはプロジェクトの data/stop_requested.flag を作成してください（run_execution/run_monitoring はこのファイルを検知して終了します）。
- KillSwitch が致命的条件（ドローダウン・ポジション上限等）を検知すると data/kill.flag へ理由を書き込み、ExecutionEngine 側で停止処理が行われます。

---

停止 / Kill スイッチについて
- KillSwitch（kabusys.monitoring.kill_switch）は条件を満たすと .env の Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記述して停止シグナルを送ります。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアする挙動になります（本番では 0 推奨）。
- 監視ループや実行エンジンの安全な停止は stop_requested.flag（data/stop_requested.flag）を作成することで行えます。

---

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py           — SQLite スキーマ初期化 / DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py           — （ファイル末尾まで未表示のがある可能性あり）
  - execution/                    — ExecutionEngine, order_manager, broker_factory 等（参照実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - data/                         — データディレクトリ（DB ファイル・フラグファイル等を配置）

※ 上記は主要ファイルの抜粋です。細かい実装や追加モジュールはソースを参照してください。

---

補足 / トラブルシューティング
- .env をコミットしないでください（秘密情報が含まれます）。
- PyYAML がインストールされていない場合、validate_config は YAML 内容チェックをスキップします（警告表示）。
- OpenAI 関連は API のレート制限やネットワークエラーを考慮したリトライ実装がありますが、API キーや費用に注意してください。
- psutil によるプロセス優先度設定は権限が必要な場合があります（Linux の nice 値や Windows の優先度設定で AccessDenied が発生することがあります）。

---

以上がこのコードベースに基づく README の要約です。  
必要があれば、各モジュール（ExecutionEngine、OrderRepository、AlertManager など）の使い方や外部ブローカ接続の詳細、設定例（.env のテンプレート）を追加で作成します。どの項目を詳しく掘り下げますか？