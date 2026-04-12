# KabuSys

日本株自動売買システムの一部を抜粋したコードベース用 README（日本語）。

このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、研究、AI バックエンド（ニュースセンチメント／レジーム判定）を含むモジュール群を提供します。ここではプロジェクトの概要、主要機能、セットアップ、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームを想定したライブラリ／アプリ群です。本コードベースは次の主要領域で構成されています。

- execution: 発注管理、ブローカークライアント抽象、再コンシリエーション
- monitoring: システム・注文・リスク監視、アラート送信（LINE）、監視ダッシュボード（Streamlit）
- portfolio: 銘柄選定、重み算出、ポジションサイズ計算、リスク調整
- research: ファクター計算、特徴量探索（DuckDB を利用）
- ai: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定
- tools: ペーパートレード検証レポート等のユーティリティスクリプト
- utils / config: 環境設定読み込み、プロセス優先度設定などユーティリティ

設計方針の例:
- DuckDB / SQLite をデータ永続化に使用
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- 可能な限り副作用を抑え、フェイルセーフ（API障害時のフォールバック）を重視

---

## 機能一覧

- 発注ワークフロー（OrderManager, OrderRepository, ExecutionEngine の組合せ）
- 起動時の再コンシリエーション（Reconciler）
- リスク管理（RiskManager, RiskMonitor）
- システム監視（CPU / Memory / Disk / プロセス生存 / データ鮮度のチェック）
- 監視ログ永続化（SQLite: monitoring_db）
- アラート送信（LINE Messaging API 経由、cooldown 管理）
- Kill Switch（条件達成時に data/kill.flag を書き込み ExecutionEngine を停止）
- Streamlit ベースの監視ダッシュボード（read-only DB 表示）
- Paper Trading 検証レポート生成ツール（集計・PASS/FAIL 判定）
- ニュースセンチメント（OpenAI）による ai_scores の生成
- 市場レジーム判定（MA200 と LLM センチメントの合成）
- ポートフォリオ構築補助（候補選定・重み付け・ポジションサイズ計算・セクター上限）

---

## 必要条件 (推奨)

- Python 3.9+
- システム依存パッケージ（プラットフォームにより差異あり）
- 主な Python ライブラリ:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit (監視ダッシュボードを使う場合)

（実際の requirements.txt がない場合はプロジェクトに合わせて追加してください）

例:
pip install duckdb openai psutil requests streamlit

---

## セットアップ手順（ローカル開発用）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai psutil requests streamlit

3. プロジェクトルートに `.env` を置く（自動読み込みが有効な場合）
   - 自動ロードは .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例:
     - KABUSYS_ENV=development | paper_trading | live
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - JQUANTS_REFRESH_TOKEN=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant | partial | never | reject

4. データディレクトリを作成
   - mkdir -p data

5. 初期 DB 作成は各起動スクリプトが行います（init_monitoring_db は冪等）。

---

## 使い方（主要スクリプト）

- Monitoring（監視ループ）起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視ログは常に production DB を参照）。

- Execution（発注エンジン）起動
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 実行:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先します。

- 監視ダッシュボード（Streamlit）
  - 起動方法:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開きます（MonitoringEngine が DB を生成・更新していることが前提）。

---

## 主要な環境設定（要点）

- KABUSYS_ENV
  - development / paper_trading / live のいずれか
  - Settings クラスで厳密に検証されます

- PAPER_FILL_MODE (paper_trading 時)
  - instant / partial / never / reject のいずれか
  - 無効値は ValueError を送出

- DB パス:
  - SQLITE_PATH: data/monitoring.db（監視 DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - DUCKDB_PATH: data/kabusys.duckdb（時系列・ファクターなどの分析用）

- PID / Kill Flag:
  - PID_FILE_PATH（例: data/execution.pid）: ExecutionEngine が生存を示す PID を書く
  - KILL_FLAG_PATH（例: data/kill.flag）: KillSwitch が書くことで ExecutionEngine に停止シグナルを送る

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env / .env.local を読み込みます
  - OS 環境変数が優先され、.env.local は上書きモードです
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます

---

## 注意点 / 実運用のヒント

- Paper Trading は本番 DB と分離されるため、テスト実行で本番データを汚染しません。
- OpenAI を使う機能（news_nlp, regime_detector）を利用するには OPENAI_API_KEY が必要です。API 呼び出しはエラー時にフォールバックするよう設計されています（失敗時はスコアを無効扱いまたは 0 にフォールバック）。
- Process priority / CPU affinity の設定はプラットフォーム差異を吸収しますが、権限不足で設定に失敗することがあります（警告ログのみ）。
- Monitoring は監視データの永続化、アラート送信、kill.flag 書き込みなどを行います。kill.flag を書くと ExecutionEngine は停止する設計です。必要に応じて KILL_FLAG_CLEAR_ON_START を設定して起動時にフラグをクリアしてください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py (パッケージ初期化)
  - config.py — 環境変数読み込み・Settings 定義
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — システム／データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - alert_manager.py — LINE 通知ロジック
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注ステートマシンの外向 API
    - reconciler.py — 起動時リコンシリエーション
    - (その他発注関連の実装ファイル: broker, engine, repository 等)
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 追加情報 / 今後の拡張案

- ブローカー接続（kabuステーション等）の実装とテストハーネス
- 銘柄ごとの lot_size 管理（現在は一律 100）
- マスターデータの補完処理（価格欠損時のフォールバック）
- CI / テストスイート、requirements.txt の整備

---

以上がこのコードベースの README です。必要であれば .env.example のテンプレートや、実行時のログ出力例、よくあるトラブルシュート（OpenAI レート制限、SQLite ロック、psutil 権限エラーなど）を追記できます。どの情報を優先して追加しましょうか？