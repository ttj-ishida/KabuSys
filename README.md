# KabuSys

日本株向け自動売買システムの一部コンポーネント群。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視、研究（ファクター計算）、およびニュースNLP / レジーム判定のユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール式システムです。本コードベースは以下の主要機能を含みます。

- ExecutionEngine 周辺（発注管理、リコンサイル、リスク管理）
- Monitoring（システム状態・注文状態・リスク監視、アラート送信）
- Portfolio construction（候補選定・重み付け・株数計算・セクター制限）
- Research（ファクター計算、特徴量探索）
- AI 関連機能（ニュースのセンチメント評価、レジーム判定。OpenAI API を使用）
- ツール群（Paper Trading の検証レポート出力、Streamlit ダッシュボード等）

設計方針として、DB（SQLite / DuckDB）を利用したデータ管理、外部 API 呼び出しは明示的に分離、ルックアヘッドバイアスを避ける実装がとられています。

---

## 機能一覧

- 監視（Monitoring）
  - システム状態の定期ログ（CPU / メモリ / ディスク / 実行プロセスの有無）
  - データ鮮度チェック（DuckDB に格納された株価の日付）
  - 注文滞留・約定価格異常検出
  - ドローダウン / ポジション上限の監視と kill.flag による停止指示
  - LINE への通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- 実行（Execution）
  - ブローカークライアント抽象化（本番 or Paper Trading 用 Mock）
  - OrderManager：発注作成、状態同期、重複チェック
  - Reconciler：起動時の注文・ポジション整合処理
  - RiskManager：発注前チェック（設定に基づく制限）

- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア順）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用
  - 株数（lot）決定（リスクベース / weight ベース）、投下金額スケーリング

- 研究（Research）
  - ファクター計算（Momentum, Value, Volatility, Liquidity）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント化（ai_scores への書き込み）
  - マクロ記事 + ETF ma200 乖離を用いた市場レジーム判定（market_regime へ書込）

- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.10 以上を想定（タイプヒントの構文等に依存）
- SQLite は標準ライブラリで利用可能
- システムにより追加パッケージのインストールが必要

推奨手順（UNIX/macOS）

1. リポジトリをクローン、ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   （requirements.txt が無い場合の例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   注意: `psutil` はプロセス優先度や CPU affinity 設定に使用されます。Windows / Linux / macOS の差分に対応しています。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数（デフォルト値と用途）:
   - KABUSYS_ENV: development | paper_trading | live (default: development)
   - SQLITE_PATH: data/monitoring.db (Monitoring 用 SQLite)
   - DUCKDB_PATH: data/kabusys.duckdb (DuckDB ファイル)
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 環境時の専用 SQLite)
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要に応じて）
   - KABU_API_PASSWORD: kabuステーション API パスワード（リアルブローカー利用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - PAPER_FILL_MODE: instant | partial | never | reject (Paper Trading の約定動作)
   - LOG_LEVEL: DEBUG/INFO/… 等
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring 側で使用）

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

6. DB 初期化
   - monitoring 用のテーブルはスクリプトから冪等的に作成されます（init_monitoring_db）。
   - 最初に run_monitoring/run_execution を起動することで自動作成されます。

---

## 使い方

主要な実行方法とフラグファイルの仕組みを示します。

共通
- 停止要求（監視ループやエンジンの即時停止）:
  - data/stop_requested.flag を作ると各プロセスが検知して安全に終了します（run_monitoring/run_execution が参照）。
- ExecutionEngine の強制停止シグナル:
  - kill.flag（Settings.kill_flag_path, デフォルト: data/kill.flag）は KillSwitch によって書き込まれ、ExecutionEngine に停止命令を与える目的で使用されます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag をクリアします（設定に依存）。

1) 監視ループ（SystemMonitor 単体実行）
```
# モジュールとして実行
python -m kabusys.run_monitoring
# またはファイルから (プロジェクトルートから)
python src/kabusys/run_monitoring.py
```
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は Settings.env に関係なく `sqlite_path`（本番用のパス）を使用します。
- プロセス優先度設定に psutil を使っています。権限によっては設定できない場合がありますが、警告が出るだけで継続します。

2) 実行エンジン（ExecutionEngine）
```
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録します。本番 DB と分離されます。
- 実行中の PID は `data/execution.pid` に書き込まれます。run_execution はこの PID ファイルを監視して stale PID を検出・削除します。
- 停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書き込まれた場合に検知して停止します。

3) Streamlit 監視ダッシュボード（ローカル可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視用 SQLite を読み取り専用で開き、ポジション / 注文 / システム状態 / リスクログを可視化します。

4) Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- DB が存在しない場合はエラー表示。
- デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは `PAPER_TRADING_SQLITE_PATH` 環境変数で指定可能。
- 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ等。しきい値はソース内に定義されています。

5) AI 関連（ニューススコア / レジーム判定）をコードから呼び出す
- ニューススコア:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（DuckDBPyConnection）を渡します。api_key を渡さない場合は環境変数 `OPENAI_API_KEY` を参照します（未設定なら ValueError）。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB 接続と API キーを渡します。

注意: OpenAI 呼び出しはリトライ・フェイルセーフを備えていますが、API キー・レートリミット・費用に注意してください。

---

## 主要ファイルとディレクトリ構成

以下はリポジトリ内の主要なモジュール構成（src/kabusys 配下）です。主要ファイルの役割も併記します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス定義（自動 .env 読込機能含む）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 環境で MockBroker を使用）
  - tools/
    - paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py
      - SQLite のテーブル初期化・永続化ラッパー（MonitoringDB）
    - system_monitor.py
      - システム状態・データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション数監視
    - kill_switch.py
      - kill.flag の作成 / 管理ロジック
    - alert_manager.py
      - LINE Push による通知
    - monitoring_engine.py
      - 各 Monitor を束ねて実行するエンジン
    - streamlit_dashboard.py
      - Streamlit ベースの可視化ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - execution_engine.py (参照あり)
    - broker_factory.py (参照あり)
    - ...（ブローカー API 抽象や発注レコードなど）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 株数算出・aggregate cap ロジック
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を OpenAI に投げるニュースセンチメントスコアリング
    - regime_detector.py
      - ETF ma200 とマクロ記事でレジーム判定
  - utils/
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ラッパー（psutil 使用）
  - data/  (想定)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## 重要な運用メモ / 注意点

- 環境分離:
  - `KABUSYS_ENV=paper_trading` の場合、実行エンジンは Paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、Mock ブローカーを使って本番データと分離します。監視（monitoring）は env にかかわらず `sqlite_path`（本番想定）を利用する実装箇所に注意してください（設計上の意図）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行います。また既存テーブルに列が足りない場合の簡単な ALTER（マイグレーション）処理を含みます（例: trade_logs.latency_ms, dashboard.peak_value）。

- ファイルフラグ:
  - stop_requested.flag はループを安全に終了させるためのフラグです（run_monitoring / run_execution がチェック）。
  - kill.flag はリスク条件により書き込まれ、ExecutionEngine に停止を促すためのフラグです。KillSwitch は冪等的に書き込みます。

- OpenAI API:
  - `OPENAI_API_KEY` は必須（AI 関数を使用する場合）。API 呼び出しはバックオフ・リトライやレスポンスバリデーションを実装していますが、費用管理とレート制御は運用側で注意してください。

- process priority / cpu affinity:
  - 特権が必要な設定（nice の負値など）はシステム権限により失敗する場合があります。失敗時は警告ログが出力されますが、プロセス自体は続行します。

---

## 追加情報 / トラブルシュート

- .env の自動読み込み:
  - config.py がプロジェクトルート（.git または pyproject.toml の存在）を探索し、`.env` と `.env.local` を読み込みます。OS 環境変数は保護され上書きされません。
  - 自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- ログレベル:
  - 環境変数 `LOG_LEVEL` でログレベルを制御します（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）。

- デバッグ:
  - 各コンポーネントは例外をキャッチしてログに残しつつ可能な限り継続する実装方針が取られています。問題発生時はログ（標準出力 / システムログ）を確認してください。

---

以上がこのコードベースの README です。必要であれば、導入手順のスクリプト化（例: requirements.txt / Dockerfile / systemd ユニットファイルサンプル）や、各モジュールの API 使用例（コードスニペット）を追記します。どの情報を優先して追記しましょうか？