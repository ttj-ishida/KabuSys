# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群を提供するプロジェクトです。  
主な責務は以下のとおりです。

- シグナル生成・ポートフォリオ構築（ポートフォリオ重み・株数決定）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- 研究用ファクター計算・特徴量解析（DuckDB 経由）
- ニュース NLP を用いたセンチメント評価（OpenAI を利用）
- ペーパートレード用の検証レポート出力ツール

設計方針としては、DB（DuckDB/SQLite）や外部 API（kabuステーション / J-Quants / OpenAI）を明示的に分離し、テストしやすく、フェイルセーフを重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注ロジック、RiskManager、OrderManager、Reconciler）
  - paper_trading モードでは MockBrokerClient を使い `data/paper_trading.db` に記録
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常などの検知）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件達成で `data/kill.flag` を書き込み ExecutionEngine を停止）
  - MonitoringEngine（各 Monitor をまとめて定期実行）
- Portfolio Construction
  - 候補選定、等金額/スコア加重、セクター上限、レジーム乗数、株数計算（単元丸め）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - news_nlp：ニュース記事を OpenAI に送って銘柄別センチメントを ai_scores に格納
  - regime_detector：ETF の MA とマクロニュースを組み合わせて市場レジーム判定
- Tools
  - paper_verification_report：ペーパートレードの検証レポート生成 CLI
- 設定・検証
  - config_setup：.env を対話式で生成/更新するウィザード
  - validate_config：起動前チェック（必須環境変数、config/*.yaml、パス等）

---

## 必要条件（推奨）

- Python 3.10+（型ヒントでの Union 演算子等を想定）
- 必要ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に任意で必要）
- OS: Linux / macOS / Windows（プロセス優先度と CPU affinity は OS に依存）

（実際の依存パッケージはプロジェクトの requirements.txt / pyproject.toml を確認してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - この README 前提: プロジェクトルートに `src/` がある構成

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージインストール
   - pip install -r requirements.txt
   - もし requirements.txt が無ければ少なくとも `duckdb psutil openai` をインストールしてください。
   - PyYAML は `python -m kabusys.validate_config` の YAML 検証に必要（任意）。

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OpenAI を使う場合は OPENAI_API_KEY を環境変数に設定（config_setup では扱わないため export 等で設定）
   - 手動で設定する場合は .env.example を参考に `.env` を作成してください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution/run_monitoring 起動時に必要テーブルは自動で作成されます（monitoring_db.init_monitoring_db）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合は MockBrokerClient を利用し DB は `PAPER_TRADING_SQLITE_PATH` を使用
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill flag クリアを許可するか（0/1、デフォルト 0）

---

## 使い方（起動・CLI）

### 1) 実行エンジン（ExecutionEngine）を起動
- デフォルト（本番 or 開発モードは KABUSYS_ENV に依る）:
  - python -m kabusys.run_execution
- ペーパートレードで起動する例:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - この場合、paper_trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`) に取引ログ等を記録します。
- 起動時、優先度を "high" に設定し PID ファイル（data/execution.pid など）を書きます。
- 停止は `data/stop_requested.flag` を作成するか、ExecutionEngine 内部ロジックに従って `data/kill.flag` が書かれると停止します。

### 2) 監視ループを起動
- python -m kabusys.run_monitoring
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は本番 sqlite_path を環境にかかわらず使用します（monitoring DB は `SQLITE_PATH`）。
- 停止フラグ: プロジェクトルートの `data/stop_requested.flag` が存在するとループを終了します。

### 3) 設定ウィザード / 検証
- .env 作成・更新: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1

### 4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

### 5) AI 系（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
- ニューススコアリング: kabusys.ai.score_news を呼ぶ（スクリプト内の API を参照）
- レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ

---

## 運用上の注意点

- 本番で `KABUSYS_ENV=live` を設定すると実際に発注が行われます。設定値・通知設定（LINE など）を十分確認してください。
- Kill Switch（`data/kill.flag`）は危険な操作です。`KILL_FLAG_CLEAR_ON_START=1` は本番では推奨しません。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリは `LOG_DIR` 環境変数で上書き可能。
- OpenAI 使用時は API レートやコストに注意してください。news_nlp はバッチ処理・再試行ロジックを持ちますが、キー管理は厳格に。

---

## ディレクトリ構成（主要ファイル / モジュール）

以下は src/kabusys の主要なモジュールと役割です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/ — 発注周り（Engine、OrderManager、BrokerFactory 等）
  - monitoring/
    - monitoring_db.py — 監視 DB スキーマ/永続層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注/約定ログ監視（実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限制御
    - kill_switch.py — フラグ書き込みによる停止
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （通知マネージャ、実装による）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算、投下資金スケーリング、単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（各フォルダ内にはさらに補助的なモジュールが存在します。実装の詳細は該当ファイルを参照してください）

---

## 開発・テストのヒント

- 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定すると無効化できます（テスト時に有用）。
- DuckDB を利用した研究関数は副作用がほぼない純粋関数群です。単体テストしやすい設計になっています。
- OpenAI 呼び出し部分は `_call_openai_api` を patch してモック化することでユニットテストが可能です（score_news / regime_detector に採用）。

---

README は以上です。必要であれば以下の追加情報を作成します。

- 詳細な起動例（systemd / supervisor / Docker Compose でのデプロイ手順）
- 各設定項目のデフォルト値一覧（表形式）
- 主要 CLI のサンプル出力例

どれが必要か教えてください。