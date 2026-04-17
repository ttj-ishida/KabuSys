# KabuSys

KabuSys は日本株の自動売買システム向けユーティリティ群です。戦略のポートフォリオ構築・位置サイズ計算、実行エンジンの起動補助、監視・アラート、研究用ファクター計算、OpenAI を使ったニュース NLP / レジーム判定などを含みます。

このリポジトリはライブラリ兼小規模なオペレーションツール群として設計されています。各モジュールはできるだけ副作用を少なく（純粋関数や明示的な DB 接続を受け取る等）実装されています。

---

## 主な特徴

- ポートフォリオ構築
  - 候補選定（スコア・等分配）
  - 重み付け（等金額・スコア加重）
  - セクター集中制限の適用
  - レジームに応じた投下資金乗数

- 位置サイズ決定
  - risk-based, equal, score ベースの発注株数算出
  - 単元（lot）丸め・集約キャップ処理

- 実行エンジン起動スクリプト
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - Paper Trading では MockBroker を使用し DB を分離

- 監視（Monitoring）
  - System / Trade / Risk の監視コンポーネント
  - SQLite に監視ログを永続化（monitoring.db）
  - LINE プッシュ通知（AlertManager）
  - Kill Switch（条件による停止フラグ自動書込）
  - Streamlit ベースの簡易ダッシュボード

- 研究用ツール
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（ランク相関）計算、統計サマリ

- AI モジュール
  - ニュースのセンチメントスコア付与（OpenAI を利用）
  - マクロニュース + ETF MA200 による市場レジーム判定
  - API 呼び出しはリトライやフェイルセーフを組み込み

---

## セットアップ

前提
- Python 3.10+（型記法に `|` を使用しているため）
- SQLite は標準ライブラリで利用可能
- DuckDB、psutil、requests、openai、streamlit 等が必要

推奨インストール（仮想環境を推奨します）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（必要に応じてその他の依存を追加してください）

.env ファイル
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先される）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

最低限設定が必要な環境変数（用途別）
- KABUSYS_ENV: 起動モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（strategy 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を使用する機能で必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）

例（.env）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方（代表的コマンド）

- 実行エンジン（ExecutionEngine）起動
  - 本番（live）や開発（development）でブローカー実接続を使う場合:
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - Paper Trading（MockBroker、専用 DB を使用）:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 動作: 起動時にプロセス優先度を high に設定し、専用または本番 SQLite に接続して実行エンジンをスレッドで走らせます。
  - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます（run_execution が監視）。

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視ループは settings.sqlite_path（monitoring.db）へ書き込みます。
  - 停止方法: data/stop_requested.flag を作成して停止。実行開始時にプロセス優先度を high に設定します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で DB パスを指定できます。指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH、さらに無ければ `data/paper_trading.db` が使われます。
  - 出力内容: 稼働率、注文成功率、送信率、レイテンシなどの集計と PASS/FAIL 判定。

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - データベースを読み取り専用で開いてダッシュボードを表示します。MonitoringEngine を先に動かしてデータを溜めてください。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）。
  - ライブラリ API を直接呼ぶ例:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
  - 実行は DuckDB 接続を渡して行います（score_news / score_regime は DuckDB 接続と日付を受け取る）。

---

## 監視・停止・フラグの取り扱い

- stop_requested.flag と kill.flag
  - run_monitoring / run_execution はプロジェクトの data/stop_requested.flag を見て停止します。
  - KillSwitch（監視モジュール）は条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - KillSwitch には冪等性があり、既存の flag があれば再書込しません。削除は手動で行うか、KillSwitch.clear() を呼ぶ実装側で行います。
- PID ファイル
  - ExecutionEngine は起動時に PID を data/execution.pid に書きます。SystemMonitor はこのファイルを見てプロセスの生存をチェックします。
- Settings.kill_flag_clear_on_start
  - 設定により起動時に kill.flag を自動的にクリアする動作を制御できます（環境変数で指定）。

---

## 主要ディレクトリ構成（src/kabusys）

- __init__.py
  - パッケージ情報（__version__ 等）

- config.py
  - 環境変数 / .env の読み込み、Settings クラス（主要設定値の取得ロジック）

- execution/
  - run_execution.py — 実行エンジン起動スクリプト（トップレベル）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - Reconciler: 再起動時の状態同期ロジック
  - OrderManager: 発注フローの上位 API

- monitoring/
  - run_monitoring.py — 監視ループ起動スクリプト
  - monitoring_db.py — SQLite テーブル初期化と CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視ロジック
  - monitoring_engine.py — 複数モニタの統合ループ
  - alert_manager.py — LINE プッシュ通知ラッパ
  - kill_switch.py — 停止フラグ書き込みロジック
  - streamlit_dashboard.py — Streamlit UI

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・キャップ・スケーリング
  - risk_adjustment.py — セクター上限・レジーム乗数

- ai/
  - news_nlp.py — ニューステキストをまとめて OpenAI に送り銘柄ごとのスコアを生成、ai_scores に書き込む
  - regime_detector.py — ETF MA200 とマクロニュースの LLM 判定を組み合わせて市場レジームを判定

- research/
  - factor_research.py — モメンタム・ボラ・バリューのファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ラッパ（psutil）

- tools/
  - paper_verification_report.py — Paper Trading DB を集計して検証レポートを作る CLI スクリプト

- data/
  - 実行時に使用する SQLite / DuckDB ファイルやフラグファイルを置く想定ディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag, data/stop_requested.flag）

---

## 開発 / 運用上の注意点

- DB の分離
  - Paper Trading モードでは必ず `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と分離すること。run_execution は KABUSYS_ENV に応じて自動選択します。

- ルックアヘッド防止
  - AI モジュールやリサーチ系の関数は内部で現在時刻を直接参照しないよう設計されており、外部から対象日を渡すことでルックアヘッドバイアスを避けるようになっています。

- フェイルセーフ
  - OpenAI API 呼び出しや外部 API 失敗時は、適切にリトライ・フォールバック（例: macro_sentiment=0）を行います。運用時は API キーのレートやコストに注意してください。

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。OS 環境変数は上書きされませんが、`.env.local` は既存の OS 環境変数以外を上書きします。自動ロード無効化には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## よく使うコマンドまとめ

- 実行エンジン（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセス
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring  # ポーリング間隔 120 秒

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README を拡張して、
- 実際の requirements.txt / poetry / pyproject.toml に基づく依存情報、
- デプロイ手順（systemd ユニット例やコンテナ化）、
- テストの書き方（モック方法、patch のポイント）
などを追加できます。必要であれば追記します。