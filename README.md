# KabuSys

日本株向けの自動売買 / リサーチ基盤の一部を実装した Python パッケージ。  
このリポジトリ内には、実行エンジン、監視 (monitoring)、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を含む小規模な自動売買フレームワークです。

- データ格納・分析用に DuckDB（prices_daily / raw_financials 等）を利用
- 発注ロジックを担う ExecutionEngine（本番 / ペーパートレード切替）
- システム状態・注文状態・リスクを監視する Monitoring
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- ファクター計算・特徴量探索などのリサーチ機能
- OpenAI を用いたニュースセンチメント評価 / レジーム判定（AI モジュール）
- 各種ユーティリティ（ログ設定・プロセス優先度設定等）

設計方針の一部:
- 本番 DB とペーパートレード DB は分離
- ルックアヘッドバイアス防止（date.today() を直接参照しない等）
- フェイルセーフを重視（API失敗時にデフォールト値で継続等）
- テスト可能性を考慮した分離（DB 書き込み箇所の明確化等）

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading モードが利用可能（MockBrokerClient）
  - 設定に応じて paper_trading 用 DB (data/paper_trading.db) を使用
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- 監視プロセス起動スクリプト（run_monitoring.py）
  - システム状態・データ鮮度・注文 / リスクの定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視用 SQLite DB（data/monitoring.db）へログ永続化

- MonitoringDB（monitoring/monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル管理
  - リスクログ重複除去（dedup）や dashboard の upsert 等のユーティリティ

- リスク監視（monitoring/risk_monitor.py）
  - ドローダウン・ポジション数監視、アラートログ記録

- Kill Switch（monitoring/kill_switch.py）
  - 条件により data/kill.flag を書き込み、ExecutionEngine 停止を促す

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重・スコア重み、リスク考慮の株数決定、セクターキャップ、レジーム乗数

- リサーチ（research パッケージ）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン・IC 計算・特徴量統計

- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア化（ai_scores に格納）
  - regime_detector: ETF 等とマクロニュースを合成して市場レジーム判定、market_regime に格納

- ツールスクリプト
  - 設定ウィザード: python -m kabusys.config_setup（.env の対話式生成・更新）
  - 設定検証: python -m kabusys.validate_config（.env / config/*.yaml の事前チェック）
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report

- 共通ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 設定読み込み（config.py）: .env 自動ロード機能、Settings クラス

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーション等を利用）
- Git リポジトリのルートで操作

1. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最小例（必要に応じて追加）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     pip install duckdb psutil openai PyYAML

   注意: requirements.txt は本リポジトリに含まれていない場合があるため、プロジェクトの実行に必要なパッケージを上記に追加してください。

3. .env の初期生成（対話式）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照してください）

4. 設定確認
   - python -m kabusys.validate_config
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

5. データディレクトリ作成（必要に応じて）
   - data/ ディレクトリに DB・フラグファイルが置かれます。スクリプト実行時に自動作成される箇所もありますが手動で用意しておくと権限問題を避けやすいです。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、Execution は専用 DB に記録（PAPER_TRADING_SQLITE_PATH）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI 呼び出し用 API キー（AI モジュールで使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で消すか（0/1、デフォルト 0）

---

## 使い方（主なコマンド）

- .env を対話式で作る / 更新
  - python -m kabusys.config_setup

- 設定検証（起動前に推奨）
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に stop_requested.flag が作成されるとエンジン停止処理を行う
    - PID ファイル (data/execution.pid) を作成

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に（環境に関わらず） Settings.sqlite_path（data/monitoring.db）を使用してログを保存
  - 停止は data/stop_requested.flag により検知

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI スコア / レジーム判定（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ これらは DuckDB 接続と OPENAI_API_KEY を必要とします

ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（utils/logging_setup.py）。

---

## 停止・制御ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring が存在をチェックし、あれば停止処理を行うためのフラグ（起動前の早期終了や外部停止トリガーに利用）

- data/kill.flag
  - Monitoring の KillSwitch により書き込まれ、ExecutionEngine に対する停止シグナルとして扱われる（存在すると Execution 側で検出可能）
  - Settings.kill_flag_clear_on_start=1 の場合、起動時に自動でクリアされる挙動に注意（本番では 0 推奨）

- data/execution.pid
  - Execution エンジンの PID を格納（Process 管理や stale PID 検出に利用）

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数読み込み / Settings クラス
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading レポート生成スクリプト
    - utils/
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / affinity ユーティリティ
    - monitoring/
      - monitoring_db.py             — SQLite 監視 DB 層（テーブル定義・Migration 含む）
      - monitoring_engine.py         — 各 Monitor を束ねるエンジン
      - system_monitor.py            — システム状態 / データ鮮度監視
      - trade_monitor.py             — （注文監視ロジック: 省略ファイル） 
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — Kill Switch（kill.flag 書込）
      - alert_manager.py             — （アラート通知: 省略ファイル）
    - execution/
      - execution_engine.py          — ExecutionEngine（本体: 省略ファイル）
      - order_manager.py             — 注文管理
      - order_repository.py          — 注文履歴 DB 操作
      - broker_factory.py            — BrokerClient の生成（Mock / Live 切替）
      - reconciler.py                — 発注結果の整合取り
      - risk_manager.py              — 実行時リスク管理（Rate limit / CB 等）
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み算出
      - position_sizing.py           — 株数決定ロジック
      - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py           — ファクター計算（momentum/value/volatility）
      - feature_exploration.py       — 将来リターン・IC・統計
    - ai/
      - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し）
      - regime_detector.py           — 市場レジーム判定（OpenAI + ETF）
    - data/                            — デフォルト DB / フラグ置場（リポジトリルートに data/）

---

## 運用上の注意・ヒント

- Monitoring は監視用 DB（SQLITE_PATH）に常に書き込みます。環境に依らない点に注意してください（run_monitoring の実装）。
- Execution は KABUSYS_ENV=paper_trading のときに paper_trading 用 DB を利用し、本番 DB とは切り離されます。
- OpenAI API を使う機能は OPENAI_API_KEY が必須（関数は引数で API キーを渡すことも可能）。
- ログディレクトリ作成に失敗した場合、ファイルログは無効化されコンソール出力のみになります（utils/logging_setup の安全設計）。
- process priority / CPU affinity の設定はプラットフォーム依存のため権限不足や未対応 OS の場合は警告ログでスキップされます。
- .env は決してバージョン管理に含めないでください（config_setup で生成される .env にも注意書きを含めています）。

---

## 開発・拡張のガイドライン（短く）

- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーションロジックを追加する（現状も簡単な ALTER を含む）。
- OpenAI 呼び出し部分はテスト容易性を考慮して _call_openai_api を patch して差し替え可能にしています（ユニットテスト作成時に活用）。
- 重たい計算・外部 API 呼び出しはモジュール単位で分離されているため、差し替えやロギング追加が容易です。

---

必要であれば、この README をベースに「インストール要件ファイル (requirements.txt)」や「デプロイ手順」「systemd / Supervisor 用のユニットファイル例」を追加で作成します。どの情報を優先して追加しますか？