# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買プラットフォームの一部実装例です。ポートフォリオ構築、ポジションサイズ計算、監視・アラート、ExecutionEngine 起動スクリプト、ペーパートレード用分離 DB、AI（OpenAI）を用いたニュース NLP / レジーム判定などを含みます。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の README です。

---

## プロジェクト概要

KabuSys は以下の機能群を持つモジュール群から成る、自動売買システムの骨格実装です。

- 戦略研究用のファクター計算（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定、重み付け、位置サイズ決定）
- ExecutionEngine（ブローカークライアント経由の発注ロジック、ペーパートレード対応）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- AI モジュール（OpenAI を用いたニュースのセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- 運用支援ツール（Paper Trading の検証レポートなど）

設計方針として、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時のフォールバック）、冪等性（DB書込み）に配慮されています。

---

## 主な機能一覧

- 環境設定
  - 対話式 .env 作成/更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- Execution & Monitoring
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite に分離して記録
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
    - 監視は常に本番の sqlite_path を参照（環境に依らず）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
  - RiskMonitor（ドローダウン、ポジション上限監視、リスクログ記録）
  - MonitoringDB（SQLite を用いた監視ログ永続化）

- ポートフォリオ
  - 候補選定、等重・スコア重み付け
  - セクター集中制限の適用
  - ポジションサイズ計算（単元株丸め、risk_based/equal/score ライター）

- 研究・分析
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns、IC 計算、統計サマリー）
  - DuckDB を用いた高速分析

- AI（OpenAI）
  - ニュース NLP（raw_news を集約して LLM でセンチメント評価 → ai_scores に書込）
  - レジーム判定（ETF MA と LLM マクロセンチメントの合成）
  - API 呼び出しはリトライ・クリッピング・バリデーションなどの堅牢化実装済み

- 運用ツール
  - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py

---

## 前提・依存関係

- Python 3.9+
- 必須パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
- 任意（検証・補助）
  - PyYAML（config/*.yaml の構文検証に使用。なくても動作しますが警告が出ます）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt を用意していない場合:
pip install duckdb psutil openai
# 開発時に PyYAML が欲しい場合
pip install pyyaml
```

（リポジトリに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / DB
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定動作）

- ログ / 実行制御
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

- OpenAI
  - OPENAI_API_KEY（AI モジュールが必要な場合）

- 監視ポーリング間隔
  - MONITOR_POLL_INTERVAL（秒。run_monitoring で上書き可能。デフォルト 60）

---

## セットアップ手順（初期）

1. リポジトリをクローンして仮想環境を作成・有効化し、依存パッケージをインストール。

2. 対話式に .env を作成（推奨）
```
python -m kabusys.config_setup
```
ウィザードに従い必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力して .env を生成します。

3. 設定の検証
```
python -m kabusys.validate_config
# 警告も厳密にチェックしたい場合:
python -m kabusys.validate_config --strict
```
exit code 0 が成功、1 が失敗（エラー／--strict 時の警告）です。

4. データディレクトリなど必要なディレクトリは自動作成される実装になっていますが、権限等で問題がある場合は手動で作成してください:
- data/
- logs/

---

## 実行方法（運用）

- ExecutionEngine（発注エンジン）を起動:
```
python -m kabusys.run_execution
```
KABUSYS_ENV が `paper_trading` の場合は mock broker が利用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。起動時に data/stop_requested.flag が存在すると起動をキャンセルします。

- Monitoring（監視ループ）を起動:
```
python -m kabusys.run_monitoring
```
MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）。

監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番 DB を参照する仕様に注意）。

- Kill Switch/停止制御
  - kill flag の書き込みは KillSwitch（監視側）で行われます。data/kill.flag が書かれると、ExecutionEngine 起動時や運用側でこれを検出して停止できます。
  - 手動で停止フラグを立てるには（運用者の判断で）、data/kill.flag を作成してください。Clearing は `KillSwitch.clear()` を使うか手動で削除します。
  - run_execution/run_monitoring は data/stop_requested.flag を見てループ停止・起動中止を行います。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
主要指標（稼働率、注文成功率、P95 レイテンシ等）を評価し PASS/FAIL を出力します。

---

## 使い方ポイント・運用注意

- KABUSYS_ENV の違い:
  - development: 開発用（発注なし等の振る舞い）
  - paper_trading: 発注はモック、発注ログは paper_trading 専用 DB に保存（本番 DB と分離）
  - live: 本番

- 監視は本番の監視 DB（Settings.sqlite_path）を参照します。ペーパートレード中でも監視は本番 DB を使う設計です（意図的）。

- OpenAI を使う AI 機能を有効にするには OPENAI_API_KEY を設定してください。API 呼び出しはリトライロジックや応答検証を行っていますが、鍵のレート制限やコストには注意してください。

- ログ:
  - 標準で stdout に出力され、ファイルは logs/<app_name>.log に日次ローテーションで保存されます（ログディレクトリ作成に失敗した場合はファイル出力は無効化されます）。
  - setup_logging() をすべての起動スクリプトで呼び出しているため、ログ設定は統一されています。

- プロセス優先度:
  - run_execution と run_monitoring の開始時に set_process_priority("high") を呼び出します。psutil のパーミッション制限により設定できない場合は警告が出て続行します。

---

## 主要スクリプト一覧（CLI）

- python -m kabusys.config_setup
  - .env 対話式生成
- python -m kabusys.validate_config [--strict]
  - 設定検証
- python -m kabusys.run_execution
  - ExecutionEngine 起動（デーモン化は CLI 側で行ってください）
- python -m kabusys.run_monitoring
  - 監視ループ起動
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - Paper Trading レポート生成

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数 / .env 自動ロード / デフォルト）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（pid / stop flag 管理, paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動
  - utils/
    - logging_setup.py: ロギング設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py: SQLite スキーマ初期化・永続化 API
    - system_monitor.py: システム・データ鮮度監視
    - risk_monitor.py: ドローダウン / ポジション監視
    - kill_switch.py: kill.flag の書き込み/管理
    - monitoring_engine.py: 各モニタを束ねるエンジン
    - ...（alert_manager 等がある想定）
  - execution/
    - execution_engine.py, order_manager.py, broker_factory.py, etc.（発注ロジック）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・投下資金制限
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py: forward returns, IC, summary
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI）
    - regime_detector.py: レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート
  - data/ (ランタイムで使用する、デフォルトパス)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード)
    - stop_requested.flag, kill.flag, execution.pid などのフラグ/PID ファイルを想定

（上記は主要ファイルの抜粋です。実際のファイルツリーはリポジトリ内を参照してください）

---

## 開発者向けメモ

- DuckDB 接続を受け取って計算する設計のため、研究・分析コードは本番データベースに直接書き込まない設計になっています（読み取り専用）。
- ai モジュール群は OpenAI SDK の変更に影響を受けるため、API 呼び出し部分は簡単に差し替えられるように設計されています（テストでのモック用フックあり）。
- DB スキーマのマイグレーション処理（列追加など）は init_monitoring_db 内に簡易対応が含まれています。

---

## よくある質問 / トラブルシューティング

- .env が自動ロードされない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認してください。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。

- OpenAI の呼び出しが失敗する:
  - OPENAI_API_KEY が設定されているか確認。レート制限やタイムアウトはリトライロジックがあるものの、API のエラーやコストに注意してください。

- ログファイルが生成されない:
  - logs/ ディレクトリ作成に失敗している可能性があります。起動ユーザーに対してログディレクトリの書き込み権限があるか確認してください。作成失敗時はコンソール（stdout）のみ出力されます。

---

この README はコードベースの主要点をまとめたものです。詳細な実装・拡張方法は各モジュールの docstring / コメントを参照してください。質問や追加で README に入れてほしい項目があれば教えてください。