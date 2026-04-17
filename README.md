# KabuSys — 自動売買システム（README）

このリポジトリは日本株向けの自動売買システム「KabuSys」の一部実装です。ポートフォリオ構築、注文管理、監視、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価などのコンポーネントを含みます。

以下は本コードベースに基づく README（日本語）です。

※本 README はソースコード内の docstring / コメントを元に作成しています。

---

## プロジェクト概要

KabuSys は以下の機能を備えた日本株自動売買基盤のコンポーネント群です。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ（momentum/value/volatility 等）
- ポートフォリオ構築（候補選定、重み付け、単元丸め、ポジションサイズ計算）
- 注文管理（OrderManager / ExecutionEngine / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 通知（LINE Push 経由の AlertManager）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- Paper Trading 用の分離 DB と検証レポート生成ツール

設計上の特徴：
- DuckDB（時系列株価等）と SQLite（監視・トレードログ）を併用
- Paper Trading 環境は本番 DB と完全分離
- 監視は監視専用 DB に必ず本番の sqlite_path を使用（環境に依存しない）
- LLM 呼び出しはフェイルセーフ設計（APIエラーはフォールバック）

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（select_candidates）
  - 等金額 / スコア重み配分（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）

- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算 / IC 計算 / 統計サマリ（calc_forward_returns, calc_ic, factor_summary）

- execution
  - OrderManager（注文作成・同期・状態遷移）
  - Reconciler（再起動時の注文・ポジション突合）
  - ExecutionEngine（別スレッドで注文セッションを実行する起動スクリプトあり）

- monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（ルールに応じて停止フラグを書込）
  - AlertManager（LINE Push 通知）
  - Streamlit ダッシュボード（監視情報の可視化）
  - monitoring.db 用の永続化層（MonitoringDB）

- ai
  - news_nlp: raw_news から銘柄別センチメントを OpenAI で評価して ai_scores に書込
  - regime_detector: ETF (1321) の MA200 とマクロニュースで日次レジーム判定し DB に書込

- tools
  - paper_verification_report: Paper Trading の検証レポート生成ツール（期間指定可）

---

## 前提 / 必要要件

- Python 3.10+
  - 型ヒント（`X | None` など）を使用しているため 3.10 以上を想定
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- データディレクトリ（デフォルト）: `data/`
  - monitoring DB: data/monitoring.db（Settings.sqlite_path）
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

インストール例:
```bash
python -m pip install "duckdb" "psutil" "requests" "openai" "streamlit"
```
（実際は requirements.txt を用意して pip install -r することを推奨）

---

## 環境変数（主なもの）

Settings クラスで読み込まれる主な環境変数：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）デフォルト: instant
- PID_FILE_PATH, KILL_FLAG_PATH: 各種ファイルパス設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化

.env / .env.local をプロジェクトルートに置くと自動読み込み（OS 環境変数優先）。自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## セットアップ手順（簡易）

1. Python 3.10+ を準備
2. 依存パッケージをインストール
   - 例: pip install duckdb psutil requests openai streamlit
3. data ディレクトリを作成
   - mkdir -p data
4. 環境変数を設定（推奨: プロジェクトルートの `.env` に記述）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - ai を使う場合: OPENAI_API_KEY
   - Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定
5. DuckDB / SQLite DB を準備（必要に応じて初期データをロード）
   - monitoring モジュールは必要なテーブルがない場合 init_monitoring_db() で自動作成します

---

## 使い方（起動／実行例）

- 監視プロセスの起動
  - デフォルトでは監視は production の sqlite_path を使用（環境にかかわらず）
  - ポーリング間隔を変更する場合: MONITOR_POLL_INTERVAL を設定（秒、1 以上）
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 停止方法:
    - プロセスを Ctrl+C で停止
    - またはプロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが検知して安全終了

- ExecutionEngine（注文実行）の起動
  - Paper Trading モード:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    この場合、Paper Trading 用 DB（data/paper_trading.db）と MockBrokerClient が使われ、本番 DB と完全分離されます。
  - 本番モード:
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 停止方法:
    - `data/stop_requested.flag` を作成すると起動中の Engine を安全に停止します。
    - KillSwitch により `data/kill.flag` が作成されると ExecutionEngine の停止シグナルとして使用されます（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定してクリアする運用も可能）。

- Streamlit ダッシュボード
  - 監視 DB を読み取り専用で開く Streamlit UI:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成
  - 期間指定や DB パス指定が可能:
    ```bash
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
    ```

- AI モジュールの利用
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。直接 import してスクリプトやスケジューラから呼び出してください。
  - 例（Python スクリプト内）:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn は duckdb.connect() の接続オブジェクト
    n = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 停止・フラグ運用

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルを監視して存在すると安全に終了します（手動停止用）。
- data/kill.flag
  - KillSwitch によって作成されるフラグ。ExecutionEngine に停止を促すためのファイルです。
  - KillSwitch は drawdown やポジション上限などの条件で書き込みます。
- data/execution.pid
  - ExecutionEngine の PID を格納するファイル。SystemMonitor はこのファイルを見てプロセスの存在を確認します。古い PID ファイル（stale）が検知されると削除してログに残します。

---

## ディレクトリ構成（抜粋・説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数／設定管理（.env 自動ロード・Settings）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ / 主要モジュール：
- ai/
  - news_nlp.py — ニュースの LLM センチメント集計・ai_scores 書込み
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — monitoring DB 初期化・永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル処理
  - alert_manager.py — LINE 通知送信
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 注文作成・状態管理
  - reconciler.py — 起動時の復旧・突合作業
  - （その他: broker_factory, execution_engine, order_repository, order_record など）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数決定・丸め・集約制限
- research/
  - factor_research.py — momentum/value/volatility 計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

（上記は本リポジトリに含まれる主なファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 運用上の注意点 / ヒント

- KABUSYS_ENV によって一部挙動が変わります（paper_trading は専用 DB、live は本番設定）。ただし Monitoring は環境にかかわらず本番 sqlite_path を使用する実装になっています（意図的）。
- AI（OpenAI）呼び出しはネットワーク/レート制限/5xx に対してリトライとフェイルセーフを組み込んでいますが、API キーや課金設定には注意してください。
- データ鮮度チェックは DuckDB の prices_daily の最終日付を参照するため、定期的に価格データを取り込むパイプラインが必要です（kabusys.data.pipeline に依存）。
- PID/フラグファイルの取り扱いは慎重に。stale PID は SystemMonitor によって検出され削除されることがあります。
- Paper Trading の挙動（PAPER_FILL_MODE）を適切に設定してテストしてください。

---

## 参考（実行コマンド一覧）

- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はソースコードコメントを基に作成しています。実運用する際は環境（API キー、証券会社 API、テスト DB、バックアップ、監視のアラート先など）に合わせて `.env` や起動コマンド・監視設定を適切に調整してください。必要があれば実運用向けのデプロイ手順や運用ガイドも作成できます。