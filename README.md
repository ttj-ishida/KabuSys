# KabuSys

日本株向けの自動売買・リサーチ基盤（部分実装）。ポートフォリオ構築、ポジションサイズ計算、監視（Monitoring）、実行エンジン（Execution）、リサーチ / ファクター計算、ニュースNLP（OpenAI）等のユーティリティ群を含みます。

以下はこのリポジトリの概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買システムのコンポーネント群です。主な目的は次のとおりです。

- 戦略からのシグナルを発注に繋げる実行基盤（ExecutionEngine, OrderManager 等）
- ポートフォリオ構築・配分計算（選定・重み付け・ポジションサイズ計算）
- 監視・アラート（System/Trade/Risk の定期チェック、kill flag、LINE 通知）
- DuckDB を用いたファクタ計算・リサーチ（Momentum, Volatility, Value 等）
- OpenAI を用いたニュースセンチメント評価（news_nlp）と市場レジーム判定
- Paper Trading 用の分離された DB と検証用ツール

設計方針としては、安全側のフォールバック（API失敗時の継続処理）、ルックアヘッドバイアスの排除（内部で date.today() を直接参照しない等）、DB マイグレーションの冪等性を重視しています。

---

## 機能一覧

- 設定管理（.env / 環境変数読み込み、Settings クラス）
- 実行プロセス起動スクリプト
  - run_execution.py：ExecutionEngine 起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 監視（monitoring）
  - SystemMonitor: CPU/Memory/Disk、Execution プロセス存否、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringDB: SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル
  - AlertManager: LINE Push による通知（クールダウンあり）
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- 実行（execution）
  - OrderManager / OrderRepository / Reconciler 等（再起動時の同期リコンシリエーションなど）
- ポートフォリオ（portfolio）
  - 銘柄選定、等配分 / スコア配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- リサーチ（research）
  - ファクター計算（mom, volatility, value）: DuckDB を用いた SQL ベース
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- AI（ai）
  - news_nlp: OpenAI を使った銘柄別センチメントスコア算出（バッチ・リトライ・応答検証）
  - regime_detector: ETF MA とマクロセンチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等の検証レポート生成

---

## 要件

- Python 3.10+
- 推奨パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリとして同梱）
- （任意）LINE Messaging API のトークン（AlertManager 使用時）

必要パッケージはプロジェクト側で requirements.txt がある場合はそれを使用してください。無ければ pip で個別にインストールします。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに入る。

2. 仮想環境を作成して依存をインストール（上記参照）。

3. 環境変数を設定する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（既存 OS 環境変数を上書きしない）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — （必須、Settings.jquants_refresh_token）
     - KABU_API_PASSWORD — （必須、kabuステーション API 用）
   - 代表的なオプション変数（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
     - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のマッチ挙動）
     - LOG_LEVEL: DEBUG|INFO|... 等
     - PID_FILE_PATH / KILL_FLAG_PATH 等
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

   サンプル `.env`（最小）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. data ディレクトリ作成
```bash
mkdir -p data
```
起動スクリプトが初回実行時に必要なテーブルを自動作成します（init_monitoring_db が呼ばれます）。

---

## 使い方

- 監視ループを起動（SystemMonitor 単体）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を上書き:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 実行エンジンを起動（本番/ペーパートレード）
```bash
# 本番（env=live にする場合）
KABUSYS_ENV=live python -m kabusys.run_execution

# Paper Trading（MockBrokerClient を使用し、data/paper_trading.db に記録）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Paper Trading 検証レポート生成
```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パス指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- Streamlit 監視ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- AI（ニューススコア・レジーム判定）のプログラム呼び出し
  - プログラム内から `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼ぶと ai_scores テーブルに書き込みます。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` で market_regime テーブルへ書き込みます。
  - どちらも API キーは引数または環境変数 `OPENAI_API_KEY` による解決を行います。

注意:
- run_monitoring は監視用の sqlite DB（Settings.sqlite_path）を常に使用します（環境にかかわらず本番DBパスを参照）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合に別 DB (`PAPER_TRADING_SQLITE_PATH`) を使用し、本番 DBと完全分離します。

---

## 主要設定 / 環境変数（まとめ）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要・よく使う:
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能）
  - KABUSYS_ENV — development / paper_trading / live（既定: development）
  - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（既定: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（既定: data/paper_trading.db）
  - PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（既定: 60）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager 用
  - PID_FILE_PATH / KILL_FLAG_PATH — 実行プロセス管理用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 で自動 .env ロードを無効化

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要ファイル／モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py : パッケージ定義
  - config.py : 環境変数の読み込み・Settings クラス（.env 自動ロード機能含む）
  - run_monitoring.py : SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py : ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py : Paper Trading 検証レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py : ニュースを OpenAI でスコア化し ai_scores に書き込む
    - regime_detector.py : マクロ + ETF MA で市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py : SQLite スキーマ初期化と MonitoringDB クラス
    - system_monitor.py : CPU/Memory/Disk・データ鮮度・プロセスチェック
    - trade_monitor.py : 注文滞留・約定異常検出
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag による停止シグナル
    - alert_manager.py : LINE push
    - monitoring_engine.py : 各 Monitor を束ねる（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py : Streamlit で監視ダッシュボード起動
  - execution/
    - order_manager.py : 発注ロジック（状態遷移・send_order フロー）
    - reconciler.py : 再起動時の注文・ポジションの突合
    - （その他：broker_factory, order_repository 等が参照される）
  - portfolio/
    - __init__.py
    - portfolio_builder.py : 候補選定・重み計算
    - risk_adjustment.py : セクターキャップ・レジーム乗数
    - position_sizing.py : 株数算出・丸め・aggregate cap
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value ファクター計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - utils/
    - __init__.py
    - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

（注）コード中に参照される `kabusys.data` パッケージ等はこの抜粋に含まれていませんが、DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）を提供するモジュールがプロジェクト内に存在する想定です。

---

## 運用時の注意点

- Paper Trading は本番 DB と分離しているため、`KABUSYS_ENV=paper_trading` を設定して動作させてください。
- OpenAI 呼び出しや外部 API 呼び出しはネットワーク障害・制限を考慮してリトライやフォールバック処理が組まれていますが、API キーやレート制限には注意してください。
- run_monitoring/run_execution はそれぞれプロセス優先度を上げようとします（psutil を使用）。必要な権限がないと警告が出ますが、処理は継続します。
- kill.flag の存在は ExecutionEngine に停止シグナルを送る仕組みです。テスト時や起動時のクリア動作に注意してください（Settings.kill_flag_clear_on_start）。

---

README に記載されていない詳細な使い方・設計文書（PortfolioConstruction.md / StrategyModel.md 等）がプロジェクト内にある想定です。個別機能の利用方法や API の詳細が必要であれば、該当モジュールに合わせたドキュメント生成を行います。