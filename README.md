# KabuSys

日本株自動売買システムの Python パッケージ（ドキュメント用 README）

※ 本 README はリポジトリ内のソースコードから要点を抜粋・整理したものです。

---

## プロジェクト概要

KabuSys は国内株式向けの自動売買フレームワークです。  
主な機能は以下の通りです。

- 取引実行エンジン（ExecutionEngine） — ブローカークライアントを通じて発注/約定管理
- 監視（Monitoring） — システム・注文・リスク監視、アラートと Kill Switch
- ポートフォリオ構築（選定・重み付け・ポジション決定）
- リサーチ機能（ファクター計算、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム検出）
- ペーパートレード専用の分離データベース（本番 DB と分離）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポートなど）

設計方針として、データ永続化は DuckDB（分析用） と SQLite（監視・発注ログ）で行い、LLM 呼び出しなどはフェイルセーフに配慮した実装になっています。

---

## 機能一覧（ハイライト）

- Execution
  - 本番 / ペーパートレード切替（環境変数 `KABUSYS_ENV`）
  - RiskManager によるポジション・ドローダウン制御
  - OrderRepository / OrderManager による注文状態管理
  - ExecutionEngine のセッション実行（PID 管理・停止フラグ対応）

- Monitoring
  - SystemMonitor：CPU/MEM/DISK・プロセス生存・データ鮮度監視
  - TradeMonitor：滞留注文、約定異常などの監視（ソースに詳細あり）
  - RiskMonitor：ドローダウン・ポジション上限チェックとリスクログ
  - KillSwitch：条件に基づき `data/kill.flag` へ停止指示を書き込み
  - MonitoringEngine：各モニタの定期実行・通知連携

- Portfolio（純粋関数群）
  - 銘柄選定、等重/スコア加重の重み計算
  - セクター制約・レジーム乗数の適用
  - 単元株丸めを含む株数決定ロジック（利用可能現金・上限等に対応）

- Research
  - momentum / volatility / value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ツール

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント算出（ai_scores テーブルへ書込）
  - regime_detector: ETF + マクロニュースの合成で市場レジーム判定を行い DB に格納

- Utilities
  - logging_setup：統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority：プロセス優先度 / CPU affinity ユーティリティ
  - config_setup：対話式 .env 生成ウィザード
  - validate_config：起動前の設定検証 CLI
  - tools.paper_verification_report：ペーパートレード検証レポート生成

---

## 必要要件（依存パッケージの例）

プロジェクトの主要な依存例（pyproject / requirements を参照してください）:

- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他：標準ライブラリ

インストール例（仮）:
- pip install -r requirements.txt

---

## 環境変数（主要）

.env や環境で設定する主要なキー（`config_setup.py` に項目定義あり）:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — `development` | `paper_trading` | `live`（デフォルト: development）

- DB / パス
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時）

- ログ / 動作
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH — Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring が参照）

- AI（OpenAI）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）

- Paper Trading 挙動
  - PAPER_FILL_MODE — MockBroker の fill モード（instant/partial/never/reject）

詳細は `src/kabusys/config.py` と `src/kabusys/config_setup.py` を参照してください。

---

## セットアップ手順（基本）

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb / psutil / openai 等を個別インストール）

3. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って入力し `.env` を生成します。

4. 設定検証（必須環境変数などをチェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

6. DuckDB / SQLite の初期化は各起動スクリプトが必要に応じて行います（monitoring は init_monitoring_db を呼ぶ）。

---

## 使い方（起動・主要コマンド）

- ExecutionEngine を起動（本番またはペーパートレードは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使われ、ペーパートレード用 DB（`PAPER_TRADING_SQLITE_PATH`）に書き込まれます。
    - 起動中、`data/stop_requested.flag` が存在するとエンジンは停止します。
    - 実行時に PID ファイル（デフォルト: data/execution.pid）を作成します。

- Monitoring を起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - Monitoring は常に本番の sqlite_path（`SQLITE_PATH`）を使用します。
  - 停止フラグ: 上述の `data/stop_requested.flag` を検出するとループを終了します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （`PAPER_TRADING_SQLITE_PATH` が指定されていれば省略可能）

- AI 関連（プログラム API）
  - news_nlp.score_news(conn, target_date, api_key=None)  — OPENAI_API_KEY が必要
  - ai/regime_detector.score_regime(conn, target_date, api_key=None)  — OPENAI_API_KEY が必要

---

## 停止・Kill Switch の運用

- Execution 停止のためのフラグ:
  - `data/kill.flag`：KillSwitch が書き込むファイル。ExecutionEngine 側でチェックして停止に使えます。
  - `data/stop_requested.flag`：run_execution / run_monitoring スクリプトがループを終了するために参照するフラグファイル（運用者が作成するとプロセスが終了します）。
- kill.flag は `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では 0 推奨）。

---

## ログ

- ログは標準出力（コンソール）とファイル出力の両方に出力されます。
- デフォルトのログディレクトリ: `logs/`
- アプリ名ごとにファイル出力されます（例: `logs/execution.log`, `logs/monitoring.log`）。
- LOG_LEVEL / LOG_DIR 等は環境変数で制御可能。

ログ初期化は `kabusys.utils.logging_setup.setup_logging(app_name=...)` を各起動スクリプトで呼び出しています。

---

## ディレクトリ構成

（ソース配下の主要ファイルと役割を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定取得
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト

  - execution/                   — 発注系（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py           — SQLite の監視 DB 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py           — （アラート送信実装がある）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                — ニュースを LLM に送って ai_scores 作成
    - regime_detector.py         — 市場レジーム判定
  - data/                         — （データ/DB ファイル置き場。リポジトリには含まれない）
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - ... その他ユーティリティ

---

## 注意事項 / 運用上のポイント

- 本番実行時は `KABUSYS_ENV=live` を必ず確認してください。validate_config は本番に関するガード（LINE 設定など）もチェックします。
- ペーパートレードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を参照）。
- OpenAI を利用する機能は API キーが必須です。失敗時は保守的にフォールバックする実装ですが、API コスト・レイテンシに注意してください。
- ログのローテーションは日次（30日保持）に設定されていますが、運用にあわせて LOG_DIR を適切に設定してください。
- process_priority.set_process_priority() により起動時にプロセス優先度が設定されます。権限不足の場合は警告ログが出ますが処理は継続します。
- DB スキーマのマイグレーションは `monitoring_db.init_monitoring_db` で最低限の互換性を維持する処理があります。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの要約です。実装の詳細・追加オプションや各モジュールの挙動については、各ソースファイルの docstring / コメントを参照してください。必要であれば、README に含める実行例や環境別の運用手順（systemd / cron / コンテナ化など）を追記できます。