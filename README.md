# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注・実行、監視、研究・分析、AI（ニュースセンチメント）の各コンポーネントを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール化された自動売買フレームワークです。

- 市場データ（DuckDB）に基づくファクター計算・特徴量生成（research）
- ポートフォリオ構築（候補選定、配分、サイズ計算、リスク調整）
- ExecutionEngine による発注制御（本番 / ペーパートレードの分離）
- 監視サブシステム（プロセス稼働・データ鮮度・注文監視・Kill Switch）
- AI を使ったニュースセンチメント評価 / 市場レジーム判定
- 各種ツール（ペーパートレードの検証レポート等）

設計方針としては「ロジックの分離」「フェイルセーフ」「ルックアヘッドバイアス回避」を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（実注文 / ペーパートレードの切替）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、データは data/paper_trading.db に分離
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor を定期ポーリング、監視ログは SQLite（monitoring.db）に永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- Monitoring サブシステム
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - MonitoringDB: SQLite ベースの永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch: 条件により data/kill.flag を書き、ExecutionEngine に停止命令を送る
  - MonitoringEngine: 各モニタを束ね、アラート送信や Kill Switch 評価を実行
- ポートフォリオ構築
  - 候補選定（score 降順・signal_rank によるタイブレーク）
  - 重み計算（等配分 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（risk_based / equal / score、単元丸め、集計キャップ）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- AI（openai）
  - news_nlp: raw_news を集約して LLM（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定
  - API 呼び出しはリトライやフェイルセーフロジックを備える
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定のレポートを生成

---

## セットアップ手順（開発環境）

1. リポジトリをクローンして、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストールします（最低限の例）。
   - pip install duckdb psutil openai pyyaml
   - 実際にはプロジェクトの requirements.txt があればそれを使用してください。

3. データディレクトリを作成します（必要に応じて）。
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）。

5. 設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. DuckDB / SQLite の初期化は通常スクリプト実行時に行われます（monitoring と実行エンジンが必要なテーブルを作成します）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時に必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL（DEBUG|INFO|...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意：本番での通知）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1 = 有効、注意して使用）

自動 .env 読み込み
- プロジェクトルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - オプション: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジンの起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、DB は data/paper_trading.db に記録されます
  - 起動時に data/stop_requested.flag が存在すると起動を行いません

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection、target_date: datetime.date
    - api_key が None の場合は OPENAI_API_KEY 環境変数を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

注意点
- 本番（KABUSYS_ENV=live）では LINE のトークン等、通知設定を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は本番での自動クリアが危険なのでデフォルトは 0（無効）を推奨します。
- MONITORING は本番 sqlite_path を使用するように実装されています（監視ログは環境にかかわらず本番 DB に書き込まれます）。

---

## ディレクトリ構成（主なファイル）

（リポジトリの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - .env 読み込み、Settings クラス（環境変数アクセスのラッパ）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパー切替）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの LLM センチメント評価と ai_scores への書込み
    - regime_detector.py
      - 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル定義と MonitoringDB（読み書きユーティリティ）
    - system_monitor.py
      - SystemMonitor（プロセス・データ鮮度）
    - trade_monitor.py
      - TradeMonitor（滞留・約定異常）
    - risk_monitor.py
      - RiskMonitor（ドローダウン、ポジション上限、dashboard 更新）
    - kill_switch.py
      - KillSwitch（kill.flag の書き込み/削除）
    - monitoring_engine.py
      - MonitoringEngine（各 Monitor を束ねる）
    - alert_manager.py
      - アラート送信用の抽象管理（実装はファイル内に記述される想定）
  - execution/
    - execution_engine.py (参照)
    - order_manager.py (参照)
    - order_repository.py (参照)
    - broker_factory.py (参照)
    - reconciler.py, risk_manager.py, ...（発注ロジック関連）
  - portfolio/
    - portfolio_builder.py
      - 候補選定、等配分・スコア配分計算
    - position_sizing.py
      - 株数決定、リスク制限、単元丸め、集計キャップ
    - risk_adjustment.py
      - セクター制限、レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB を解析して PASS/FAIL 判定を出すレポートツール
  - utils/
    - process_priority.py
      - プラットフォーム差分を吸収したプロセス優先度・CPU affinity 操作
    - その他ユーティリティ

その他
- data/
  - デフォルトの SQLite / DuckDB ファイルはここに置かれる想定（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - フラグ / PID: data/kill.flag, data/stop_requested.flag, data/execution.pid など

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live を設定し、validate_config の注意メッセージを確認してください。
- Kill Switch（data/kill.flag）は ExecutionEngine を即時停止させるため重要です。KILL_FLAG_CLEAR_ON_START を不用意に有効化しないでください。
- OpenAI API を利用する機能は API キー・コスト・リクエスト失敗時の取り扱いを理解した上で運用してください。LLM 呼び出しはリトライ・フェイルセーフが組み込まれていますが、API 利用制限やコストは別途管理が必要です。
- SQLite / DuckDB ファイルのバックアップ・適切なディレクトリ権限を確保してください。

---

この README はコードベースの主要機能と使い方のサマリです。詳細は各モジュールの docstring やソースコメントを参照してください。必要であれば、特定モジュールの詳しい README（例: monitoring, execution, ai）を別途作成します。