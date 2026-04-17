# KabuSys — README

KabuSys は日本株向け自動売買／リサーチ基盤の一部を実装したコードベースです。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ／ファクター計算、LLM を使ったニュース NLP 等を含みます。

以下はこのコードベースの概要、機能、セットアップ手順、実行方法、主要ディレクトリ構成の説明です。

---

## プロジェクト概要

- 自動売買実行エンジン（ExecutionEngine）と、監視エンジン（MonitoringEngine）を提供します。
- Paper Trading（検証環境）と Live（本番）を分離して動作可能。Paper Trading は専用の SQLite DB に記録され、本番 DB と完全に分離されます。
- DuckDB を用いた時系列データ（prices_daily 等）からファクターや将来リターンを計算するリサーチモジュールを含みます。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント判定やマクロ判定（regime）機能を実装しています。
- 監視ログは SQLite（data/monitoring.db など）に保管し、Streamlit によるダッシュボードを起動できます。
- LINE Messaging API を使った通知（AlertManager）や、監視により重大なリスク発生時に Execution を停止する Kill Switch 機構を持ちます。

---

## 主な機能一覧

- Execution（発注・注文管理）
  - OrderManager：発注・注文状態管理の外向き API
  - Reconciler：起動時の自動リコンシリエーション（ブローカー照合）
  - ブローカーファクトリ（Mock を含む）で本番/紙トレード切替

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文／約定価格異常を検知
  - RiskMonitor：ドローダウン／ポジション上限監視とアラート記録
  - KillSwitch：重大なリスクで停止フラグ（data/kill.flag）を作成
  - AlertManager：LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（data/monitoring.db を参照、読み取り専用で起動）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア加重配分、セクターキャップ適用、ポジションサイジング（単元丸め、aggregate cap 等）

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（LLM 統合）
  - news_nlp: ニュース記事を集約して LLM でセンチメントスコアを算出し ai_scores テーブルへ書込み
  - regime_detector: ETF の MA200 乖離とマクロセンチメントを合成して market_regime を決定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（kabusys.monitoring.streamlit_dashboard）

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.10+ を推奨します。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 明示的に必要な主要パッケージ（例）:
     - pip install duckdb psutil requests openai streamlit

   （実際の requirements.txt がない場合はプロジェクトで使われているパッケージを適宜インストールしてください）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定（.env を作成するか、シェルでエクスポート）
   - 推奨: リポジトリルートに .env を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

必須（実行する機能により異なる）環境変数例:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須プロパティ参照）
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 環境（development / paper_trading / live） デフォルト: development

任意／デフォルト有りの例:
- SQLITE_PATH — 監視 DB path（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB path（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）（デフォルト: instant）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）

例 .env（テンプレート）
- JQUANTS_REFRESH_TOKEN=YOUR_TOKEN
- KABU_API_PASSWORD=YOUR_PASSWORD
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=development
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=

注意:
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する設計です（監視は本番 DB を参照する想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要スクリプト）

プロジェクトルートから実行してください（src がパッケージのルートになる想定）。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 停止方法: data/stop_requested.flag を作成するとポーリングループが検知して終了します

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV により実行モードが変わります:
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録
    - live / development: 本番ブローカークライアント等（設定に依存）
  - 実行中に data/stop_requested.flag を作成するとエンジン停止処理が開始されます
  - Execution は起動時に data/stop_requested.flag が既に存在する場合は起動しません

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
  - 出力: 指定期間の稼働率・注文成功率・レイテンシ等のサマリと Pass/Fail 判定

- AI / リサーチ関数（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI を使って ai_scores を更新
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
  - 各研究関数: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等

---

## 停止 / フラグについて

- data/stop_requested.flag
  - run_execution/run_monitoring が参照する「停止要求」フラグ。存在を検知すると起動しない／実行中なら停止処理を行います。
- data/kill.flag
  - KillSwitch が重大リスク発生時に書き込むフラグ（Execution を停止させるため）。KillSwitch.evaluate() によって生成されます。
- data/execution.pid
  - ExecutionEngine が自身の PID を書き出すファイル。SystemMonitor はこの PID を参照してプロセス生存を判定します。

Settings により KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に kill.flag をクリアする挙動になります。

---

## 主要ディレクトリ／ファイル構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数／設定管理（.env 自動読み込み機能含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (※実装のある場合)
  - broker_factory.py, broker_api.py, order_record.py 等 — 発注・ブローカー関連

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化ラッパ
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル生成
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 複数 Monitor の束ね（run_once/run ）
  - streamlit_dashboard.py — Streamlit ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・制限・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum/Volatility/Value などのファクター
  - feature_exploration.py — 将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュース集約 → OpenAI でスコアリング → ai_scores へ書込み
  - regime_detector.py — MA200 とマクロセンチメントを合成したレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ

- data/
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB のパス）
  - stop_requested.flag / kill.flag / execution.pid 等の制御ファイル

簡易ツリー（抜粋）
```
src/kabusys/
├─ run_execution.py
├─ run_monitoring.py
├─ config.py
├─ execution/
├─ monitoring/
├─ portfolio/
├─ research/
├─ ai/
└─ tools/
data/
```

---

## 実行上の注意点 / 運用上のヒント

- Monitoring は本番 DB（Settings.sqlite_path）を参照するため、監視を開発環境で動かすと本番モニタ情報に書き込む可能性があります。用途に応じて .env でパスを切り替えてください。
- process priority の設定（psutil を使用）や CPU affinity 設定は権限が必要な場合があります。権限不足時は警告が出て処理を続行します。
- OpenAI API を使用する箇所は API キーが必須です。API 呼び出しで一時エラー（429 / タイムアウト / 5xx）は自動リトライを行いますが、リトライ上限を越えると該当部分はフェイルセーフ（スコアを 0.0 にフォールバックやスキップ）化します。
- Paper Trading 用 DB は PAPER_TRADING_SQLITE_PATH で明示的に分離することを強く推奨します（デフォルト: data/paper_trading.db）。
- monitoring_db.init_monitoring_db() は冪等（既存テーブルへの列追加マイグレーション処理を含む）なので、安全に複数回実行できます。

---

## 贡献 / 拡張のヒント

- broker 実装（ライブ接続）や mock broker の拡充
- 単元株数の個別対応（stocks マスタに lot_size を持たせるなど）
- AlertManager に複数通知チャネル（Slack, Email）を追加
- DuckDB のスキーマ拡張・ETL パイプライン（prices_daily 等）を整備
- テスト用のユニットテスト・モック実装の追加（OpenAI 呼び出し等を patch 可能に設計済）

---

上記を参考にローカルで起動・検証を行ってください。必要なら .env.example のテンプレート作成や requirements.txt の整備、起動スクリプトの systemd / supervisor 用ユニット例も作成できます。希望があれば追加で記載します。