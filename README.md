# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは取引ロジック（execution）、ポートフォリオ構築（portfolio）、ファクター計算・研究（research）、AI を使ったニュースセンチメント（ai）、監視・アラート（monitoring）など、運用に必要なコンポーネント群を収めています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 監視ループ起動
  - ExecutionEngine 起動
  - Paper Trading 検証レポート
  - Streamlit ダッシュボード
- 環境変数（主なもの）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を持つ、自動売買システムの基盤です。

- 取引発注と注文管理（OrderManager / ExecutionEngine）
- リコンシリエーション（再起動時の同期）
- リスク管理（ドローダウン監視、ポジション上限など）
- モニタリング（システム状態、注文滞留、アラート送信）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、株数算出）
- 研究用ファクター計算（momentum / volatility / value 等）
- ニュースセンチメント評価（OpenAI を利用した LLM スコアリング）
- 運用支援ツール（paper trading レポート、streamlit ダッシュボード）

設計方針の一例:
- DuckDB を使った市場データ分析（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ / 注文永続化
- Paper Trading（テスト用）と Live（本番）を環境変数で切り替え
- 外部 API 呼び出し（OpenAI 等）は失敗時フォールバックを設ける（フェイルセーフ）

---

## 機能一覧

- モニタリング
  - CPU / メモリ / ディスク使用率の記録
  - Execution プロセス生存チェック（pid ファイル）
  - データ鮮度チェック（prices_daily ベース）
  - 注文滞留・約定異常検出、リスクログ記録
  - LINE によるアラート送信（AlertManager）
  - kill.flag による外部停止シグナル（KillSwitch）

- Execution（発注）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading では Mock）
  - OrderManager：注文の状態遷移管理（作成・送信・同期）
  - Reconciler：再起動時に OrderSent 等をブローカーと突合
  - RiskManager：ポートフォリオ制約チェック（設定で制御）

- ポートフォリオ構築
  - 候補選定（スコア順）、等重・スコア重み計算
  - セクター集中制限適用
  - レジーム乗数計算（bull/neutral/bear）
  - 株数（shares）算出（リスクベース / equal / score）

- 研究用
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（LLM 統合）
  - ニュース記事を LLM（gpt-4o-mini 等）でセンチメント化し ai_scores に格納
  - マクロニュース＋ETF MA200 乖離を組み合わせた市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB から稼働率・成功率・レイテンシ等の検証レポート出力
  - streamlit_dashboard: 監視ダッシュボード（read-only で monitoring DB を参照）

---

## セットアップ手順

前提:
- Python 3.10+（typing / match 等の表現があるため、少なくとも 3.9 以上を推奨）
- （任意）仮想環境（venv / pyenv 等）

1. リポジトリをクローン
   - git clone ... (本リポジトリ URL)

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要な主なパッケージ（抜粋）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

   例:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. data ディレクトリなどの作成
   - mkdir -p data

   デフォルト DB パス:
   - SQLite (monitoring): data/monitoring.db
   - DuckDB: data/kabusys.duckdb
   - Paper trading SQLite: data/paper_trading.db

   実行時に存在しなければ自動でテーブルは作成されます（init_monitoring_db）。

5. 環境変数設定
   - .env ファイルまたは環境変数として各種設定を行います（後述の「環境変数」セクション参照）。
   - 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方

以下は主要スクリプトの起動方法例です。プロダクション運用では systemd 等でプロセス化する想定です。

- 監視ループ（SystemMonitor のポーリング）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 概要:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
    - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用する（KABUSYS_ENV に依存しない）。
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil が必要）。

- ExecutionEngine（発注エンジン）起動
  - コマンド:
    - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
    - 起動時にプロセス優先度を "high" に設定します。
    - 実行前に必要な環境変数（KABU_API_PASSWORD 等）を確認してください。

- Paper Trading 検証レポート
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで SQLite DB パスを指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH > default）
  - 出力:
    - 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

- Streamlit ダッシュボード（監視）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 概要:
    - monitoring DB を read-only で開き、Overview / Positions / Orders / System の情報を表示します。

---

## 環境変数（主要）

主要な環境変数とデフォルト / 意味を抜粋します。

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須となる箇所あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（未設定時は送信をスキップ）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると .env 自動ロードを無効化

.env 例（抜粋）
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=xxxxx
- DUCKDB_PATH=data/kabusys.duckdb

---

## ディレクトリ構成（主要ファイルと説明）

以下はソースツリー（src/kabusys）内の主要モジュールとその簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）

- src/kabusys/config.py
  - 環境変数 / .env 読み込み、Settings クラスを提供

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading では MockBroker）

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル作成・永続化 API（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク、データ鮮度、pid チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン、ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - alert_manager.py: LINE Push による通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - reconciler.py: 起動時の注文・ポジション突合
  - order_manager.py: 注文状態遷移・送信の外向き API
  - （その他: broker_factory, execution_engine, order_repository 等 — 発注周りの実装群）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出と各種キャップ処理
  - risk_adjustment.py: セクター制限・レジーム乗数

- src/kabusys/research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector.py: ETF + マクロニュースで日次の市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

実際のファイル一覧（抜粋）
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/config.py
- src/kabusys/monitoring/monitoring_db.py
- src/kabusys/monitoring/system_monitor.py
- src/kabusys/monitoring/trade_monitor.py
- src/kabusys/monitoring/risk_monitor.py
- src/kabusys/monitoring/alert_manager.py
- src/kabusys/monitoring/streamlit_dashboard.py
- src/kabusys/execution/reconciler.py
- src/kabusys/execution/order_manager.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

（上記は主要モジュールの抜粋です。詳細はソースを参照してください。）

---

## 運用上の注意

- データ鮮度や PID 管理、kill.flag の扱いに注意してください。監視コンポーネントは運用監視を前提とした設計になっています。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に記録されます。検証目的で使用してください。
- OpenAI API 呼び出しは、キーの管理と呼び出し制限（課金）に注意してください。LLM 呼び出しは失敗時にフォールバック（スコア 0 等）しますが、API キー未設定時は例外になる関数もあります（明示的に api_key を渡すか OPENAI_API_KEY を設定してください）。
- データベースマイグレーション：monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加入れ）を行いますが、複雑なマイグレーションは手動対応が必要です。

---

もし README に追記してほしい点（例：運用手順の systemd ユニット例、より詳しい環境変数サンプル、依存関係の固定ファイルなど）があれば教えてください。README を用途に合わせて拡張します。