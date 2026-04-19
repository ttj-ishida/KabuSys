# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究プラットフォームです。  
本リポジトリは以下の主要機能を備え、実運用・ペーパートレード・研究ワークフローをサポートします。

- 注文実行エンジン（ExecutionEngine）
- システム監視（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数算出）
- リスク監視（ドローダウン・ポジション制限）
- 研究用ファクター計算・特徴量探索（DuckDB を用いた集計）
- ニュース -> LLM（OpenAI）によるセンチメントスコアリング & レジーム判定
- 各種ユーティリティ（設定ウィザード、設定検証、レポート出力 等）

以下、README.md に含める内容を日本語でまとめます。

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存関係
- セットアップ手順
- 使い方（起動・操作）
- 環境変数（主要）
- ファイル / ディレクトリ構成（抜粋）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。  
実売買（live）・ペーパートレード（paper_trading）・開発（development）モードを想定しており、データ永続化に DuckDB（分析用）と SQLite（監視・発注ログ）を併用します。  
ニュース解析やレジーム判定には OpenAI（gpt-4o-mini）を利用するため、必要に応じて API キーを設定します。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動して注文ロジックを実行
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 用 DB に分離
  - Execution の PID 管理、停止フラグ監視
- run_monitoring.py
  - SystemMonitor を定期ポーリングしシステム状態を記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用（環境に依存しない）
- monitoring モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / MonitoringDB
  - risk monitor によるドローダウン検出やポジション上限検出、Kill Switch 発動機能
- portfolio（portfolio_builder / position_sizing / risk_adjustment）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research（factor_research / feature_exploration）
  - DuckDB を用いたファクター算出（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー
- ai（news_nlp / regime_detector）
  - raw_news を LLM でスコアリングして ai_scores に保存
  - マクロニュース + ETF ma200 乖離を合成して市場レジーム判定（market_regime）
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- utils
  - logging_setup（統一ログ設定）、process_priority（プロセス優先度設定）、その他ユーティリティ
- 設定まわり
  - config.py（Settings クラス）：環境変数とデフォルトの管理
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：起動前に設定の妥当性チェック

---

## 必要条件 / 依存関係

推奨 Python バージョン: 3.10+（型ヒントに | 演算子を使用しているため）

主な Python パッケージ:
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- PyYAML（validate_config の YAML 検証を行う場合）
- （その他標準ライブラリを多数使用）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

※ 実行環境で必要な OS 標準パッケージ（データベースファイル配置や権限など）に注意してください。

---

## セットアップ手順

1. リポジトリを取得
   - git clone などでソースを配置

2. 仮想環境作成・依存関係インストール
   - 先述の通り pip で必要パッケージを導入

3. .env の初期作成（推奨）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - これによりプロジェクトルートに `.env` が作成されます（Git にコミットしないでください）。

4. 設定検証
   - 自動検証を実行して必須変数やファイルパス等を確認:
     ```
     python -m kabusys.validate_config
     ```
   - 必要に応じて `--strict` を付けると警告も失敗扱いになります。

5. データディレクトリの準備（必要に応じて）
   - デフォルトで `data/` に DB ファイルやフラグが置かれます。
   - `logs/` ディレクトリは logging_setup が自動作成しますが、権限に注意してください。

---

## 使い方

基本的にモジュールを Python の -m 形式で起動します。

- ExecutionEngine 起動（発注エンジン）
  - 本番 / ペーパートレードは KABUSYS_ENV に依存します
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止: `data/stop_requested.flag` を作成すると、起動中のループが検出して停止します。また `data/execution.pid` を PID 管理に使用します。
  - ペーパートレード:
    - 環境変数 `KABUSYS_ENV=paper_trading` を設定すると、MockBroker を使い DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。

- Monitoring 起動（監視プロセス）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可。デフォルト 60 秒。
  - 監視は常に Settings.sqlite_path（デフォルト `data/monitoring.db`）を使用します（環境にかかわらず本番 DB を参照）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前）
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db` で DB パスを指定できます。デフォルトは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

- AI / ニュース関連（プログラム API）
  - ai.score_news(conn, target_date, api_key=None) — OpenAI API キーが必要
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらはライブラリ関数として呼び出すことを想定しています。OpenAI API を利用するには `OPENAI_API_KEY` を環境変数に設定してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 停止・キルフラグ関連設定
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）

デフォルト値は `kabusys.config.Settings` クラス内に定義されています。`.env.example`（存在する場合）を参照して .env を作成してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリング
  - regime_detector.py — レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・CRUD）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 発注ログ監視（ファイル内に実装詳細あり）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag の生成 / 管理
  - alert_manager.py — （通知管理: LINE 等に送る実装想定）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- execution/ (発注ロジック群)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py

プロジェクトルート:
- data/ — DB やフラグファイル（例: data/monitoring.db, data/paper_trading.db, data/kill.flag）
- logs/ — ログファイル（設定によって自動作成）
- config/ — YAML ベースの設定ファイル（テンプレート / 生成スクリプトで使用）

（実際のファイル構成は上記からさらに派生します。詳細は該当ソースを参照してください）

---

## 運用上の注意点 / ヒント

- 監視（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で間隔を調整できます。0 以下など不正値はデフォルト（60 秒）にフォールバックします。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。一方、run_execution は KABUSYS_ENV=paper_trading のとき paper_trading 用 DB に分離します。運用時に誤って本番 DB を上書きしないよう注意してください。
- Kill Switch（data/kill.flag）が書き込まれると ExecutionEngine に停止シグナルが送られます。Kill Switch は RiskMonitor 等から発火します。
- OpenAI を用いた機能は API レート制限・ネットワーク障害を考慮したリトライ実装がありますが、API キーやコスト管理には十分注意してください。
- logging_setup はデフォルトで stdout と日次ローテートのファイルハンドラを設定します。ログ出力先は環境変数 LOG_DIR / 引数で変更可です。
- process_priority.set_process_priority を初期化時に呼び出してプロセス優先度を上げようとしますが、権限不足で失敗することがあります（警告が出るのみで続行されます）。
- config_setup で作成した .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。

---

## 問い合わせ / 貢献

README の改善、バグ修正、機能追加は歓迎します。プルリクエスト / Issue を通して提案してください。大きな設計変更を行う場合は事前に Issue で相談いただけるとスムーズです。

---

以上が本リポジトリの概要と基本的な使い方です。必要に応じて各モジュールのドキュメント（ソース内 docstring）を参照してください。