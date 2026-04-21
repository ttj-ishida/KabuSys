# KabuSys

日本株自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）→ 監視（Monitoring）までを含む自動売買システムの主要コンポーネント群を提供します。研究・解析用のモジュール（DuckDB ベースのファクター計算や特徴量解析）や、OpenAI を用いたニュース NLP / レジーム判定、ペーパートレード用の検証ツールも含まれます。

以下はプロジェクト概要、機能一覧、ローカルセットアップ手順、使い方、ディレクトリ構成のまとめです。

---

## プロジェクト概要

- 自動売買のコア機能（ExecutionEngine、OrderManager、RiskManager、Reconciler 等）を含む。
- 監視機能（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager）により稼働状況・リスクを継続的にチェックし、必要に応じて ExecutionEngine を停止する仕組みを備える。
- DuckDB を用いた研究/ファクター計算モジュール（momentum/volatility/value 等）。
- OpenAI を利用したニュースセンチメントスコアリング（news_nlp）と市場レジーム判定（regime_detector）。
- ペーパートレード用 DB と本番 DB の分離、ペーパートレード向けの検証レポート生成ツール。
- .env を用いた設定管理（自動読み込み、対話式ウィザード、検証 CLI）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV に応じて本番／ペーパー切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 設定管理
  - config.py — 環境変数・設定の取得ラッパー（Settings クラス）
  - config_setup.py — .env の対話式ウィザード生成
  - validate_config.py — .env と config/*.yaml の検証 CLI
- 監視
  - monitoring/monitoring_db.py — SQLite への監視ログ永続化
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py
  - monitoring/kill_switch.py — kill.flag による強制停止シグナル
- 発注・実行
  - execution/*.py — Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager、OrderRepository、Reconciler
- ポートフォリオ構築
  - portfolio/portfolio_builder.py — 候補選定・重み計算
  - portfolio/position_sizing.py — 株数決定・リスク配分
  - portfolio/risk_adjustment.py — セクター上限、レジーム乗数
- 研究（Research）
  - research/factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research/feature_exploration.py — 将来リターン、IC、統計サマリー
- AI（OpenAI）
  - ai/news_nlp.py — ニュース記事を LLM でセンチメント評価し ai_scores に格納
  - ai/regime_detector.py — マクロ記事 + ETF MA を合成して市場レジームを判定
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（stdout + 日次ローテート）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - 推奨: Python 3.10+

2. 依存パッケージをインストール
   - 代表的な依存: duckdb, psutil, openai, PyYAML（config 検証で必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - このウィザードは .env（デフォルト: プロジェクトルート）を生成します。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, etc.

4. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ（data）やログディレクトリ（logs）は自動作成を試みますが、必要に応じて手動で作成しておくと良いです。

補足:
- config.py はプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト・コマンド）

- ExecutionEngine の起動
  - デフォルト（KABUSYS_ENV に従う。本番は production DB を使用、paper_trading は専用ペーパーデータベースを使用）
  - 実行:
    - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時は data/execution.pid ファイルが利用され、停止フラグ（data/stop_requested.flag）を検出すると安全停止します。
  - ExecutionEngine を強制停止したい場合は data/kill.flag を作成（KillSwitch 経由で評価されます）。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は Settings.sqlite_path（監視 DB）を使用します（monitoring は常に本番 sqlite_path を参照します）。
  - 停止フラグファイル data/stop_requested.flag を検出するとループを終了します。

- .env の更新・確認
  - python -m kabusys.config_setup で対話的に編集/上書き
  - python -m kabusys.validate_config で検証

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を優先）

- AI / 研究モジュールの利用（ライブラリとして）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
    - いずれも DuckDB 接続と target_date を渡して使用

---

## 重要な挙動メモ

- 環境区分
  - KABUSYS_ENV は development / paper_trading / live のいずれかで、Settings クラス経由で参照します。値が不正だと例外を投げます。
  - paper_trading は MockBrokerClient を使い、発注ログは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と完全に分離されます。
- 監視と停止
  - KillSwitch は RiskMonitor 等の結果に応じて data/kill.flag を作成します。ExecutionEngine は kill.flag を検出して停止します（設定により起動時に kill.flag をクリアするオプションあり）。
  - 停止用のストップフラグ: data/stop_requested.flag（run_execution / run_monitoring が検出して終了）。
- ログ
  - ログは stdout に加え logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリは環境変数 LOG_DIR またはデフォルト "logs"）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブルと一部カラム（例: latency_ms, peak_value）の追加を行います。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
- LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- PAPER_FILL_MODE (instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (1 または 0。live では 0 推奨)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env 読み込みを無効化)

---

## ディレクトリ構成（主なファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (※実装ファイルが存在する想定)
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py (※prices / raw_financials 取得等、想定される実装)
    - monitoring/ (上記)
    - tools/ (上記)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （config/*.yaml は validate_config で存在・パースをチェック）

---

## 開発上の注意点 / FAQ

- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 は危険です。Kill Switch を不用意にクリアしないでください。
- monitoring は監視用 DB（Settings.sqlite_path）を用い、本番/開発に関係なく同じ sqlite_path を参照する点に注意してください（run_monitoring の設計による）。
- ExecutionEngine の PID 管理 / stop フラグ / kill.flag の取り扱いは慎重にテストしてください。誤ったフラグ操作は本番の自動停止を招きます。
- OpenAI を利用する機能（news_nlp / regime_detector）は API 呼び出しでコスト・レイテンシ・失敗に対処する実装（リトライ、フォールバック）を含んでいますが、API キーやレート制限設定は運用側で管理してください。

---

README は以上です。必要であれば以下の追加を作成できます：
- 具体的な .env.example のテンプレート
- systemd / supervisor 用のサービス定義サンプル
- テスト手順（ユニットテスト / モックの作り方）