# KabuSys — README

このリポジトリは日本株向け自動売買システム「KabuSys」の一部実装です。  
本READMEはコードベース（src/kabusys 以下）を対象に、プロジェクト概要、機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたドキュメントです。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成された、日本株の自動売買・研究・監視システムです。

- 実行エンジン（ExecutionEngine）による発注・リスク管理・リコンシリエーション
- 監視コンポーネント（Monitoring）によるシステム状態・注文状況・リスクの定期チェックとアラート送信
- ポートフォリオ構築（候補選択・重み計算・ポジションサイズ算出・リスク調整）
- リサーチ（ファクター計算、特徴量探索）
- AI（ニュースセンチメント／レジーム判定）モジュール（OpenAI を利用）
- 開発・検証用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード 等）

設計上のポイント：
- 環境変数 / .env を介した設定管理（src/kabusys/config.py）
- DuckDB を使ったリサーチデータ（prices_daily 等）
- SQLite を監視ログ・注文ログ保存に使用
- Paper Trading (KABUSYS_ENV=paper_trading) は本番 DB と分離（data/paper_trading.db）

---

## 主な機能一覧

- 監視（Monitoring）
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution プロセス生存確認（pid ファイル監視）
  - データ鮮度チェック（prices_daily の最終日付）
  - 注文滞留検出、約定時価格異常検出
  - ドローダウン / ポジション上限の監視と kill.flag による停止シグナル発行
  - LINE へのアラート（AlertManager）

- 実行（Execution）
  - ブローカークライアント抽象化（Mock と実ブローカー切替）
  - OrderManager による注文ステート管理、送信、同期
  - Reconciler による再起動後の自動復旧・ポジション突合

- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア加重配分
  - セクター集中制限の適用
  - ポジションサイズ計算（risk-based / equal / score）

- リサーチ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI（ai）
  - ニュースのセンチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA 乖離による市場レジーム判定（LLM を利用）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## 前提条件（依存）

（主要なもの）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- その他（標準ライブラリ: sqlite3 等）

インストール例（仮想環境使用を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／取得し、Python 仮想環境を作成・有効化する。

2. 依存パッケージをインストールする（上記参照）。

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くことで自動的に読み込まれます（src/kabusys/config.py）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI モジュール利用時）
   - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
   - PAPER_TRADING_SQLITE_PATH（paper_trading の場合の SQLite パス、デフォルト: data/paper_trading.db）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE アラート）
   - PAPER_FILL_MODE（paper_trading の成行約定挙動: "instant" | "partial" | "never" | "reject"）

5. 必要な DB 初期化
   - 監視 DB のテーブルは run_monitoring や run_execution 内で `init_monitoring_db()` により冪等に作成されます。
   - DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）は別途データ投入処理が必要です（本リポジトリ外で準備）。

---

## 実行方法（使い方）

※ 以下はプロジェクトルートで実行する想定です。

- 監視ループを起動（SystemMonitor 単体）
```
python -m kabusys.run_monitoring
```
- 説明
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）を使用。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使います。
  - プロセス優先度を "high" に設定しようとします（プラットフォームに依存し権限が無ければスキップ）。

- 実行エンジン（ExecutionEngine）を起動
```
python -m kabusys.run_execution
```
- 説明
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、`data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
  - Execution の起動時に監視用テーブルが存在することを保証します（冪等）。

- Streamlit ダッシュボードを起動（監視 DB を参照）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パス指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- 説明
  - 統計・指標を集計して PASS/FAIL 判定を行います。
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。

- AI モジュールの利用例（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

---

## 主要環境設定（要点）

- KABUSYS_ENV
  - development / paper_trading / live
  - paper_trading の場合、発注はモック・DB は data/paper_trading.db に分離されます。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。0 以下や不正値はデフォルト（60 秒）にフォールバック。

- PID / kill flag
  - 起動・停止制御に PID ファイル / kill.flag を使用（Settings.pid_file_path / kill_flag_path）。
  - KillSwitch はリスク条件で kill.flag を書き込み、ExecutionEngine 側で停止を検出することを期待する設計。

- PAPER_FILL_MODE（paper_trading）
  - instant / partial / never / reject（不正値は例外）

---

## ディレクトリ構成（主要ファイルの役割）

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロードや検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル初期化 / CRUD）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE Push によるアラート送信
  - streamlit_dashboard.py — Streamlit ベースの監視 UI

- src/kabusys/execution/
  - reconciler.py — 起動時の注文／ポジション突合・復旧
  - order_manager.py — 注文ステートマシン外向け API（作成・送信）
  - その他（execution/*.py） — ブローカ関連／注文リポジトリ等（省略分が存在）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・等配分/スコア加重
  - position_sizing.py — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDBベース）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA 乖離 + マクロニュースで市場レジーム判定（LLM 使用）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

- data/
  - data/kabusys.duckdb（デフォルト DUCKDB_PATH）
  - data/monitoring.db（監視 SQLite）
  - data/paper_trading.db（paper_trading 用 SQLite）

---

## 開発メモ / 注意点

- .env のパースは独自実装で、シングル/ダブルクォート、export プレフィックス、コメントの扱いに対応しています（config.py）。
- MonitoringDB.init_monitoring_db() は冪等であり、既存 DB に対する簡易マイグレーション（カラム追加）も行います。
- AI 系機能は OpenAI の API を利用するため、API 利用制約やレートリミット、レスポンス検証に注意しています。API キーは環境変数 OPENAI_API_KEY を設定してください。
- psutil を使ったプロセス優先度/CPU affinity 設定は OS に依存します。権限不足や未サポート環境では警告を出してスキップします。
- DuckDB 側のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）は外部データ準備が必要です。
- Paper Trading モードはブローカー操作を分離するため、実稼働データと混ざらないよう設計されていますが、本番運用前には十分な検証を行ってください。

---

## 付録：よく使うコマンドまとめ

- 依存インストール
  - pip install duckdb psutil requests openai streamlit

- 監視起動
  - python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README をさらに拡張して、実行エンジンの設定詳細、ブローカープラグインの実装ガイド、DuckDB のスキーマ定義サンプルなども追加できます。希望があれば教えてください。