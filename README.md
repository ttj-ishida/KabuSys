# KabuSys — README (日本語)

このドキュメントは、リポジトリ内の主要スクリプト・モジュール群の概要、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究プラットフォームです。  
主な設計方針は以下の通りです。

- 発注ロジック・リスク制御・監視・データ処理を分離して実装
- 本番環境とペーパートレード（模擬発注）を容易に切り替え可能
- DuckDB / SQLite を利用したローカル DB をデータソースとして利用
- ニュースの NLP（OpenAI）を用いたセンチメント評価や市場レジーム判定をサポート
- モジュールはテストしやすい純粋関数設計（研究・ポートフォリオ構築など）

バージョンはパッケージ内 `kabusys.__version__` で管理（現時点: 0.1.0）。

---

## 主な機能一覧

- Execution（発注実行）
  - ExecutionEngine を使った注文管理、リスク制御、リコンシリエーション
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB に分離記録

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期ポーリング監視
  - Kill Switch（条件を満たすと `data/kill.flag` を作成して Execution を停止）
  - 監視ログの永続化（SQLite）

- 研究・特徴量計算
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（スピアマン）や統計サマリー

- ポートフォリオ構築
  - 候補選定、等重/スコア重配分、リスクベースのポジションサイズ計算
  - セクター制限、レジーム乗数の適用

- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュースセンチメント（銘柄別）スコアリング
  - マクロニュースと MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- ツール
  - ペーパートレード検証レポート生成（期間指定可）

- ユーティリティ
  - 環境変数管理（.env ロード）、対話式 .env 作成ウィザード、設定検証 CLI
  - ログ設定、プロセス優先度制御、CPU affinity（psutil 利用）

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   このリポジトリに requirements ファイルがない場合は、少なくとも以下をインストールしてください。

   ```bash
   pip install duckdb psutil openai
   # YAML 検証を行いたい場合:
   pip install PyYAML
   ```

   - duckdb: 分析用 DB
   - psutil: プロセス優先度設定・システム情報取得
   - openai: ニュース NLP / レジーム判定（必要時）
   - PyYAML: config/*.yaml のパース検証（任意）

3. プロジェクトルートに移動して `.env` を作成

   対話式ウィザードで初期 `.env` を作る:

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザード完了後は以下コマンドで設定を検証できます。

   ```bash
   python -m kabusys.validate_config
   ```

   `--strict` を付けると警告も FAIL 扱いになります。

4. data ディレクトリやログディレクトリは必要に応じて自動作成されますが、権限等に注意してください。

---

## 環境変数（主要）

主に `.env` に記載する想定のキー（抜粋、デフォルトを含む）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、Execution は専用 DB (data/paper_trading.db) を使用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視 DB（monitoring は常に本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレード約定モード（default "instant"）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — default INFO
- LOG_DIR (default: logs)
- OPENAI_API_KEY — AI 機能で必要
- KILL_FLAG_CLEAR_ON_START — 本番注意（0 推奨）

その他、config/*.yaml を使う設定がある場合は README の該当サンプル/テンプレートを参照してください（`python scripts/generate_config.py` のような補助スクリプトがある場合があります）。

---

## 基本的な使い方 / 起動例

起動スクリプトはモジュールとして実行します。ログ設定は各スクリプト内で統一的に行われます。

- ExecutionEngine を起動（デフォルト動作は Settings に依存）

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録されます。
  - 実行時に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中は `data/execution.pid` へ PID を書きます（設定により場所変更可）。

- Monitoring（ポーリング監視）を起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可（デフォルト: 60 秒）。
  - 監視は monitoring 用の sqlite（Settings.sqlite_path）にログを残します（環境に関係なく本番 sqlite_path を使う仕様）。
  - 停止フラグファイル `data/stop_requested.flag` を検知してループを抜けます。

- 環境設定ウィザード / 検証

  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / 研究系はライブラリ API として利用可能（例: `kabusys.ai.score_news`、`kabusys.ai.regime_detector.score_regime`、`kabusys.research.calc_momentum` など）。これらは DuckDB 接続を受け取るため、スクリプト内や REPL で使えます。

---

## 運用上の重要点

- 監視（monitoring）は常に `Settings.sqlite_path`（デフォルト `data/monitoring.db`）を用います。ペーパートレード時でも監視 DB は本番パスを参照する仕様に注意してください。
- ペーパートレード（paper_trading）は注文実行側（ExecutionEngine）が MockBrokerClient を使い DB を分離します（`PAPER_TRADING_SQLITE_PATH`）。
- プロセス優先度設定（set_process_priority("high")）やログローテーション（logs/<app>.log）が標準で行われます。
- Kill Switch（`data/kill.flag`）が作成されると ExecutionEngine に停止シグナルを送り、`KILL_FLAG_CLEAR_ON_START` が 1 に設定されていると起動時に自動クリアされる可能性があるため、本番では 0 を推奨します。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必要とし、外部 API 呼び出しに伴うエラー処理・リトライロジックが実装されていますが、API キー未設定時は ValueError を送出する箇所があります。

---

## ディレクトリ構成（主要ファイル / モジュール）

以下はパッケージ内部（src/kabusys）の主要なファイル（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み、自動 .env ロード）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注/約定等の監視（コードベースに存在）
    - risk_monitor.py — ドローダウンやポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag の書き込み/評価
    - alert_manager.py — アラート送信（LINE 等。コードベースに存在）
  - execution/
    - execution_engine.py — ExecutionEngine（発注実行の中核）
    - broker_factory.py — Broker クライアントの生成（Mock / 実ブローカー）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースを使った銘柄別センチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/   (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト)
    - kill.flag / stop_requested.flag / execution.pid 等の制御ファイル
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成

（実際のリポジトリにはさらに細かなモジュールや補助スクリプトが含まれる場合があります）

---

## 開発・拡張のヒント

- DuckDB を通して prices_daily / raw_financials / raw_news 等のテーブルを参照する設計なので、データ投入やスキーマ整備が重要です。
- 研究系・ポートフォリオ系の関数は純粋関数として設計されている箇所が多く、ユニットテストを作成しやすくなっています。
- AI 関連は外部 API に依存するので、テスト時は API 呼び出し関数をモックする（例: unittest.mock.patch）ことを推奨します。
- ログ出力は centralize されており、`kabusys.utils.logging_setup.setup_logging` を使うことでアプリケーション毎にファイル/ローテーション設定が統一されます。

---

## よくある運用コマンドまとめ

- 環境構築（仮想環境・パッケージ）
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- モニタ起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、この README を元に具体的な例（.env.example、systemd サービス例、Dockerfile、CI 用テスト手順）も作成できます。どのドキュメントを優先してほしいか教えてください。