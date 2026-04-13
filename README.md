# KabuSys — README

このリポジトリは日本株向けの自動売買／リサーチ／監視システム「KabuSys」の一部実装です。本ドキュメントはコードベース（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめた README.md です。

注意：実行には Python 3.10 以上を想定しています（型注釈に PEP 604 の記法を使用）。

---

## プロジェクト概要

KabuSys は日本株の自動売買向けに設計されたモジュール群です。主な役割は次の通りです。

- 戦略に基づく銘柄選定・配分（portfolio モジュール）
- ポジションサイズ計算・リスク調整
- 発注管理・ブローカーとの同期（execution モジュール）
- 監視（Monitoring）：プロセス・システムリソース・注文/約定状態の定期チェック、アラート送信、停止（kill）シグナル出力
- 研究用途のファクター計算・特徴量解析（research モジュール）
- ニュースを LLM によってスコアリング（ai.news_nlp）・市場レジーム判定（ai.regime_detector）
- Paper Trading の検証レポート生成用ツール

設計方針として、DB（DuckDB/SQLite）や外部 API（OpenAI, ブローカーAPI）との接続箇所は最小限に切り分けられ、テスト容易性とフェイルセーフ性（API失敗時のフォールバック、冪等なDB操作等）に配慮されています。

---

## 主な機能一覧

- portfolio
  - 候補選定（スコア順／上位N）
  - 等分配／スコア加重配分
  - ポジションサイズ算出（risk_based, equal, score）
  - セクター上限適用、レジーム乗数
- research
  - Momentum / Volatility / Value ファクター算出（DuckDB 接続）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約
- ai
  - ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定と格納（market_regime）
- execution（発注系）
  - OrderManager / Reconciler による起動時の状態復旧およびブローカー同期（再起動後の整合性維持）
  - Paper trading モードの分離（専用 SQLite DB）
- monitoring
  - SystemMonitor: CPU/Memory/Disk・プロセス・データ鮮度チェック（DuckDB の価格データを参照）
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件に応じてファイル（kill.flag）を書き込み ExecutionEngine 停止シグナルを送出
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- ユーティリティ
  - process_priority: プラットフォーム差異を吸収してプロセス優先度 / CPU affinity を設定
  - config: .env 自動ロード・Settings クラス

---

## セットアップ手順

以下はローカルで動かすための一般的な手順です。実際の依存関係はプロジェクトで管理されている requirements.txt 等に合わせてください（本コードベースではファイル未提供のため代表的なパッケージを記載します）。

1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 他に使用するブローカー SDK がある場合はそれもインストールしてください
4. プロジェクトルートに .env を用意（自動ロードされます）
   - 自動ロード条件：プロジェクトルートを .git または pyproject.toml で検出し .env / .env.local を読み込み
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨する .env の主要キー（例）

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development|paper_trading|live
- PAPER_FILL_MODE=instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- LOG_LEVEL=INFO

注意事項:
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録します。本番 DB（SQLITE_PATH）とは完全に分離されます。
- Monitoring モジュールは環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する実装箇所があります（run_monitoring.py の説明参照）。

---

## 使い方（主要スクリプト・コマンド）

以下はリポジトリ内の実行可能スクリプトの代表例です。いずれもプロジェクトの仮想環境内で実行してください。

- 監視ループを起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - ログ出力は標準 logging を使用。起動時にプロセス優先度を "high" に設定しようとします。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
  - 起動時に process priority を "high" に設定

- Streamlit 監視ダッシュボードを起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブで表示

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH の代替）
  - 出力は標準出力にテキストレポートを表示します（稼働率・注文成功率・送信率・P95 レイテンシ等）

- AI モジュール（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（DuckDBPyConnection）
    - target_date: date オブジェクト
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意: OpenAI API を利用する機能は API キーが必要です。API 呼び出しは結果の妥当性チェック・リトライ・フェイルセーフ（失敗時はスコア0.0 など）を行いますが、課金やレート制限に注意してください。

---

## 設定関連（Settings / .env）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env をロードします。
  - .env.local は上書き可能（override=True）
  - OS 環境変数は保護され、.env がそれらを上書きしないようになっています。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

- 主要な Settings プロパティ（概要）
  - env: KABUSYS_ENV（development, paper_trading, live）
  - duckdb_path: DuckDB のパス（デフォルト data/kabusys.duckdb）
  - sqlite_path: monitoring 用 SQLite（デフォルト data/monitoring.db）
  - paper_sqlite_path: paper trading 用 SQLite（デフォルト data/paper_trading.db）
  - pid_file_path / kill_flag_path: 監視・停止用ファイルパス
  - PAPER_FILL_MODE: paper trading の約定動作（instant, partial, never, reject）
  - CPU/MEM/DISK 閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

---

## ディレクトリ構成（抜粋）

主要なファイル・モジュールのツリー（src/kabusys 以下の主要ファイルを列挙）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env ローダと Settings
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数計算・集約キャップ・単元丸め
    - risk_adjustment.py            — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py           — ETF MA200 + マクロニュースでレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ定義 + MonitoringDB ラッパ
    - system_monitor.py            — CPU/MEM/DISK/プロセス/データ鮮度監視
    - trade_monitor.py             — 滞留注文・約定異常の検出
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag の作成 / 管理
    - alert_manager.py             — LINE Push API 通知
    - monitoring_engine.py         — 複数 Monitor を束ねるエンジン + アラート連携
    - streamlit_dashboard.py       — streamlit での監視ダッシュボード
  - utils/
    - __init__.py
    - process_priority.py          — OS 間差異吸収のプロセス優先度/affinity 設定ユーティリティ
  - execution/
    - order_manager.py             — 発注ステートマシン外向き API（途中まで掲載）
    - reconciler.py                — 起動時の注文・ポジション整合性チェック
    - order_repository.py          — （リポジトリ層: SQLite）※実装は省略箇所あり
    - ...                          — ブローカー関連（factory / API）や他コンポーネント

上記は主要ファイルのみ抜粋しています。詳細は src/kabusys 以下の各モジュールを参照してください。

---

## 運用上の注意点 / 実装上の重要点

- Monitoring と Execution の DB 分離
  - Paper Trading モードでは発注系 DB を paper_sqlite_path に分離します。監視 DB は環境にかかわらず monitoring.db を使う実装箇所があるため、運用時は DB パスを確認してください（run_monitoring は本番 sqlite_path を使用する旨のドキュメント記載あり）。
- Kill Switch
  - RiskMonitor の判定により kill.flag を書き込むと、ExecutionEngine 側で検出して安全に停止する設計になっています。kill.flag の場所は Settings.kill_flag_path で指定。
- OpenAI 使用
  - ai モジュールは OpenAI API を用います。API キー（OPENAI_API_KEY）を .env または引数で渡してください。API レスポンスのバリデーション・リトライ・クリッピングが実装されていますが、API レートや課金に注意して運用してください。
- 冪等性とマイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブル作成・簡単なマイグレーション（カラム追加）を行います。
- テスト性
  - OpenAI / プロセス設定など外部依存を差し替え可能なように設計されています（関数の patch がしやすい）。

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール（例）
  - pip install duckdb psutil requests openai streamlit
- 監視起動
  - python -m kabusys.run_monitoring
- 発注エンジン起動
  - python -m kabusys.run_execution
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい具体的な情報（例えば使用している外部ブローカー SDK の設定手順、CI/デプロイ手順、より詳しい .env.example）や、実行時のログ例、API レート制御のチューニング例などがあれば教えてください。必要に応じて追記します。