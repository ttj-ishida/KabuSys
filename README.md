# KabuSys

日本株自動売買システムの一部モジュール群。信号生成・ポートフォリオ構築・発注実行・監視・リサーチ・AI（ニュースNLP / レジーム検出）等の機能を含むライブラリ/実行スクリプト群です。

---

## プロジェクト概要

このリポジトリは、以下の責務を持つモジュール群から構成されています。

- 発注エンジン関連（ExecutionEngine、OrderManager、OrderRepository、Reconciler 等）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、AlertManager）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、株数決定）
- リサーチ（ファクター計算、特徴量探索、IC 計算 等）
- AI モジュール（ニュースセンチメント解析、レジーム判定。OpenAI API を利用）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）
- ユーティリティ（設定管理、プロセス優先度設定等）

設計上、DuckDB を用いた履歴データ参照（prices_daily / raw_financials / raw_news 等）と、SQLite による監視ログ・注文ログ永続化を分離しています。Paper Trading（KABUSYS_ENV=paper_trading）時は発注処理をモック化して本番 DB と分離します。

---

## 主な機能一覧

- 実行系
  - OrderManager: 発注状態管理・重複防止
  - Reconciler: 再起動時の注文・ポジション照合
  - Engine: 発注セッション実行（run_execution.py で起動）

- 監視系
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限チェックとアラート/kill flag 発行
  - AlertManager: LINE Push による通知
  - MonitoringEngine: これらをまとめたポーリング実行（run_monitoring.py）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等配分 / スコア加重（calc_equal_weights, calc_score_weights）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定（calc_position_sizes）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計

- AI
  - news_nlp.score_news: raw_news をまとめて LLM に送り銘柄ごとのスコアを ai_scores テーブルに書込
  - regime_detector.score_regime: ma200 とマクロニュースセンチメントを合成して market_regime を更新

- 運用ツール
  - paper_verification_report: Paper Trading の検証レポート生成
  - streamlit_dashboard: 監視 DB のダッシュボード表示

---

## 必要環境・依存パッケージ

推奨 Python バージョン: 3.10+（ソース中の型注釈で | 演算子を使用）

主なランタイム依存:
- duckdb
- psutil
- requests
- streamlit （ダッシュボードを使う場合）
- openai （AI モジュールを使う場合）
- sqlite3（標準ライブラリ）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

（プロジェクトに requirements.txt があればそれを使ってください。）

---

## 環境変数（主なもの）

設定は .env / .env.local または OS 環境変数で指定できます。config.Settings が自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（"1" で有効）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値

（上記は主要なもののみ抜粋。config.Settings を参照すると全項目が確認できます。）

---

## セットアップ手順（例）

1. リポジトリをチェックアウト
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. data ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
5. .env をプロジェクトルートに作成し必要な環境変数を設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）
6. DuckDB / SQLite データファイルを準備（既存データがない場合、多くのテーブルは実行時に自動作成されます）

注意:
- monitoring のテーブルは init_monitoring_db() により冪等に作成 / マイグレーションされます（run_* スクリプトが呼び出します）。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path を使用します。

---

## 使い方（代表的なコマンド）

プロジェクトルートから Python モジュールとして実行できます（パッケージインポートパスが通ることが前提）。

- 監視プロセス起動（MonitoringEngine を単独で回す簡易スクリプト）
```
python -m kabusys.run_monitoring
# または (ポーリング間隔を環境変数で変更)
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い data/paper_trading.db に記録します。起動時に data/stop_requested.flag があると起動せず終了します。実行中に stop flag を書くと安全停止します。

- Paper Trading 検証レポート（コマンドライン）
```
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB は data/paper_trading.db。--db で指定可。
```

- Streamlit ダッシュボード（監視 DB を可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI / リサーチ関数をプログラムから呼ぶ
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="...")  # 戻り値: 書き込んだ銘柄数
    ```
  - レジームスコア:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - ファクター計算:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    records = calc_momentum(duckdb_conn, target_date)
    ```

---

## 運用上のポイント

- kill.flag（デフォルト data/kill.flag）を書くと ExecutionEngine に停止シグナルを出します（KillSwitch により評価されます）。run_execution と run_monitoring は stop flag の検知で停止処理を行います。
- PID ファイル（data/execution.pid）を利用して実行プロセスの生存を監視します。stale PID 検知時は自動的に削除・ログ記録します。
- Monitoring は本番用の sqlite_path を参照して永続化します（run_monitoring は環境に関係なく本番 sqlite_path を使用）。
- Paper Trading は本番 DB と完全に分離されるよう設計されています（settings.paper_sqlite_path を使用）。

---

## ディレクトリ構成

概略（src/kabusys 配下）:

- kabusys/ (パッケージルート)
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 操作用ラッパー
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 監視エンジン
    - alert_manager.py — LINE 通知
    - kill_switch.py — kill.flag の管理
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ... — 発注関連
  - portfolio/
    - portfolio_builder.py, risk_adjustment.py, position_sizing.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — リサーチ用関数群
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI）
  - data/ (運用上のファイル配置想定)
    - monitoring.db, kabusys.duckdb, paper_trading.db, kill.flag, execution.pid, stop_requested.flag など

（実際のリポジトリでは src/ 以下に配置されています。プロジェクトルートでパッケージとして実行してください。）

---

## 開発・拡張のヒント

- 設定は Settings クラスを経由して取得するため、テスト時は環境変数や KABUSYS_DISABLE_AUTO_ENV_LOAD を使って挙動を切り替えられます。
- AI 呼び出し部分は外部 API の失敗をフェイルセーフに扱う設計になっているため、ローカルテスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えると良いです。
- DuckDB を使用したファクター計算やニュース集約は副作用を持たない純粋な関数として設計されています。リサーチ用途で再利用しやすくなっています。

---

## 補足

必要に応じて README を拡張します。例えば:
- requirements.txt / poetry / pyproject.toml に基づくインストール手順
- 実行時のログ設定例（LOG_LEVEL）
- 具体的な .env.example の追記
ご希望があれば追記します。