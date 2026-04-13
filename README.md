# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群を含む軽量フレームワークです。本リポジトリは主に次の機能を提供します：発注実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、ファクター計算／研究ユーティリティ、ニュース NLP（OpenAI）連携など。

以下はコードベース（src/kabusys 配下）に基づく README です。

---

## 概要

- 発注・復旧・リスク管理を行う Execution モジュール
- Execution の稼働状況やトレードの健康度を記録・監視する Monitoring モジュール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）用の純関数群
- DuckDB を用いたファクター計算・リサーチモジュール
- OpenAI を使ったニュースセンチメント評価（ai モジュール）
- Streamlit で稼働状況を可視化するダッシュボード
- Paper Trading 用ツール（検証レポート生成など）

設計上のポイント：
- .env ファイルからの設定読み込みをサポート（自動ロードはプロジェクトルートに .git または pyproject.toml が存在する場合に有効）
- KABUSYS_ENV による動作モード（development / paper_trading / live）
- Paper Trading モードでは実際のブローカーと書き込み先 DB を分離（デフォルト: `data/paper_trading.db`）
- 監視ログは SQLite（monitoring.db）、時系列や分析には DuckDB を利用

---

## 主な機能一覧

- Execution
  - 発注の作成 → 送信 → 状態同期（Reconciler による起動時の自動復旧）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）や約定ログ保存

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - KillSwitch：条件に応じて flag ファイルを作成し ExecutionEngine に停止シグナルを送出
  - AlertManager：LINE Push による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（read-only DB 表示）

- Portfolio
  - 候補選定（スコア順、上位N）
  - 重み計算（等配分 / スコア加重）
  - セクター集中制限の適用
  - ポジションサイズ計算（lot 単位丸め、risk-based 等）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - ニュースの銘柄別センチメントスコア化（OpenAI API を利用）
  - 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）

- Tools
  - Paper Trading の検証レポート生成スクリプト（期間指定可能）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子等を使用）
- SQLite は標準ライブラリ
- DuckDB / psutil / requests / openai / streamlit などの外部パッケージが必要

1. 仮想環境の作成（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※実際のプロジェクトでは requirements.txt / pyproject.toml を用意することを推奨します。

3. 環境変数（.env）設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数が優先され、同名キーの保護あり）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（または運用で必要になりうる）環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必要な機能を使う場合）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- OPENAI_API_KEY — OpenAI を使う場合
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合
- KABUSYS_ENV — one of: development / paper_trading / live（デフォルト: development）

主な DB 関連環境変数（任意、デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject、default: instant)

監視関連:
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60秒）。0 以下や不正な値はデフォルトにフォールバックします。

---

## 使い方

実行スクリプト（モジュールとして起動）:

- 監視ループを起動する（Monitoring の単独実行）
  ```
  # プロジェクトルートで
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書きできます（秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは常に production DB 想定で記録される）。

- Execution エンジンを起動する（発注実行）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（Paper Trading 用）を使用し、デフォルトで `data/paper_trading.db` に書き込みます。
  - 起動時に Reconciler による自動復旧（OrderSent 情報の同期）を行います。
  - 起動直後に kill flag を消去する設定（Settings.kill_flag_clear_on_start）を環境変数から制御できます。

- Paper Trading 検証レポート生成（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する例
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit ダッシュボード（監視用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 指定 DB を read-only モードで開き、Overview / Positions / Orders / System タブを表示します。
  - DB が存在しない場合は「MonitoringEngine を先に起動してください」というメッセージが出ます。

ライブラリ関数の利用（例）:
- OpenAI を使ったニューススコアリング（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（DuckDBPyConnection）を受け取り、DB テーブル（raw_news / news_symbols / ai_scores / prices_daily 等）を参照します。

運用上の注意:
- 実行プロセスは起動時にプロセス優先度を "high" に設定するようになっています（psutil を使用）。権限不足時は警告が出てスキップされます。
- KillSwitch は条件（ドローダウンやポジション上限）で flag ファイルを書き、ExecutionEngine に停止を促します。flag が既に存在する場合は上書きしません。
- Paper Trading では実口座に影響を与えないよう DB を分離しています。実運用時は KABUSYS_ENV を `live` に設定してください。

---

## よく使う環境変数まとめ（例とデフォルト）

- KABUSYS_ENV=development | paper_trading | live (default: development)
- MONITOR_POLL_INTERVAL=60
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant | partial | never | reject (default: instant)
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- OPENAI_API_KEY=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋 / 説明）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（自動 .env ロード、必須チェック、既定値）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・CRUD ラッパー
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度のチェック
  - trade_monitor.py — 滞留注文 / 約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — flag ファイルによる停止シグナル発行
  - alert_manager.py — LINE 通知（クールダウン）
  - monitoring_engine.py — 各 Monitor の束ねラッパ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・丸め・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- execution/
  - order_manager.py — 発注管理（OrderState 機構を操作）
  - reconciler.py — 起動時の注文・ポジションの突合
  - ...（ブローカ関連、order_repository 等はコードベースの他ファイルに存在）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成（CLI）

その他:
- data/ (デフォルトの DB 保存先や PID/flag の配置先)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag

---

## 運用上のヒント / トラブルシューティング

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成・ALTER を行います。既存 DB に新カラムがない場合は自動的に追加します。
- Read-only で Streamlit を使う場合:
  - スクリプトでは sqlite の URI を `Path.resolve().as_uri() + "?mode=ro"` として開いています。別プロセスで書き込み中でも参照可能です。
- OpenAI 利用時:
  - API 呼び出しは再試行・バックオフ処理を実装しています。API キーが未設定の場合は例外が出ます。テスト時は _call_openai_api をモックできます。
- プロセス優先度・CPU affinity:
  - set_process_priority, set_cpu_affinity は psutil を利用。権限不足や未対応 OS の場合は警告を出してスキップします。

---

## 参考コマンドまとめ

- 仮想環境作成・起動
  - python -m venv .venv && source .venv/bin/activate

- 必要パッケージインストール
  - pip install duckdb psutil requests openai streamlit

- 監視開始
  - python -m kabusys.run_monitoring

- 実行エンジン開始（Paper Trading モード例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、この README をベースに「環境変数のテンプレート (.env.example)」や「運用手順（systemd ユニット・ログローテーション・バックアップ）」のセクションも作成します。どの情報を追加希望か教えてください。