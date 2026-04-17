# KabuSys

日本株向け自動売買・リサーチ基盤（リポジトリ抜粋）
この README はコードベースの主要機能・セットアップ・実行方法・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとそれを支援するリサーチ／モニタリングツール群です。  
主な目的は以下の通りです。

- 戦略に基づく銘柄選定・ポートフォリオ構築・発注（ExecutionEngine）
- システム稼働状況・注文状態・リスク（ドローダウン等）の継続監視（Monitoring）
- ファクター計算・特徴量探索・将来リターン評価など研究用モジュール（Research）
- ニュースを LLM（OpenAI）でスコアリングして市場レジームやシグナルに活用（AI）
- Paper Trading（ペーパートレード）機能と、その検証レポート生成

主要コンポーネントは基本的に「DB（SQLite / DuckDB）を介した処理」「純粋関数群（ポートフォリオ計算等）」「外部 API 呼び出し（kabuステーション, J-Quants, OpenAI）」で構成されています。

---

## 機能一覧

- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト（python -m kabusys.run_execution）
  - paper_trading 環境時は MockBroker を使用し、Paper 用 SQLite（data/paper_trading.db）へ記録
  - プロセス優先度の設定・PID ファイル管理・停止フラグ対応
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプトによる定期ポーリング（既定 60 秒、MONITOR_POLL_INTERVAL で上書き可）
  - 監視ログの永続化（SQLite）と簡易アラートトリガ（kill.flag）
- Portfolio（純粋関数）
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター上限、レジーム乗数
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（情報係数）、統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai_scores テーブルへ保存）
  - マクロニュースを用いた市場レジーム判定（market_regime テーブルへ保存）
  - 再試行とフェイルセーフを実装（API失敗時は中立スコア等で継続）
- ユーティリティ
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 環境の準備（仮想環境推奨）
   - Python 3.10+ を想定
   - 依存ライブラリ（例）
     - duckdb
     - psutil
     - openai（AI 機能利用時）
     - PyYAML（config の解析・validate_config の拡張検証に任意）
   - 例：
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
     ※ requirements.txt が無ければ必要なパッケージを個別にインストールしてください。

3. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     - J-Quants トークン、kabuステーション API パスワードなど必須項目を入力します。
     - .env は Git にコミットしないでください（機密情報含む）。
   - 手動で作成する場合は .env.example を参考に。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告もエラー扱い
   ```

5. DB 初期化
   - monitoring 用の SQLite（デフォルト `data/monitoring.db`）や DuckDB（`data/kabusys.duckdb`）は初回起動時にテーブルが作成されます。
   - Paper Trading を使う場合は `data/paper_trading.db` を用意（run_execution が必要に応じて作成／初期化する）。

6. (任意) OpenAI 利用
   - ニュース NLP / regime 判定を使う場合は環境変数 `OPENAI_API_KEY` に API キーを設定するか、関数呼び出し時に引数で渡してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注はモッククライアントを使い data/paper_trading.db に記録
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring は常にこの本番パスを参照
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用、任意）
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）

---

## 使い方

基本的にモジュールとして起動します。

- ExecutionEngine を起動（本番 or paper_trading 判定は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を High に設定します。
  - Paper Trading 環境では MockBroker を使用し、paper_trading 用 DB に書き込みます。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると順次安全停止します。
  - ExecutionEngine 側の kill スイッチは監視プロセスが data/kill.flag を書き込むことで停止されます。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path（SQLITE_PATH）を使用してログを記録します。
  - 停止: data/stop_requested.flag を作成すると監視ループを終了します。

- .env 対話式設定
  ```
  python -m kabusys.config_setup
  ```

- 設定の静的検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム呼び出し）
  - ニューススコアリング（プログラム内）
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジームスコア（プログラム内）
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - どちらも OPENAI_API_KEY を使う場合は環境変数に設定可能。API 呼び出しはリトライ・フェイルセーフ実装あり。

注意:
- run_monitoring と run_execution はそれぞれ stop フラグ（data/stop_requested.flag）を見て終了します。  
- KillSwitch（監視側）が閾値を超えた場合 data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — （未表示: 通知管理）
  - execution/               — 発注関連（OrderRepository / OrderManager / Engine 等）※詳細はリポジトリ参照
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 株数計算・aggregate cap
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロ NLP）
  - data/                    — 実行時生成される DB / フラグファイル想定場所
    - monitoring.db (SQLITE_PATH のデフォルト)
    - kabusys.duckdb (DUCKDB_PATH のデフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
    - execution.pid / stop_requested.flag / kill.flag

---

## 注意事項 / ベストプラクティス

- 機密情報（API トークンなど）は .env に保存し、決して Git に commit しないでください。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start=0 を推奨（自動クリアは危険）。
- Monitoring は常に SQLITE_PATH を使用するため、paper_trading 環境でも監視ログは本番用 DB に残ります（設計上の仕様）。
- OpenAI を使う機能は API のレート制限や料金を伴います。API キーは適切に管理し、テスト時はモックや小さなデータサイズで検証してください。
- DB マイグレーションは monitoring_db.init_monitoring_db にて簡易対応あり（列追加等）。

---

必要であれば、README に含める具体的なコマンド例や起動フロー図、各モジュールの詳細ドキュメント（API サーフェス、戻り値形式、エラー挙動）を追記します。どの項目を詳述しましょうか？