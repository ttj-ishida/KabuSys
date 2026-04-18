# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群）。  
このREADMEはコードベース（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ方法・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を支援する Python モジュール群です。  
主な目的は以下です:

- 戦略実行（ExecutionEngine）
- システム監視（Monitoring）
- ペーパートレード検証（Paper Trading）
- ポートフォリオ構築・位置量計算（Portfolio Construction）
- ファクター計算・研究（Research / Factor）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- 環境設定ウィザード・設定検証ツール

設計方針として、外部 API へのアクセスは必要最小限に抑えられ、DuckDB / SQLite を用いたローカル DB を中心に動作します。Production / Paper 環境の分離やフェイルセーフ（API失敗時のフォールバック）等の配慮があります。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、専用の paper_trading DB を使って本番 DB と完全分離
  - PID / stop フラグ管理

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で調整可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring DB）へ永続化

- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / MonitoringDB
  - リスクイベントやダッシュボードの永続化、kill.flag による Execution 停止の仕組み

- portfolio パッケージ
  - 銘柄選定、等ウェイト・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算

- research パッケージ
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等

- ai パッケージ
  - ニュース NLP による銘柄ごとのセンチメント評価（OpenAI 使用）
  - 市場レジーム判定（ETF の MA と LLM センチメントの合成）

- tools
  - paper_verification_report: ペーパートレード DB から検証レポート生成（稼働率・約定率・レイテンシ等の指標）

- 設定関連
  - config_setup.py: 対話式に `.env` を生成・更新するウィザード
  - validate_config.py: 起動前に環境変数や config/*.yaml の妥当性を検証する CLI

- utils
  - ロギング設定、プロセス優先度設定、ユーティリティ

---

## 必要条件（推奨）

- Python 3.10+
  - 型注釈（| 演算子等）を使用しているため Python 3.10 以上を推奨します
- 主な Python パッケージ（必要に応じてインストール）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（validate_config の YAML 検証を行う場合）
  - 例: pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt は含まれていないため利用する機能に応じて依存を追加してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. Python 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/Mac)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

4. .env の作成（必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに `.env` を作成（.env.example を参照）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリ権限を確認
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - `LOG_DIR` 環境変数で変更可

7. OpenAI を使う機能を実行する場合:
   - 環境変数 `OPENAI_API_KEY` を設定する（または該当関数に api_key を渡す）

---

## 使い方（起動とツール）

基本的にはモジュールを直接実行します。

- ExecutionEngine を起動する（本番/ペーパートレード共通）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading にすると MockBroker を使い paper_trading 専用 DB を利用
    - 起動前に `data/kill.flag` の扱いや `KILL_FLAG_CLEAR_ON_START` の設定を確認

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は常に「本番用 sqlite_path」を使用（環境に依らず）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると WARNING も失敗扱いで exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 関連（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news（DuckDB 接続と target_date を渡して呼ぶ）
  - kabusys.ai.regime_detector.score_regime（同様）
  - 実行には OPENAI_API_KEY（または api_key 引数）が必要

- ログ
  - setup_logging() を通して統一されたログ出力
  - ログファイル: logs/<app_name>.log（日次ローテーション、30日保持）

- Kill / Stop フラグ
  - ExecutionEngine / monitoring は以下フラグ/ファイルで制御されます:
    - data/kill.flag : KillSwitch による停止指示（ExecutionEngine 側で検出して停止）
    - data/stop_requested.flag : run_* スクリプトでループ終了トリガーとして使用
    - data/execution.pid : PID ファイル（起動時に作成される想定）

---

## 環境変数（主なもの）

必須（起動に必要、validate_config に列挙あり）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション / 設定
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db（paper_trading 用）
- LOG_LEVEL — デフォルト INFO
- LOG_DIR — ログ保存ディレクトリ
- OPENAI_API_KEY — AI 機能実行時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 経由で利用）

詳しいキーやデフォルトは `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成（主要ファイルの説明）

（プロジェクトルート配下に `src/kabusys` が存在する前提）

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 対話式生成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントの取得・書き込み（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - trade_monitor.py — （存在する場合）約定監視ロジック
    - kill_switch.py — kill.flag の書き込み・判定ユーティリティ
    - monitoring_engine.py — Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信用、実装による）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py — 共通ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py

（実際の全ファイルは src/kabusys 配下を参照してください）

---

## よくある注意・トラブルシュート

- Python バージョン
  - 型注釈で 3.10+ 構文を利用しているため、古い Python では動作しません。

- ログディレクトリの作成失敗
  - 権限やパスに問題があるとファイルハンドラ生成をスキップしてコンソール出力のみになります。`LOG_DIR` を指定するかパーミッションを確認してください。

- psutil の権限
  - プロセス優先度 / CPU affinity 設定は権限が不足すると警告が出ます（AccessDenied）。問題なく動作は継続します。

- OpenAI API
  - API 呼び出しはネットワーク・レート制限・5xx を想定してリトライ実装がされていますが、APIキーは必須です。テストでは API 呼び出し部分をモックできます。

- データのルックアヘッド（研究 / AI）
  - research / ai モジュールはルックアヘッドバイアスを防ぐよう設計されています。target_date を明示して実行してください。

- Kill Switch / flag ファイル
  - 本番環境で `KILL_FLAG_CLEAR_ON_START=1` を設定するのは危険（kill.flag が自動でクリアされる）。validate_config は live 環境時に警告します。

---

## 開発者向けメモ

- DB スキーマは monitoring_db.init_monitoring_db() に記載。マイグレーションの最小処理（カラム追加）も実装あり。
- DuckDB は分析用、SQLite は監視/注文履歴用など用途を分離。
- AI 関連は OpenAI の Chat Completions API（gpt-4o-mini 等）を想定。JSON mode を使った厳密な出力を期待している実装。
- 単体テストや CI のために、環境自動ロード（.env 読み込み）は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

---

必要であれば、README に以下を追加できます：
- 具体的な .env.example のテンプレート
- systemd / supervisor 用のサービスユニット例（実運用向け）
- よく使う CLI コマンド集（短い Cheat Sheet）
- テスト実行方法（pytest などがあれば）

ほかに追記したい節（例: デプロイ手順、Dockerfile、CI 設定など）があれば教えてください。