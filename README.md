# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注エンジン、監視/アラート、リサーチ（ファクター計算）および AI を用いたニュースセンチメント評価などの機能を含みます。

以下は本リポジトリの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な役割は以下：

- シグナルから銘柄選定・ウェイト計算・ポジション設計を行う（portfolio モジュール）
- 発注管理、ブローカー連携、起動時リコンシリエーション（execution モジュール）
- システム稼働・注文状況・リスク指標の監視とアラート（monitoring モジュール）
- DuckDB 上の価格/決算データを用いたファクター計算・リサーチ（research モジュール）
- OpenAI を用いたニュースセンチメント評価・市場レジーム判定（ai モジュール）
- 検証レポート生成などのユーティリティ（tools）

設計上のポイント：
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は本番 DB と分離して専用 SQLite を使用
- 監視は本番の monitoring DB を参照（MONITOR は環境に依存せず本番 sqlite_path を使う）
- 各種設定は環境変数（.env / .env.local）から読み込む（自動ロードあり。無効化可）

---

## 主な機能一覧

- portfolio
  - 候補銘柄選定（スコア降順）、等分配・スコア加重配分
  - リスク調整（セクターキャップ適用、レジーム乗数）
  - 株数決定（単元丸め、リスクベース / ウェイトベース配分、aggregate cap）

- execution
  - OrderManager / ExecutionEngine による発注ライフサイクル管理
  - ブローカー抽象化（本番/モック切替）
  - Reconciler による再起動時の状態同期・ポジション差分検出
  - リスク管理（RiskManager, Reconciler 等はコードベースに含まれる）

- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクイベントログ
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送出
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）

- research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- ai
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価、結果を ai_scores に書き込み
  - regime_detector: ETF 1321 の MA とマクロニュースセンチメントを組み合わせて日次で regime 判定し DB へ永続化

- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## 必要条件（主な依存ライブラリ）

最低限必要な Python ライブラリ（バージョンは開発環境に合わせて調整してください）：

- Python 3.8+
- duckdb
- psutil
- requests
- openai
- streamlit

（パッケージ管理は好みに応じて requirements.txt / Poetry 等を利用してください）

例（venv 作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主要なもの）

多くの設定は環境変数で行います。`.env`/`.env.local` の自動読み込み機能あり（プロジェクトルートが検出可能な場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（デフォルトを含む）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- SQLITE_PATH: 監視用 SQLite パス — デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — デフォルト: data/paper_trading.db
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス — デフォルト: data/execution.pid
- KILL_FLAG_PATH: KillSwitch による停止フラグパス — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — デフォルト: 60
- PAPER_FILL_MODE: Paper Trading の MockBroker の約定動作（instant/partial/never/reject） — デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp, ai.regime_detector が使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用（設定必須な場合あり）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO

設定不足時に Settings クラスは ValueError を投げる（必須項目は .env.example を参照してください）。

---

## セットアップ手順（開発者向け）

1. レポジトリをクローンして作業ディレクトリに移動
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成して環境変数を設定（例: OPENAI_API_KEY、KABU_API_PASSWORD など）
5. data ディレクトリ作成（実行スクリプトが自動で作成することもあります）
6. DuckDB / SQLite ファイルはスクリプト実行時に自動で初期化される（監視 DB のテーブル初期化は init_monitoring_db が行います）

例 (.env):
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=yourpassword
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## 使い方（実行例）

注意: 実行するスクリプトはパッケージとして `python -m kabusys.<module>` で呼ぶことを想定しています。

1. 監視プロセス（SystemMonitor のポーリング）を起動
```bash
python -m kabusys.run_monitoring
```
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 停止はプロジェクトルート下 `data/stop_requested.flag` を作成することでループを安全に終了できます。

2. Execution エンジン（発注エンジン）を起動
```bash
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。本番 DB と分離されます。
- 起動時に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。
- 実行中に `data/stop_requested.flag` を作成すると安全に停止します。
- 実行中、PID は `data/execution.pid` に書き込まれます（SystemMonitor はこの PID の存在を監視します）。

3. Streamlit ダッシュボード（監視 DB の可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視用 SQLite を読み取り専用で開き、ダッシュボードを表示します。

4. Paper Trading 検証レポートの生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB 指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 稼働率、注文成功率、レイテンシ等を集計して標準出力にレポートを出力します。

5. AI 関連のプログラム的呼び出し
- news_nlp.score_news(conn, target_date, api_key=None)
- regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも DuckDB 接続（duckdb.connect(...).cursor() のような接続）と target_date を渡して呼び出します。
  - API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定します。

---

## 停止・フェイルセーフ

- stop フラグ:
  - `data/stop_requested.flag` を作成すると、run_monitoring / run_execution のループが検知して安全に停止します（両スクリプトとも検査あり）。
- kill フラグ:
  - KillSwitch が条件を満たすと `data/kill.flag` に理由を書き込みます。ExecutionEngine はこのファイルを確認して停止を受けます。
  - KillSwitch が書く条件は RiskMonitor（ドローダウン、ポジション上限）などに基づきます。
- PID ファイル:
  - ExecutionEngine 起動時に `data/execution.pid` に PID を書き込みます。SystemMonitor は PID 存在を確認します。古い PID（既に存在しないプロセス）を検出した場合は stale PID として削除し、risk_event をログします。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数読み込み・Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスクと丸め処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py — 監視 DB テーブル定義および MonitoringDB クラス
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・価格異常監視
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — 停止フラグ生成ユーティリティ
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各モニタの統合ループ（テスト用 / 本番用）
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py — 発注 API 周りの外向きインターフェース
    - reconciler.py — 起動時リコンシリエーション
    - （その他：broker_factory, execution_engine, order_repository 等）
  - utils/
    - process_priority.py — プラットフォーム非依存の優先度設定 / CPU affinity
    - __init__.py
  - research と monitoring で DuckDB / SQLite を使う箇所が多く存在します

data/（実行時に使用される想定ファイル）
- data/monitoring.db — 監視用 SQLite（DEFAULT: SQLITE_PATH）
- data/paper_trading.db — Paper Trading 用 SQLite（DEFAULT: PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — DuckDB（DEFAULT: DUCKDB_PATH）
- data/execution.pid — ExecutionEngine の PID
- data/stop_requested.flag — 外部からプロセスを停止するためのフラグ
- data/kill.flag — KillSwitch が書き込む停止理由

---

## 開発上の注意点 / 実運用での留意点

- Paper Trading と live（本番）は DB を分離してください（`KABUSYS_ENV` の設定）。
- OpenAI API 呼び出しはネットワーク/レート制限エラーに対して冗長性（リトライ）を設けていますが、API キーや料金に注意してください。
- プロセス優先度や CPU affinity の設定は OS 権限依存です。権限が足りないと警告が出てスキップします。
- DuckDB / SQLite のファイルロック・並列アクセスに注意。ダッシュボードは読み取り専用で接続するよう設計されています（URI + mode=ro が利用可能）。
- 監視周りは稼働率・レイテンシの計測を行い、条件を満たすと kill.flag を書き込みます。運用時には通知先（LINE）やしきい値を適切に設定してください。

---

## お問い合わせ / 貢献

ソースコードの改善、バグ修正、ドキュメント追加等は Pull Request を受け付けます。大きな設計変更を行う場合は Issue を立てて議論してください。

---

README は以上です。必要であれば、セットアップのための requirements.txt や簡単なデプロイ手順（systemd ユニット例など）も追加できます。どの部分を優先して追加しますか？