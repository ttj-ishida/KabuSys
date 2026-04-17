# KabuSys

日本株向けの自動売買システムのコンポーネント群（ライブラリ & 実行スクリプト）。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース評価などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下のような役割を持つモジュール群で構成されています。

- ExecutionEngine：ブローカーと連携して注文発行・状態管理・リスク管理を行う
- Monitoring：システム状態・注文状態・リスク（ドローダウン等）を定期的に監視しログ／アラート／Kill Switch を扱う
- Portfolio：銘柄選定、重み計算、ポジションサイズ計算、リスク調整の純粋関数群
- Research：DuckDB 上の株価・財務データからファクターや将来リターン、IC 等を計算
- AI：OpenAI を用いたニュースのセンチメントスコアリングや市場レジーム判定
- Tools：Paper Trading 検証レポート生成などのユーティリティ

設計上の特徴：
- DuckDB / SQLite を用いたローカルデータ処理
- 環境変数（.env / .env.local）の自動読み込み（必要に応じて無効化可）
- Paper Trading モード（本番 DB と分離された専用 SQLite を使用）
- フェイルセーフ設計（外部 API の失敗時はフェイルオーバーして継続）

---

## 主な機能一覧

- 注文管理（OrderManager）と起動時の自動リコンシリエーション（Reconciler）
- ExecutionEngine による注文実行・リスク管理（RiskManager）・約定管理
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）：
  - CPU/メモリ/ディスク監視、プロセス死活検知、データ鮮度チェック
  - 滞留注文検出・約定価格異常検出・ドローダウン / ポジション上限監視
  - kill.flag による外部からの強制停止シグナル
  - LINE へのアラート送信（AlertManager）
- Streamlit ベースの監視ダッシュボード（read-only で monitoring DB を参照）
- Research：モメンタム／ボラティリティ／バリュー等のファクター計算、IC や統計サマリ
- AI：
  - news_nlp.score_news: raw_news から銘柄ごとのセンチメントを LLM（OpenAI）で算出し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM センチメントを組み合わせて市場レジームを判定
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発・ローカル実行向け）

前提：Python 3.9+（プロジェクトで想定される互換性を満たすバージョン）を想定。

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 基本的に以下パッケージが必要です（環境によって追加が必要になることがあります）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. .env ファイルの作成
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（最低限確認すべきもの）:
     - JQUANTS_REFRESH_TOKEN — （必須）J-Quants 用トークン
     - KABU_API_PASSWORD — （必須）kabuステーション API 用パスワード
     - OPENAI_API_KEY — （AI 機能を使う場合）OpenAI API キー
     - KABUSYS_ENV — one of development | paper_trading | live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring 用）

5. データディレクトリ
   - デフォルトで data/*.db, data/*.flag, data/*.pid といったファイルを作成します。必要に応じて `data/` を作成してください。

---

## 使い方（主要な実行方法）

スクリプトはパッケージとしてモジュール実行できます（プロジェクトルートから実行することを想定）。

1. Execution Engine（発注エンジン）を起動
   - 本番/開発/ペーパートレードは環境変数 `KABUSYS_ENV` によって切り替えられます。
   - Paper Trading の場合、MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ保存されます。
   - 実行例:
     - python -m kabusys.run_execution
     - あるいは python src/kabusys/run_execution.py

   - 停止: 外部から停止するには `data/stop_requested.flag` を作成するか、kill スイッチ (`data/kill.flag`) を使います。
   - 実行時はプロセス優先度を "high" に設定しようとします（権限がない場合は警告のみ）。

2. Monitoring（監視ループ）を起動
   - 監視はデフォルトで本番 sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存せず本番 DB を参照する意図）。
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
   - 実行例:
     - python -m kabusys.run_monitoring
     - あるいは python src/kabusys/run_monitoring.py

   - 監視ループは `data/stop_requested.flag` を検知すると終了します（Execution 側と同様）。

3. Streamlit ダッシュボード
   - 監視 DB（SQLite）を読み取り専用で表示します。
   - 実行例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート
   - Paper Trading の SQLite を対象に期間指定で検証レポートを出力します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を明示する場合: --db path/to/db

5. AI 機能
   - ニュースのセンチメントスコア取得:
     - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
     - API キーが未指定の場合は環境変数 OPENAI_API_KEY を参照します（未設定だと例外）。
   - 市場レジーム判定:
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意: OpenAI 呼び出しはレート制限・5xx 等でリトライ処理を行いますが、失敗した場合はフェイルセーフ（スコア 0.0 など）で継続する設計の箇所があります。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による LINE 通知用
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

Settings クラスにより値の検証・デフォルトが管理されています。必要なキーが欠けると起動時に例外が発生します。

---

## 操作上の注意

- Paper Trading モードでは本番 DB と分離されるよう設計されています。実際に本番資金を動かす前に Paper Trading で十分に検証してください。
- kill.flag / stop_requested.flag / execution.pid 等のファイルを data/ 下に配置してプロセス間の同期・停止制御を行います。これらは手動生成・削除が可能です（KillSwitch による制御）。
- OpenAI を用いる機能は API キーとコストに注意してください。大量バッチ処理時はレート制限に留意する必要があります。
- 一部の操作（プロセス優先度や CPU affinity の設定）は OS 権限や環境によりスキップされます（警告ログのみ）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読込ロジック（.env 自動読み込み含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 単独ポーリング起動スクリプト

サブパッケージ：
- ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA を用いたレジーム判定
- execution/
  - order_manager.py — 注文の作成・送信・同期を扱う
  - reconciler.py — 起動時の注文・ポジション再照合（自動復旧）
  - （その他 execution 系モジュールが存在します）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（テーブル初期化・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク・プロセス/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常の監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成/管理
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 各モニタを束ねる実行エンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・制約適用
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補助:
- data/ — 実行時に作成される DB / flag / pid ファイルを格納する想定ディレクトリ（プロジェクトルート）

---

## 参考コマンドまとめ

- Execution 起動：
  - python -m kabusys.run_execution
- Monitoring 起動：
  - python -m kabusys.run_monitoring
- Streamlit Dashboard：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL から関数呼び出し（例）：
  - from kabusys.ai.news_nlp import score_news

---

## 開発メモ / 注意事項

- Settings モジュールはプロジェクトルート（.git または pyproject.toml の存在）を基に .env 自動読み込みを試みます。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB と SQLite の両方を使用します。DuckDB はリサーチ／ファクター計算等の大規模分析向け、SQLite は監視ログ・オーダーログ保存向けに使用します。
- OpenAI 関連の呼び出しは retry/backoff を実装していますが、API 仕様変更に伴う例外ハンドリングの見直しが必要になることがあります。
- モジュールや関数はドキュメント文字列で意図・入出力・副作用が明示されています。ロジック変更時は docstring の整合性も必ず更新してください。

---

README は以上です。必要であれば、次の内容について追記できます：
- 実際に期待される .env.example のテンプレート
- 開発用の unit テスト実行方法
- requirements.txt / Dockerfile のサンプル

どの部分を詳細化しますか？