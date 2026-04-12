# KabuSys

日本株自動売買システムのコアライブラリ / ユーティリティ群です。  
このリポジトリには、注文実行エンジン、監視モジュール、ポートフォリオ構築ロジック、リサーチ / ファクター計算、ニュース NLP（OpenAI）連携などが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買を想定したモジュール群です。主な設計方針は以下です。

- 実行と監視は分離（ExecutionEngine / MonitoringEngine）
- Paper trading と Live を明確に分離（環境変数 `KABUSYS_ENV`）
- DuckDB を使った時系列・ファクター計算（research モジュール）
- SQLite を監視ログ / 注文履歴の永続化に使用
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / レジーム判定（AI モジュール）
- フェイルセーフ設計（API エラーはリトライ、部分失敗時に他データを保護など）

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine / OrderManager / Reconciler による注文発行と起動時リコンシリエーション
  - Broker クライアントを抽象化（paper_trading 時は MockBrokerClient を使用）
  - リスク管理（RiskManager の設定に基づく約定上限など）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセスPID、データ鮮度チェック
  - TradeMonitor: 滞留注文 / 約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限監視、kill.flag の発行
  - AlertManager: LINE push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only で monitoring DB を表示）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等金額 / スコア加重）、ポジションサイズ計算
  - セクター制限・レジーム乗数の適用
- Research（リサーチ / ファクター）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン、IC（スピアマン）計算、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集計 → ai_scores への書き込み
  - マクロニュース + ETF ma200 による市場レジーム判定（market_regime 書き込み）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
  - monitoring の起動スクリプト、execution の起動スクリプト

---

## セットアップ手順

以下は開発 / 実行に必要な最低限の手順です。環境やバージョンにより調整してください。

1. Python 環境の準備（推奨: venv）
   - python >= 3.10 を想定
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - ※実プロジェクトでは requirements.txt / poetry 等で管理してください。

3. ディレクトリ作成
   - data ディレクトリを作成（SQLite / DuckDB のデフォルトパスがここを指します）
     - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
   - 主要な環境変数（必須/推奨）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
     - KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — Paper trading の約定モード: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 例 .env（テンプレート）:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=yyyy
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=paper_trading
     - PAPER_FILL_MODE=instant

5. DB 初期化
   - Monitoring テーブル等は起動スクリプト内で `init_monitoring_db()` により冪等に作成されます。特別な初期 SQL は不要です。
   - DuckDB の prices_daily / raw_financials / raw_news 等テーブルはデータ投入が必要です（リサーチ機能を使う場合）。

注意:
- `KABUSYS_ENV=paper_trading` のとき、Execution は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離されます。
- Monitoring は環境にかかわらず本番の sqlite_path を使用する実装箇所が存在します（run_monitoring.py のコメント参照）。

---

## 使い方

以下は典型的な起動・実行方法です。

1. ExecutionEngine 起動（発注処理）
   - python -m kabusys.run_execution
   - 概要:
     - プロセス優先度を High に設定（可能であれば）
     - BrokerClientFactory を使って Broker クライアントを生成（paper_trading なら MockBrokerClient）
     - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動
   - Paper trading と Live の切り替えは `KABUSYS_ENV` で行います。

2. Monitoring 起動（監視ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
   - 監視用 SQLite の初期化は自動で行われます。

3. Streamlit ダッシュボード（監視表示, read-only）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - monitoring DB を read-only URI で開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 範囲を指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定できます。

5. AI（ニューススコア / レジーム）
   - ライブラリ関数として利用可能:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - DuckDB 接続を渡し、OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で供給します。
   - 注意: OpenAI の呼び出しはレートリミットや一時エラー対策（リトライ）を実装していますが、APIキー・コストに注意してください。

ログ / アラート:
- LINE 通知は `AlertManager` を使って送信します。`LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` を設定してください。
- KillSwitch は `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送信します（存在チェック、clear を実装）。

---

## ディレクトリ構成（主なファイル）

リポジトリ内の `src/kabusys` を基準にした簡易ツリー:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定の読み込み・検証
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py           — レジーム判定（ETF MA + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ / MonitoringDB
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 滞留注文 / 約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 管理
    - alert_manager.py             — LINE 通知
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - (order_manager.py, reconciler.py, order_repository.py, broker_factory など)
    - reconciler.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - (ブローカー抽象・実装)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py
    - stats.py
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度設定など

（注）execution 以下や data.pipeline 等はこの README では詳細を省略しています。各モジュールの docstring を参照してください。

---

## 追加の注意点 / 運用上のヒント

- Paper trading と Live のデータ隔離を厳格に守るため、`KABUSYS_ENV` を適切に設定してください。Paper では SQLite が別ファイルに切り替わります。
- Monitoring は run_monitoring.py 内のコメントの通り、本番 sqlite_path を使う箇所に注意が必要です（意図的な実装です）。
- OpenAI 経由の処理は API コストが発生します。ロギングやバッチサイズ、リトライ設定を運用に合わせて調整してください。
- process priority / CPU affinity の設定は OS 権限に依存します。権限不足で失敗しても警告を出してスキップする実装になっています。
- DB スキーマは init_monitoring_db() により冪等に作成・マイグレーション（簡易）されます。既存 DB のカラム追加処理などを含みます。

---

README は以上です。必要であれば以下の追記を行います:
- 依存パッケージの正確なバージョンリスト（requirements.txt / pyproject.toml）
- 実行フロー図やシーケンス図
- よくあるトラブルシューティング（OpenAI エラー、psutil の権限、DuckDB ファイルロック等）

どの情報を追加しましょうか？