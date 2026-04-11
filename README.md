# KabuSys

日本株向けの自動売買・監視システム（ライブラリ / 実行スクリプト群）

本リポジトリは、シグナルに基づく発注エンジン、監視/アラート基盤、ファクター計算・リサーチユーティリティ、LLM（OpenAI）を使ったニュースセンチメント評価などを含む自動売買システムのコア実装です。

---

## プロジェクト概要

- 発注エンジン（ExecutionEngine）
  - シグナル取得 → Gate チェック（リスク） → 発注 → プッシュ（broker）ドレインのワークフローを実装
  - 再起動時のリコンシリエーション（Reconciler）による自動復旧を実装
  - paper_trading 環境用にモックブローカーを利用し、本番 DB と分離可能
- 監視（Monitoring）
  - システムリソース・データ鮮度・注文滞留・約定異常等の検知とログ保存
  - kill.flag による外部停止シグナル、LINE への通知（AlertManager）
  - Streamlit ダッシュボードで監視情報を可視化
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み付け（等加重／スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ（Research）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）や特徴量探索（IC / forward returns）
- AI（LLM）連携
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores に保存
  - マクロニュース + ETF の MA を用いた市場レジーム判定

---

## 主な機能一覧

- Execution
  - OrderManager（発注、同期、キャンセル）
  - ExecutionEngine（セッション運用・push ドレイン）
  - Reconciler（OrderSent 等の復旧、ポジション差分検出）
  - RiskManager（レート制限、回路遮断、ポートフォリオ利用制限 等）※設定で動作
- Monitoring
  - SystemMonitor（CPU/MEM/DISK、プロセス PID、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン監視、ポジション上限監視）
  - KillSwitch（kill.flag 書き込み / クリア）
  - AlertManager（LINE Push）
  - Streamlit ダッシュボード（data/monitoring.db を read-only で表示）
- Portfolio
  - 候補選定・重み計算・株数決定（lots/aggregate cap の考慮）
- Research
  - calc_momentum / calc_volatility / calc_value
  - forward returns / IC / 統計サマリー
- AI
  - news_nlp.score_news（OpenAI によるニュースセンチメント）
  - regime_detector.score_regime（ETF MA とマクロセンチメントを合成して regime 判定）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 構文を使用）
- SQLite は標準で利用可能
- duckdb, psutil, openai, requests, streamlit などの外部パッケージが必要

例: 仮想環境作成と依存インストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

3. 開発モードでパッケージを使いやすくする（任意）
   - (repo ルートにて) PYTHONPATH を通すか、パッケージ化してインストール:
     - pip install -e .

.env 自動読み込み
- config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（代表例）
- JQUANTS_REFRESH_TOKEN — J-Quants API（使用箇所がある場合）
- KABU_API_PASSWORD — kabuステーション API
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境: development | paper_trading | live

主要ファイル / データベースのデフォルトパス
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag

（必要なら `data/` を作成して DB ファイルを用意してください。MonitoringDB は起動時にテーブルを作成します。）

---

## 簡単な使い方

実行方法の前提: ソースをインポート可能な状態にする（`pip install -e .` または `PYTHONPATH=src`）。

1) 監視プロセスの起動（Monitoring）
- 環境変数でポーリング間隔を変更可能:
  - MONITOR_POLL_INTERVAL=30  # 秒（1以上、無効値はデフォルト 60 秒にフォールバック）
- 実行コマンド例:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - または (パッケージインストール済み) python -m kabusys.run_monitoring
- 補足:
  - run_monitoring は Settings を読んでプロセス優先度を high に設定します（set_process_priority）。
  - 監視は monitoring DB（settings.sqlite_path）を使用します。KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

2) 発注エンジンの起動（ExecutionEngine）
- paper trading を使う場合:
  - export KABUSYS_ENV=paper_trading
  - Paper trading 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
  - PAPER_FILL_MODE を設定可能: instant | partial | never | reject（デフォルト: instant）
- 実行コマンド例:
  - PYTHONPATH=src python -m kabusys.run_execution
- 補足:
  - 起動時にプロセス優先度を high に設定します。
  - 実行中は kill.flag を検知すると安全に停止します（kill.flag を書くのは Monitoring 側の KillSwitch）。

3) Streamlit ダッシュボード（監視データの可視化）
- 実行コマンド例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI を使って DB を開くため、MonitoringEngine が書き込んでいる同ファイルを安全に表示できます。

4) AI（OpenAI）を使った処理
- OpenAI API を使う機能:
  - kabusys.ai.score_news(target_date, conn) — ニュースのセンチメントを ai_scores へ書き込む
  - kabusys.ai.regime_detector.score_regime(target_date, conn) — レジーム判定と market_regime への書込
- 実行には OPENAI_API_KEY が必要:
  - export OPENAI_API_KEY="sk-..."

---

## 重要な挙動・注意点

- .env 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされません。
- Monitoring の DB は環境に関わらず production sqlite_path を使います（監視は常に本番 DB を参照する想定）。
- Execution は KABUSYS_ENV=paper_trading のとき専用 DB（paper_sqlite_path）を使用します。
- プロセス優先度/CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil 権限により適用できない場合は警告を出します。
- kill.flag
  - KillSwitch が kill.flag を作成すると ExecutionEngine は安全に停止します。kill.flag は clear() で削除できます。
  - ExecutionEngine 起動時に kill_flag_clear_on_start が有効であればフラグをクリアする設定もあります（Settings）。
- Paper trading
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。
- OpenAI API の呼び出しはリトライ/バックオフを実装していますが、API キー未設定時は例外を投げます。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py — パッケージのバージョン/エクスポート
- config.py — 環境変数/.env のロードと Settings クラス
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロセンチメントで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による永続化レイヤ（テーブル作成・CRUD）
  - system_monitor.py — CPU/MEM/DISK、PID、データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - execution_engine.py — ExecutionEngine 実装（signal loop / push drain）
  - order_manager.py — 発注フロー（create/send/sync/cancel）
  - reconciler.py — 再起動時のリコンシリエーション
  - その他: broker_factory, order_repository, order_record, risk_manager（参照あり）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 計算
  - feature_exploration.py — forward returns / IC / 統計サマリー
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/ (実行時に利用するディレクトリ。
  - data/kabusys.duckdb  (DuckDB)
  - data/monitoring.db   (SQLite: Monitoring)
  - data/paper_trading.db (SQLite: Paper trading 用)

（注）上記は主要ファイルの抜粋です。細かい実装は各ファイルの docstring を参照してください。

---

## 開発・デバッグのヒント

- ログレベルは環境変数 LOG_LEVEL で設定可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- .env.example を参考に .env を作成して必要なキーを設定してください。
- テスト実行や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードを無効化できます。
- DuckDB/SQLite のクエリはそれぞれのモジュールで直接 SQL を実行しているため、DB スキーマ変更時はマイグレーションに注意してください（monitoring_db.init_monitoring_db は一部カラム追加入力の対応あり）。
- OpenAI 呼び出し部分はテスト時にモック化できるよう設計されています（内部の _call_openai_api を patch するなど）。

---

README はここまでです。必要であれば以下を提供します：
- .env.example（サンプル環境変数ファイル）
- requirements.txt の草案
- よく使う実行コマンドスニペット

必要があれば追加で作成します。