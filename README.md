# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
この README はプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
主な目的は以下：

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（System / Trade / Risk の監視、アラート、kill switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約等）
- 研究（ファクター計算・特徴量探索・将来リターンやIC計算）
- AI によるニュースセンチメント評価（OpenAI を利用したニュース NLP）
- Paper Trading 環境（本番 DB と分離して検証可能）
- モニタリング用ダッシュボード（streamlit）

設計方針として、DB（SQLite / DuckDB）を用いたデータ永続化、外部 API 呼び出し（kabu API, J-Quants, OpenAI）を抽象化、監視・リスクロジックはフェイルセーフになるよう実装されています。

---

## 機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（実運用 / モックの切替）
  - Reconciler による再起動後の自動同期
  - OrderManager / OrderRepository による注文管理

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/実行プロセス/データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出と永続化
  - KillSwitch: 条件に応じて kill.flag を作成し ExecutionEngine に停止シグナルを送信
  - AlertManager: LINE Push を用いた通知（クールダウン管理）
  - MonitoringEngine: 各モニタを束ねてポーリング（テスト用 run_once あり）
  - streamlit ダッシュボード（監視情報の可視化）

- AI / Research
  - news_nlp: OpenAI を利用したニュースセンチメント（ai_scores テーブルへ書込）
  - regime_detector: ETF MA とマクロニュースを合成して市場レジーム判定
  - research.factor_research / feature_exploration: ファクター計算・将来リターン・IC・統計サマリ

- Portfolio
  - portfolio_builder: 候補選定、等配分・スコア加重配分
  - position_sizing: 株数算出（risk-based / equal / score）、単元丸め、aggregate cap
  - risk_adjustment: セクター上限適用、レジーム乗数

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）

---

## 前提・依存関係

主要な Python パッケージ（例）:

- python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード用)
- sqlite3（標準ライブラリ）

（実際のバージョンや追加パッケージは環境に応じて調整してください）

例インストール（仮の requirements）:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

- KABUSYS_ENV: environment タイプ（development / paper_trading / live）  
  - paper_trading の場合、Execution はモックブローカーを使い data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- PAPER_FILL_MODE: paper trading の注文成立モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用 flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（空なら送信せずログのみ）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 で無効）

config モジュール（kabusys.config）はプロジェクトルートの `.env` / `.env.local` を自動でロードします（必要に応じて無効化可能）。

---

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローンし、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成する（例は下記）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（実行モジュールで必要に応じて）
   - OpenAI を使う場合は OPENAI_API_KEY を設定

例 .env（最小）:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成（必要なら）
   - mkdir -p data

5. 初期 DB 作成
   - 実行スクリプト（run_monitoring / run_execution）を起動すると init_monitoring_db() が自動でテーブルを作成します。

---

## 使い方（主要スクリプト）

- 監視ループを起動（SystemMonitor 単体の polling を開始）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない実装）

- Execution エンジン起動（発注実行プロセス）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に data/stop_requested.flag を作ると安全停止する

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

- Streamlit ダッシュボード（監視データ）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 DB（読み取り専用）を開いてポートフォリオ・ポジション・ログ・最新システム状態を表示

- AI / レジーム判定 / ニューススコアリング
  - ライブラリ関数として利用:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - conn は duckdb.connect(...) で作った接続を渡す
  - OPENAI_API_KEY が必須（引数でも与え可）

- プロセス停止・kill flag
  - KillSwitch は条件を満たすと data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag を検出して停止します。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring / run_execution の外部停止トリガーとして使われます。

---

## 実行シーケンスの例（運用想定）

1. ExecutionEngine を起動（注文・ポジションを実行）
   - python -m kabusys.run_execution
2. Monitoring を起動（監視とアラート・kill switch）
   - python -m kabusys.run_monitoring
3. 定期的に news_nlp / regime_detector をスケジュールして ai_scores / market_regime を更新
4. 必要時に streamlit ダッシュボードで状態確認
5. 運用停止時は data/stop_requested.flag を作成（または kill.flag による自動停止）

---

## ディレクトリ構成（主なファイルと役割）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env ロードおよび Settings クラス
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite 監視ログの永続化（スキーマ定義・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知ラッパー
  - monitoring_engine.py — 各 Monitor の統合ポーリング
  - streamlit_dashboard.py — streamlit ダッシュボード
- execution/
  - order_manager.py — 注文状態遷移と発注ロジック
  - reconciler.py — 起動時の状態同期（ブローカーとの突合）
  - （その他：broker_factory, order_repository 等はコードベースに含まれる想定）
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数算出、リスク・単元丸め
  - risk_adjustment.py — セクター制約、レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算
  - feature_exploration.py — 将来リターン計算・IC計算・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
- data/（実行時生成）
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB ファイル）
  - execution.pid, stop_requested.flag, kill.flag などの制御ファイル

備考: 実際のリポジトリではさらに `data`, `strategy`, `execution` などのディレクトリやファイルが存在する可能性がありますが、本 README は提供されたコードスニペットに基づいて要点をまとめています。

---

## 開発・デバッグのヒント

- config.py はプロジェクトルートの .env を自動ロードします。テスト時に自動ロードを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SystemMonitor / ExecutionEngine は PID ファイルや flag ファイルで外部から制御できます（stop_requested.flag / kill.flag）。
- Monitoring の初期化（テーブル作成）は init_monitoring_db() により冪等に行われます。DB マイグレーション（既存カラム追加）も起動時に対応しています。
- psutil を用いたプロセス優先度設定は権限に依存するため、権限不足時は警告が出て処理は継続します。
- OpenAI 関係はレスポンスパース失敗・API エラーに対してフェイルセーフ（0.0 やスキップ）で扱われます。API キー未設定は例外を投げます。

---

必要であれば、この README をベースに「運用手順書」「デプロイ手順」「.env.example」や「requirements.txt」等を別途作成します。どの追加ドキュメントが欲しいか教えてください。