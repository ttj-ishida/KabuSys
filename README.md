# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買を想定した小規模なトレーディングプラットフォームのコードベースです。戦略・ポートフォリオ構築、発注（実運用 / ペーパートレード）、監視、AI を用いたニュース解析・レジーム判定、解析用ユーティリティなどの機能を含みます。

---

## 概要

主なコンポーネント：

- ExecutionEngine — 発注ロジック / 注文管理 / リスク管理を担う（本番 / ペーパートレード対応）
- Monitoring — システム・発注・リスクを継続監視し、Kill Switch（停止フラグ）やアラートを発生
- Portfolio（ポートフォリオ構築） — 候補選定・重み付け・ポジションサイズ決定・セクター制約等の純粋関数群
- Research — DuckDB を用いたファクター計算や特徴量探索
- AI モジュール — ニュースのセンチメントスコアリング（OpenAI を利用）と市場レジーム判定
- ユーティリティ — ログ設定、プロセス優先度、設定ウィザード / 検証、ツール系スクリプト

設計方針の一部：
- 環境設定は .env ファイル / 環境変数で管理（自動読み込み機能あり）
- ペーパートレードは本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- AI 呼び出しは失敗耐性（リトライ・フォールバック）を持つ
- ログはコンソール + 日次ローテートファイルで管理

---

## 機能一覧（主なもの）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証ツール: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を利用して data/paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は常に production の sqlite_path を参照（環境によらず同じ monitoring DB を使用）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築: 候補選定 / 等金額・スコア加重 / リスクベース配分 / セクターキャップ適用 等
- Research: momentum / volatility / value ファクター計算、将来リターン・IC 計算
- AI: news_nlp.score_news（ニュースセンチメント→ai_scores 書き込み）、regime_detector.score_regime（市場レジーム判定）
- MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブル管理
- Utilities: ログ設定（コンソール + 日次ローテーション）、プロセス優先度設定、CPU affinity（psutil ベース）

---

## 必要条件（概略）

- Python 3.10+
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML (validate_config で config/*.yaml の検証を有効にする場合)
- SQLite（組み込み）、ファイルシステム書き込み権限

requirements.txt はリポジトリに含まれていないため、実行に必要な外部パッケージを pip 等でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化（推奨）
3. 必要パッケージをインストール（上記参照）
4. 初期の環境変数 (.env) を対話式で作成:
   - python -m kabusys.config_setup
   - これにより .env が生成されます（.env は決して Git にコミットしないでください）
5. 設定を検証:
   - python -m kabusys.validate_config
   - 必須環境変数が未設定の場合はエラーになります
6. データディレクトリ作成（必要なら）:
   - デフォルトの SQLite / DuckDB パスは data/ 以下に置く想定です（例: data/monitoring.db, data/kabusys.duckdb）
   - logging 設定は logs/ ディレクトリを使用します（存在しない場合は自動作成を試みます）

主要な必須環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合必須）
主なオプション / 注意項目:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START（本番で 1 にしないこと推奨）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします
- テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine を起動（本番またはペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、ペーパートレード用 DB に記録されます
  - 起動時に data/stop_requested.flag が既にあると起動をスキップ
  - execution は data/execution.pid を生成します（PID 管理）

- Monitoring（継続ポーリング）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
    - 0以下の設定は無効扱いされデフォルト 60 秒にフォールバックします
  - 停止は data/stop_requested.flag を作成するか、プロセスを SIGINT（Ctrl-C）で停止

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

- AI 機能（プログラムから呼び出し）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（引数でも渡せます）
  - regime_detector.score_regime(conn, target_date, api_key=None) も同様

- ログ設定
  - 各起動スクリプトが内部で setup_logging(app_name=...) を呼び出します
  - デフォルトで logs/<app_name>.log に日次ローテーション（30日保持）

---

## ファイル・ディレクトリ構成（抜粋）

プロジェクトのルートは src/kabusys 以下を想定しています。主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env の読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・DB アクセス
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag 制御（ExecutionEngine 停止）
    - monitoring_engine.py   — 複数 monitor を束ねるループ
    - (alert_manager, trade_monitor など 他ファイル)
  - execution/                — 発注エンジン、OrderManager 等（実装多数）
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数計算・aggregate cap
    - risk_adjustment.py      — セクター制約・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value 計算
    - feature_exploration.py  — 将来リターン・IC 等
  - ai/
    - news_nlp.py             — ニュースの LLM ベーススコアリング
    - regime_detector.py      — マクロ + ETF MA でレジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - data/                     — 実行時に生成される想定のフォルダ（DB・フラグ・PID など）
  - logs/                     — ログ出力先（自動作成）

（上記は含まれるメインモジュールの抜粋です。repository 全体ではさらに細かな実装ファイルがあります。）

---

## 永続ファイル / フラグについて

- data/monitoring.db（または SQLITE_PATH） — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db（PAPER_TRADING_SQLITE_PATH） — ペーパートレード専用 DB
- data/kabusys.duckdb（または DUCKDB_PATH） — 分析用 DuckDB
- data/execution.pid — ExecutionEngine 起動時に書き込まれる PID
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine の停止トリガ）
- data/stop_requested.flag — モニタリング / 実行プロセスの停止リクエストチェック用
- logs/<app_name>.log — 日次ローテーションで残るログファイル

注意:
- kill.flag を自動で消す挙動は KILL_FLAG_CLEAR_ON_START により制御（本番では 0 推奨）
- monitoring は環境にかかわらず本番 sqlite_path を使用する（意図的設計）

---

## トラブルシューティング

- 必須環境変数未設定
  - validate_config を実行して警告/エラーを確認してください
- PyYAML が無い場合
  - validate_config は YAML パース検証をスキップして警告を出します（必要な場合は PyYAML をインストール）
- OpenAI 関連
  - OPENAI_API_KEY が未設定だと AI 機能は例外を投げます。API キーは環境変数か関数引数で与えてください
- ログディレクトリ作成失敗
  - logging_setup は作成に失敗した場合ファイルハンドラをスキップしてコンソールのみで継続します。ファイル権限を確認してください
- psutil による優先度設定で権限不足
  - set_process_priority は権限不足時に警告ログを出して処理を継続します（必須ではありません）
- DuckDB / SQLite のバージョン差異
  - 一部の executemany 空リストに関する制約等に注意（コード内で互換性対策を行っています）

---

## 開発者向けメモ

- コードは可能な限り副作用を少なく設計されています（多くは純粋関数、DB 書き込みは明示的）
- AI 呼び出しや外部通信はリトライ・フォールバックを実装（フェイルセーフ設計）
- データ参照はルックアヘッドバイアス防止に配慮（target_date 未満など）
- Unit test 用に外部呼び出しポイントは差し替えやすく書かれています（例: _call_openai_api の patch）

---

## 参考コマンドまとめ

- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- AI スコア（プログラム呼び出し例）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026, 4, 1), api_key="...")

---

この README はコードベースの主要機能と運用手順を簡潔にまとめたものです。具体的な設計や API の詳細は各モジュールの docstring を参照してください。必要であれば、サンプル .env.example や起動スクリプトのデプロイ手順（systemd / supervisor 用の Unit ファイルなど）も追加で作成できます。