# KabuSys

日本株自動売買フレームワーク（軽量なプロトタイプ実装）

バージョン: 0.1.0

---

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアコンポーネントを含みます。
設計上のポイントは「本番とペーパートレードを分離」「監視と Kill Switch による安全停止」「DuckDB を用いた研究/分析」「LLM を用いたニュースセンチメント評価（オプション）」です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動/停止/ツール）
- ディレクトリ構成（主要ファイルと説明）
- 環境変数一覧（重要）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は次の目的をもつモジュール群で構成されています。

- ExecutionEngine: 注文作成・ブローカ連携・リスク管理を行う実行系
  - 本番（live）とペーパートレード（paper_trading）を環境で切り替え可能
  - ペーパートレード時は MockBrokerClient を用い、専用 SQLite(DB) に記録
- Monitoring: システム健全性・注文ログ・リスク（ドローダウン・ポジション数）を監視
  - 異常時に Kill Switch を発動し ExecutionEngine を安全停止可能
- Research / Portfolio: DuckDB を用いたファクター計算、ポートフォリオ構築、ポジションサイズ計算
- AI モジュール（任意）: OpenAI を用いたニュースのセンチメントスコアリング、市場レジーム判定
- ツール: 設定ウィザード、設定検証、ペーパートレード検証レポート生成 等

---

## 主な機能一覧

- 環境別分離:
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切り替え
  - ペーパートレード時は専用 SQLite（デフォルト `data/paper_trading.db`）を使用
- 監視:
  - CPU/メモリ/ディスクの定期チェック
  - Execution プロセスが停止している場合の検知
  - 注文の滞留・成行/約定の異常検出
  - ドローダウン・ポジション上限の検出とログ化
  - Kill Switch によるフラグファイル出力（data/kill.flag）
- ロギング:
  - 統一的ロギング設定（コンソール + 日次ローテートファイル）
- 研究用:
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility 等）
  - 特徴量探索・IC計算等
- AI連携（任意）:
  - OpenAI (gpt-4o-mini など) を使ったニュースセンチメント計算・市場レジーム推定
  - バッチ化、リトライ、レスポンス検証を含む堅牢な実装
- CLI ツール:
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート（tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing の Union | 記法など）
- システムに duckdb, psutil, openai 等のパッケージが必要（使用する機能に依存）

1. リポジトリをクローンし、作業ディレクトリを src 配下に設定（パッケージ参照のため）
   - 例: git clone ...; cd repo_root

2. 必要パッケージをインストール
   - 最低限:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の内容検証を行いたい場合）
   - 例:
     pip install duckdb psutil openai pyyaml

   （requirements.txt がない場合は上記を個別にインストールしてください）

3. .env の作成（対話式ウィザード推奨）
   - 実行:
     python -m kabusys.config_setup
   - これによりプロジェクトルートに `.env` を生成できます（Git へは絶対にコミットしないでください）。

4. 設定の検証
   - 実行:
     python -m kabusys.validate_config
   - 問題があればエラー/警告が出ます。--strict を付けると警告も失敗と見なします。

5. データディレクトリの確認
   - デフォルトの DB / ログディレクトリは `data/` と `logs/` です。必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `LOG_DIR` を変更してください。

---

## 使い方

以下は代表的な起動・操作コマンド例です。いずれもプロジェクトのルート（pyproject.toml/.git があるディレクトリ）から実行してください。

- 設定ウィザード（.env 生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（本番 or ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特徴:
    - 起動時に process priority を "high" に設定しようとします（OS/権限により失敗する場合は警告）
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
    - `data/stop_requested.flag` が存在すると起動を中止または実行中に停止します
    - PID ファイルはデフォルトで `data/execution.pid` に書き込まれます

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 特徴:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60）
    - 監視は monitoring 用の DB 初期化を行い、SystemMonitor を定期実行します
    - 停止は `data/stop_requested.flag` を置くことで行えます

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で PAPER_TRADING_SQLITE_PATH を明示できます（優先度: --db > 環境変数 > デフォルト）

- Kill Switch（監視側が発動）
  - リスク条件に該当すると `data/kill.flag` が書き込まれ、ExecutionEngine 側で検知・停止できます

プログラムを停止したい場合:
- 直接プロセスに SIGINT（Ctrl+C）を送る
- または `data/stop_requested.flag` を作成すると run_* スクリプトのループが安全に終了します

---

## 主要な環境変数（重要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 動作環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）

- ロギング / 運用
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。production では "0" 推奨）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

- ペーパートレード
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（ペーパーブローカの約定挙動）

- AI（OpenAI）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合必須）

---

## ディレクトリ構成（主要ファイルと簡単な説明）

（リポジトリの src/kabusys 相当）

- __init__.py
  - パッケージ宣言。バージョン情報など。

- config.py
  - 環境変数の自動読み込み（.env / .env.local 対応）と Settings クラスを提供

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、スレッド起動、停止フラグ監視）

- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）

- monitoring/
  - monitoring_db.py: SQLite を使った監視データの永続化層（テーブル初期化、読み書き API）
  - system_monitor.py: CPU / メモリ / データ鮮度 / 実行プロセス監視
  - trade_monitor.py: 注文ログの監視（滞留注文・約定異常など）
  - risk_monitor.py: ドローダウン / ポジション上限チェック
  - kill_switch.py: kill.flag の作成/評価
  - alert_manager.py: （アラート送信実装。LINE 等に通知する想定）
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ

- execution/
  - execution_engine.py: エンジン本体（注文フロー・セッション管理）
  - broker_factory.py: ブローカークライアントを生成（実ブローカ or Mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py: 発注管理・リスク管理等

- portfolio/
  - portfolio_builder.py: 候補抽出・スコア順ソート
  - position_sizing.py: 株数決定ロジック（リスクベース、等配分等）
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility 等のファクター算出（DuckDB）
  - feature_exploration.py: forward returns, IC, 統計サマリ

- ai/
  - news_nlp.py: ニュースを LLM に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py: ETF + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード DB を集計して PASS/FAIL を判定するレポート

- utils/
  - logging_setup.py: ログ設定ユーティリティ（コンソール + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度・CPU affinity 設定
  - その他ユーティリティ群

---

## 例: .env の最小サンプル

（対話式ウィザードを推奨しますが、手動で作る場合の例）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

注意: 上記はサンプルです。JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須で本物の値に置き換えてください。

---

## 運用上の注意点 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（自動クリア無効）にすることを推奨します。誤って Kill Switch を無効化するリスクを防ぎます。
- ログディレクトリ（logs/）とデータディレクトリ（data/）は適切な権限で管理してください。
- OpenAI を利用する機能は API コストが発生します。利用する場合は API キーとコスト管理に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL でポーリングしますが、短すぎる間隔はリソース消費やログ/DB ライトの増加を招きます。通常は 60 秒程度がデフォルトです。
- ペーパートレード用 DB は本番 DB と完全分離されています（デフォルト: data/paper_trading.db）。運用テスト時は必ずペーパー環境で動作確認してください。
- kill.flag / stop_requested.flag / execution.pid といったフラグファイルでプロセスの起動停止や検知を行います。これらファイルの扱いを運用手順として明文化してください。

---

問題や追加のドキュメント化が必要な箇所があれば、どの部分を深掘りしたいか教えてください（例: ExecutionEngine の起動パラメータ詳細、AI モジュールの運用、DB スキーマの詳解など）。