# KabuSys

日本株向けの自動売買／研究フレームワーク（KabuSys）。  
このリポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI連携）などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのシステムです。

- 自動売買の実行エンジン（実口座／ペーパートレード対応）
- 実行中システムの監視（CPU/メモリ/ディスク、プロセス死活、データ鮮度など）
- リスク管理（ドローダウン監視、ポジション上限など）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、サイズ決定）
- 研究用ファクター計算・特徴量分析（DuckDB を使用）
- ニュースの NLP スコアリング（OpenAI を利用）
- 運用サポートツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

---

## 主な機能一覧

- Execution
  - 実口座 / ペーパートレードの切替（`KABUSYS_ENV`）
  - ブローカークライアントファクトリ、注文管理、リスク管理、照合作業
- Monitoring
  - SystemMonitor: CPU/Memory/Disk, 実行プロセス監視, データ鮮度検査
  - TradeMonitor, RiskMonitor, KillSwitch, Alert 管理（LINE などの通知はトークン設定で有効化）
  - データ永続化: SQLite（監視用） + DuckDB（分析用）
- Portfolio
  - 候補選定（スコア順）、等重／スコア重み、ポジションサイズ決定（lot 単位）
  - セクター上限の適用、レジームに応じた資金乗数
- Research
  - momentum/volatility/value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI
  - ニュース記事を LLM（OpenAI）でスコアリング（銘柄別センチメント）
  - 市場レジーム判定（MA とマクロセンチメントの合成）
- Tools
  - .env 対話ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - Paper Trading 検証レポート（`paper_verification_report.py`）

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用／データ:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 DB（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）

ロギング / 実行:
- LOG_LEVEL — ログレベル（例: INFO、DEBUG）
- LOG_DIR — ログディレクトリ（デフォルト: `logs/`）
- PID_FILE_PATH — ExecutionEngine 用 pid ファイル（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: `data/kill.flag`）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" or "0"、デフォルト: "0"）

モニタリング:
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト: 60）

AI（OpenAI）:
- OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector で使用）

ペーパートレードモードの設定:
- PAPER_FILL_MODE — MockBroker の約定挙動（`instant` / `partial` / `never` / `reject`、デフォルト: `instant`）

注意: 必須環境変数が未設定だと起動前に `validate_config.py` で検知できます。

---

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 追加で便利: pip install PyYAML

   ※requirements.txt がある場合はそれを使用してください（本コード例では同梱されていません）。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、必須トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳しく扱いたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトで `data/` に DB やフラグファイル（`monitoring.db`, `paper_trading.db`, `execution.pid`, `kill.flag` 等）を作成します。必要に応じてディレクトリ作成・権限設定を行ってください。

---

## 使い方（起動・停止・ツール）

基本的にモジュールをモジュール実行します。

- ExecutionEngine を起動（実運用／ペーパートレードいずれも）
  - KABUSYS_ENV を切り替えることで paper_trading モードになります。
    - 本番（live）: export KABUSYS_ENV=live
    - ペーパー: export KABUSYS_ENV=paper_trading
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - `data/stop_requested.flag` を作成すると起動中のエンジンは検知して停止します。
    - KillSwitch による強制停止は `data/kill.flag` を書き込まれた場合に発動します（KillSwitch のロジックに基づく）。

- Monitoring を起動（システム監視）
  - MONITOR_POLL_INTERVAL を秒で指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - run_monitoring も `data/stop_requested.flag` を検知して終了します。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用します（監視は本番 DB を想定）。

- .env を対話で作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）：
    - kabusys.ai.news_nlp.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)
  - これらはモジュール関数であり、DuckDB 接続（prices_daily / raw_news 等）を引数にとって実行します。

---

## 停止・フラグについて

- data/stop_requested.flag
  - run_execution/run_monitoring の両方が起動ループ内で確認する停止フラグ。
  - 手動でファイルを作成すると安全に停止シーケンスに入る。

- data/kill.flag
  - KillSwitch が条件（ドローダウン超過等）を満たした際に書き込むフラグ。ExecutionEngine の停止トリガーに使われます。
  - Settings で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアする設定もあります（本番では推奨されません）。

---

## ロギング

- setup_logging が全スクリプトで使用されます。デフォルトは stdout と日次ローテートファイル（logs/<app_name>.log）。
- 環境変数 LOG_DIR、LOG_LEVEL で動作を制御できます。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 配下の主要モジュールと役割の抜粋です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込み）
  - config_setup.py — .env 対話ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
    - monitoring_engine.py — Monitors を統合してポーリング
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書き込み・評価
    - ...（TradeMonitor, AlertManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定、等重／スコア重み
    - position_sizing.py — 株数計算、資金配分、lot 丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - logging_setup.py — ログ統一設定
    - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ

外部に config/（yaml テンプレート）や data/（DB、フラグ、pid）ディレクトリが存在する想定です。

---

## 備考 / 運用上の注意

- 本番運用時は必須トークン・パスワードを適切に管理し、.env を絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意（validate_config は追加の注意喚起を表示します）。
- Monitoring は監視用データベースとして sqlite_path を使用します。監視は常に本番 DB を参照する設計の箇所があるため、テスト時は環境変数でパスを分離してください（PAPER_TRADING_SQLITE_PATH など）。
- OpenAI 利用部分は API 呼び出し失敗時にフォールバック動作（無害化）する設計ですが、API キーのレート制限やコストに注意してください。

---

必要に応じて README を拡張します。例えば:
- 依存パッケージの固定バージョン（requirements.txt）
- 実行例（ログ出力例）
- 開発用テスト手順（ユニットテストの実行方法）
などを追加できます。どの情報を優先して追加しましょうか？