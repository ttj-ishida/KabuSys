# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群です。  
このREADMEはリポジトリ内の主要スクリプト・モジュールから作成した利用ガイドです。

注意：本リポジトリは複数の外部ライブラリ（duckdb, psutil, openai など）に依存します。実行前に依存関係をインストールしてください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 主要環境変数
- 動作上の注意（Kill Switch 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買エンジン・監視・研究ツール群をまとめたパッケージです。
- 発注ロジック、ポートフォリオ構築、リスク制御、監視（モニタリング）、AI を用いたニュース評価などを含みます。
- DuckDB / SQLite をデータ層に利用し、OpenAI をニュース解析やレジーム判定に利用する拡張を含みます。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 環境に応じて MockBrokerClient を使う（paper_trading）か実ブローカに接続（live）する。
  - paper_trading は本番 DB と分離して data/paper_trading.db を使用（既定）。
  - プロセス優先度を "high" に設定。
- Monitoring サービス（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリングを実行。
  - 監視ログは SQLite（data/monitoring.db）へ保存。MONITOR_POLL_INTERVAL でポーリング間隔を変更可（既定 60 秒）。
  - 停止フラグ（data/stop_requested.flag）でループを終了。
- 設定ウィザード（config_setup.py）
  - 対話式に .env を作成・更新。
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の不足や不整合を起動前に検出。--strict オプションあり。
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率、約定・送信率、レイテンシ等をレポート出力。
- AI 関連
  - ニュース NLP（ai/news_nlp.py）：OpenAI を使ったニュースの銘柄ごとのセンチメント評価と ai_scores テーブルへの書き込み。
  - レジーム判定（ai/regime_detector.py）：ETF の MA とマクロニュースセンチメントを合成して 'bull'/'neutral'/'bear' を判定し保存。
- ポートフォリオ構築ライブラリ（portfolio/）
  - 候補選定、重み付け、セクター制約、ポジションサイズ計算など純粋関数として提供（DB 参照無し）。
- 研究用モジュール（research/）
  - ファクター計算（momentum / value / volatility）、将来リターン、IC 計算、統計サマリーなど（DuckDB 接続を受け取る形）。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）
  - 監視用 DB 操作用ラッパー（monitoring/monitoring_db.py）
  - リスク監視・Kill Switch 機構（monitoring/）

---

セットアップ手順（ローカル開発向け）
1. Python 環境の用意（3.9+ を推奨）
2. 依存関係をインストール
   - 例:
     - pip install duckdb psutil openai
     - PyYAML は validate_config で YAML 検証を行う場合に必要: pip install pyyaml
   - （リポジトリに requirements.txt がある場合はそれを利用）
3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリに例ファイルが無い場合は下記「主要環境変数」を参照）。
4. DB のディレクトリ作成
   - デフォルトは data/*.db。必要ならディレクトリを作成:
     - mkdir -p data
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 本番準備時は --strict を付けて警告も失敗扱いにする: python -m kabusys.validate_config --strict

---

使い方（コマンド例）
- Execution エンジン（本番または paper_trading）
  - 通常起動:
    - python -m kabusys.run_execution
  - paper_trading に切り替える:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在する場合、起動をスキップします。
  - エンジンは data/execution.pid に PID を書きます。
- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を使います（環境に依らず）。
  - 停止:
    - data/stop_requested.flag を作成するとループが終了します（運用側での安全停止）。
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 既定値付き
  - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - OPENAI_API_KEY — OpenAI を使う機能（ai/news_nlp, ai/regime_detector）を使う場合に必要
  - PAPER_FILL_MODE — ペーパートレード時の約定モード（instant / partial / never / reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、既定 60）
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。live では注意）

.env の例（簡易）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

動作上の注意（安全機構）
- Kill Switch
  - RiskMonitor / TradeMonitor / SystemMonitor の結果に基づき、KillSwitch が data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 本番（KABUSYS_ENV=live）では kill.flag 設定に特に注意してください。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- 停止フラグ
  - data/stop_requested.flag を作ると run_monitoring/run_execution が検出して安全に終了します（運用停止用）。
- PID / stale PID
  - Execution は data/execution.pid に PID を書きます。監視側は PID ファイルをチェックし、stale PID を検出して削除・通知します。
- モニタリング DB
  - monitoring 用 DB（SQLite）は init_monitoring_db() でテーブルを作成・簡単なマイグレーションを行います。

---

依存関係（主なもの）
- duckdb — 研究用データベースクエリ
- psutil — プロセス/リソース監視、プロセス優先度操作
- openai — AI 機能（任意、API キーが必要）
- PyYAML — validate_config の YAML 検証で任意で使用

インストール例:
- pip install duckdb psutil openai pyyaml

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings の読み込み・管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュースの LLM によるスコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite による永続化層
    - monitoring_engine.py — Monitor 群の統合ポーリングループ
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（flag ファイル書き込み）
    - alert_manager.py — （通知管理、実装参照）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算、リスク・上限適用
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（リポジトリによってはさらに execution/ data/ strategy/ 等のサブパッケージが存在する想定です）

---

追加のヒント / 推奨運用
- 本番環境（KABUSYS_ENV=live）では .env を慎重に管理し、Git 等にコミットしないでください。
- validate_config を使って起動前に設定やファイルパスの妥当性を確認してください。
- OpenAI を使う処理は API 呼び出しが失敗してもフェイルセーフ（0.0 等で継続）となるよう設計されていますが、APIキーの設定とレートリミット対策は必須です。
- Paper Trading（ペーパートレード）は本番 DB と分離されるため、検証時も本番データの上書き事故を防げます。

---

問題や不足箇所
- この README はソース内コメントと実装を基に作成しました。リポジトリ内に README のテンプレや追加の運用ドキュメントがあればそちらも参照してください。
- 実行に必要な依存パッケージ一覧（requirements.txt）やデフォルトの config/*.yaml の生成スクリプトは環境に依存します。必要に応じて追加で提供してください。

--- 

以上。必要であれば README の内容を実際の README.md 形式へ整形したり、セクションを追記（デプロイ手順、systemd ユニット例、ログ管理方法など）します。どの情報を追記しましょうか？