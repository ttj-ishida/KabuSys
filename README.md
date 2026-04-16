# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ / 実行スクリプト /モニタリング /研究用ツール群）。

以下はこのリポジトリの主要な概要・セットアップ・使い方・ディレクトリ構成です。

> 注意: この README はソースコード（src/kabusys 以下）から抽出した情報に基づきます。実運用前にコードや設定を十分に確認してください。

---

## プロジェクト概要

KabuSys は以下の機能群を備えた自動売買システムのコンポーネント群です。

- 実行エンジン（ExecutionEngine）: 注文作成・送信・状態管理・リスク管理・リコンシリエーション等
- 監視（Monitoring）: システム状態、注文の滞留、約定異常、ドローダウン監視、kill-switch の発動
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイズ計算・セクター上限
- 研究モジュール: ファクター計算、特徴量探索、将来リターン / IC 計算
- AI/LLM 補助: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード など

主要な設計方針の一部:
- DuckDB / SQLite を用いたローカルデータベース中心の処理
- 本番・Paper Trading の DB 分離（paper_trading 環境）
- OpenAI 呼び出しは失敗時にフェイルセーフで継続する実装
- ランタイムの優先度設定（psutil を利用）

---

## 機能一覧（抜粋）

- SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視しログ化
- TradeMonitor: 滞留注文（stale）、約定価格の異常検出
- RiskMonitor: ドローダウン・保有銘柄上限の監視およびアラート・kill 条件判定
- KillSwitch: ファイルベースで ExecutionEngine に停止シグナル送信（data/kill.flag）
- AlertManager: LINE Messaging API による通知（クールダウン機能あり）
- MonitoringEngine: 各モニタの統合ポーリング（run モード / run_once）
- ExecutionEngine 起動スクリプト: 本番/ペーパートレードでの実行、Broker クライアントファクトリ使用
- Reconciler: 再起動時の注文・ポジション突合
- Portfolio モジュール: 候補選定 / 重み付け / position sizing / セクター制約 / レジーム乗数
- Research モジュール: ファクター・ボラティリティ・バリュー等の計算、IC/統計関数
- AI モジュール: news_nlp.score_news（ニュースを OpenAI でセンチメント評価して ai_scores に書込）、regime_detector.score_regime（MA とマクロセンチメントを合成して日次レジーム判定）
- Tools: paper_verification_report（Paper Trading の検証レポートを生成）、streamlit_dashboard（監視ダッシュボード）

---

## 必要条件（推奨）

- Python 3.9+（ソースは typing 構文や Path を多用）
- システムライブラリ / Python パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
  - その他標準ライブラリ（sqlite3, logging, threading, datetime など）

（requirements.txt は付属しないため、上記を仮想環境にインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / 配布されたソースを配置
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. data ディレクトリを作成（スクリプトは data/* を利用します）
   ```bash
   mkdir -p data
   ```
4. 必要な環境変数を設定（下記「環境変数」参照）。開発では .env / .env.local を使えます。
   自動ロード機能が有効（KABUSYS_DISABLE_AUTO_ENV_LOAD が未設定）であれば、プロジェクトルートの .env・.env.local を読み込みます。
5. （任意）Paper Trading 用 DB を初期化する場合は data/paper_trading.db を準備するか、Execution スクリプトが起動時に作成/初期化します（init_monitoring_db 等を利用）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 起動環境。valid: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API キー（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を消す（"1" にするとクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

注意: Settings クラスは環境変数の妥当性チェックを行います。必須変数が欠けると ValueError が発生します。

---

## 実行方法（主要なコマンド）

プロジェクトルートから実行することを前提に例を示します。

- 監視ループを起動（SystemMonitor を単独で動かす）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（例: 30 秒）。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring 用 DB）。

- ExecutionEngine を起動（本番または paper_trading に応じて Broker を切替）:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag（run_execution 側で監視）を作成するか、kill.flag を使用して Execution を停止させる仕組みがあります。

- Paper Trading 検証レポート（コマンドライン）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  引数 --from/--to（YYYY-MM-DD）で期間フィルタを指定できます。--db を省略すると環境変数 PAPER_TRADING_SQLITE_PATH やデフォルトを使用します。

- Streamlit 監視ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます。MonitoringEngine がデータを書き込んでいることが前提です。

- AI / レジーム判定（プログラムから呼ぶ例）:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  いずれも OpenAI の API キーが必要です。関数は DuckDB 接続オブジェクトを受け取ります。

---

## 停止・制御関連

- 停止フラグ: data/stop_requested.flag
  - run_monitoring/run_execution はこのファイル存在を監視し、存在するとループを終了またはエンジン停止します。
- Kill switch: data/kill.flag（デフォルト KILL_FLAG_PATH）
  - KillSwitch が条件を満たすとこのファイルを書き込み、外部から ExecutionEngine を停止させる仕組み（安全停止）。
  - KillSwitch は冪等的に動作し、既に存在する場合は書き換えません。
- PIDファイル: data/execution.pid
  - Execution エンジンの生存判定に使用されます。SystemMonitor は stale PID を検出して削除やリスク記録を行います。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義 / バージョン
- config.py — 環境変数 / Settings クラス（デフォルトパスやバリデーション）
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ（主なファイル）
- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化 & 永続化 API（MonitoringDB）
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor の統合ポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, ...（注文管理・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の算出（DuckDB 利用）
  - feature_exploration.py — 将来リターン / IC / 統計
- ai/
  - news_nlp.py — ニュースの LLM によるセンチメント取得と ai_scores への書込
  - regime_detector.py — MA とマクロセンチメントの合成によるレジーム判定
- utils/
  - process_priority.py — psutil 経由の優先度 / CPU affinity セット

ツール:
- tools/paper_verification_report.py — Paper Trading 検証レポート

その他:
- data/ — デフォルトの DB / PID / flag ファイルを置く想定（リポジトリには含まれないことが多い）

---

## 運用上の注意 / ヒント

- DB 初期化:
  - 監視用のスキーマは run_monitoring/run_execution 起動時に init_monitoring_db が呼ばれて作成されます。data ディレクトリの作成と書き込み権限を確認してください。
- 環境分離:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH を用い、本番 SQLite を汚さないように分離しています。
- OpenAI:
  - news_nlp / regime_detector は OpenAI API を利用します。API キーが未設定だと例外が発生する関数があります（呼び出し前にキーを渡すか環境変数 OPENAI_API_KEY を設定してください）。
  - LLM の応答失敗は基本的にフェイルセーフで 0.0 やスキップにフォールバックする設計です。
- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。psutil による権限エラーはログで無害に扱われます。
- ログ:
  - スクリプトは logging.basicConfig(level=logging.INFO) を使用します。詳細ログが必要な場合は LOG_LEVEL 環境変数や起動前に logging 設定を上書きしてください。
- テスト:
  - 本リードミーではユニットテスト手順は記載していません。各モジュールは純粋関数・副作用を分離した設計が多く、mock を用いた単体テストが実装しやすい構成です。

---

## 参考コマンドまとめ

- 仮想環境と依存インストール:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil requests openai streamlit
  ```

- 監視ループ起動:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（Paper Trading）:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

必要に応じて README に追加したい内容（例: サンプル .env.example、より詳細な運用手順、依存バージョン指定、ユニットテストの実行方法など）があれば教えてください。README をそれに合わせて拡張します。