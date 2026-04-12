# KabuSys

日本株向けの自動売買システム（モジュール群）。戦略・ポートフォリオ構築、発注実行、監視・アラート、研究向けファクター計算、AI（ニュースのセンチメント）評価などを含む。コードは純粋関数・小さな責務単位で設計されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を持つコンポーネント群で構成された自動売買プラットフォームです。

- Execution: ブローカークライアント経由の発注、注文管理、リコンシリエーション
- Monitoring: プロセス・システム状態、注文の滞留・約定異常、リスク監視、Kill Switch、LINE通知、監視用 DB／Streamlit ダッシュボード
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整
- Research: DuckDB を使ったファクター計算 / 特徴量探索
- AI: OpenAI（gpt-4o-mini）を用いたニュース NLP（センチメントスコア）やレジーム判定
- Tools: Paper Trading 検証レポート生成などのユーティリティスクリプト

設計上の特徴：
- DuckDB / SQLite をデータ層として利用（ローカルでの高速集計と永続化）
- 環境変数 / .env ファイルでの設定管理（自動ロード機能あり）
- Paper trading と本番（live）を明確に分離（専用 SQLite DB）
- 外部 API（OpenAI / LINE / ブローカー）呼び出しはフェイルセーフ設計（失敗時は継続）

---

## 主な機能一覧

- system_monitor: CPU/メモリ/ディスク/データ鮮度 / 実行プロセス監視とログ化
- trade_monitor: 注文滞留（stale orders）と約定異常価格の検出
- risk_monitor: ドローダウン、ポジション上限の監視とリスクログ
- kill_switch: ファイル（data/kill.flag）による ExecutionEngine 停止シグナル生成
- alert_manager: LINE Messaging API を使ったアラート送信（クールダウン管理）
- monitoring_engine: 上記モニタをまとめて定期実行（ポーリング）
- execution_engine + order_manager: 注文の生成・送信・同期（リコンシリエーション含む）
- portfolio utilities: 候補選定 / 等配分・スコア加重・リスクベースの株数算出
- research: Momentum / Value / Volatility 等のファクター計算、IC 等の評価
- ai/news_nlp: ニュースを集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores に書込
- tools/paper_verification_report: Paper Trading の検証レポート生成
- Streamlit ダッシュボード: 監視用の簡易 UI（read-only 接続）

---

## 前提（Prerequisites）

- Python 3.10 以上（| 型注釈等を使用）
- pip（パッケージ管理）
- 推奨パッケージ（主要な要件）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
  - その他（標準ライブラリを除く）

（実運用時は requirements.txt を用意して pip install -r requirements.txt を推奨）

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の運用では追加の依存がある場合があります。requirements.txt がある場合はそれを使用してください。

4. データディレクトリの作成（任意、デフォルトは data/ 下）:
   - mkdir -p data

5. 環境変数設定:
   - プロジェクトルートに .env（/ .env.local）を作り、必要な環境変数を設定できます。自動ロード機能により OS 環境変数と .env の読み込みが行われます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（代表）:
- KABUSYS_ENV: 起動環境（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合、必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: 実行プロセス PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60） — run_monitoring.py 用

参考: 設定値は kabusys.config.Settings クラスにまとめられています。値の検証やデフォルトもここで定義されています。

---

## 使い方（実行例）

- 監視ループ（SystemMonitor のポーリング）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  run_monitoring はプロセス優先度を "high" に設定し、monitoring 用 DB（Settings.sqlite_path）を使って初期化します。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - Paper Trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading は settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離されます。
  - 実行開始時にプロセス優先度を "high" に設定します。

- Paper Trading 検証レポートの生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード（read-only）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既に監視 DB が存在しないと起動時にエラー表示されます（MonitoringEngine を先に起動）。

---

## 環境変数の挙動（抜粋）

- 自動 .env ロード:
  - プロジェクトルート (.git または pyproject.toml がある場所) を探索し、`.env` と `.env.local` を自動で読み込みます。
  - OS 環境変数が優先され、`.env.local` は上書き（override）されます。
  - ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- KABUSYS_ENV:
  - 値: development | paper_trading | live
  - paper_trading の場合、run_execution は paper_trading DB を使い MockBroker を利用する設計（実際の BrokerFactory の実装に依存）。

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔（秒）を上書きします。0 以下や不正値はデフォルト（60秒）にフォールバックします。

- OPENAI_API_KEY:
  - AI モジュール（news_nlp, regime_detector）で使用。未設定の場合、該当機能を呼び出すと ValueError が出ます（もしくはフェイルセーフで 0.0 を使う箇所もあります）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- run_monitoring.py              — Monitoring のポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading 検証レポート
- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - position_sizing.py            — 株数計算・スケール調整
  - risk_adjustment.py            — セクター上限・レジーム乗数
- monitoring/
  - monitoring_db.py              — SQLite 監視 DB（初期化・読み書き）
  - system_monitor.py             — システム / データ鮮度監視
  - trade_monitor.py              — 注文滞留 / 約定異常監視
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag の作成 / 削除ロジック
  - alert_manager.py              — LINE 通知ラッパ
  - monitoring_engine.py          — 各 Monitor をまとめるエンジン
  - streamlit_dashboard.py        — Streamlit での監視ダッシュボード
- execution/
  - order_manager.py              — 注文ワークフロー（作成/送信/同期）
  - reconciler.py                 — 再起動後のリコンシリエーション
  - ...（ブローカー API / order_repository 等のコンポーネントが想定）
- research/
  - factor_research.py            — Momentum / Volatility / Value の計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ
- ai/
  - news_nlp.py                   — ニュースの LLM スコアリング
  - regime_detector.py            — マクロ＋MA200 によるレジーム判定
- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (デフォルトの出力ディレクトリ、実行時に自動生成されるファイル)
  - kabusys.duckdb (デフォルト)
  - monitoring.db (監視 SQLite)
  - paper_trading.db (paper trading 用 SQLite)

（実際のプロジェクトでは execution/ 内に broker_factory, order_repository, order_record などのファイルがあります）

---

## 運用上の注意 / トラブルシューティング

- OpenAI / ブローカー / LINE の API キーや認証情報は適切に保護してください。
- run_monitoring / run_execution はプロセス優先度を上げようとします（psutil を使用）。権限不足で警告が出ることがありますが、動作自体は継続します。
- Paper Trading と本番 DB は完全分離する設計です。paper_trading モードを使うと data/paper_trading.db が利用され、本番 monitoring.db を上書きしません。
- monitoring_db.init_monitoring_db は冪等でテーブル追加・簡単なマイグレーションを行います。既存 DB のスキーマ変更は安全性を確認した上で行ってください。
- Streamlit ダッシュボードは読み取り専用（URI を mode=ro で開く）にして運用することを推奨します。
- kill.flag による停止シグナルはファイル存在で判定します。kill.flag をクリアするには KillSwitch.clear() を呼ぶか、ファイルを手動削除してください。

---

## 開発 / 貢献

- 小さな責務ごとにユニットテストを書くことを推奨します（外部 API 呼び出しはモック化）。
- .env.example を用意して必須環境変数の雛形を提供するのが便利です。
- 各モジュールは副作用を極力排し、純粋関数（research / portfolio）と副作用を持つ I/O 層（monitoring_db, broker）を明確に分離しています。拡張時はこの分離を維持してください。

---

必要であれば README にサンプル .env、requirements.txt の推奨内容、より詳細な起動手順（systemd ユニットや Dockerfile）などを追加します。どの情報を優先して追加しますか？