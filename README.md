# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリには、発注実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を用いたニュースセンチメント評価などのモジュール群が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）
  - ブローカークライアント経由で注文を送信、注文状態管理、リスク制御、再起動時のリコンシリエーション等を行います。
  - 本番（live）とペーパートレード（paper_trading）を切り替え可能。ペーパートレードでは MockBroker を用い、データは本番 DB と分離して `data/paper_trading.db` に記録されます。
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）、注文滞留、約定価格異常、ドローダウン等をポーリングして SQLite に保存します。
  - アラート送信（LINE push）や Kill Switch（閾値超過時にエンジン停止フラグを出す）をサポートします。
- ポートフォリオ構築
  - 候補選定、重み計算（等配分・スコア重み）、セクター制限、ポジションサイズ計算など純粋関数群を提供します。
- リサーチ
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）、将来リターン計算、IC 計算など。
- AI（LLM）モジュール
  - ニュースのセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存する `ai.news_nlp`。
  - マクロ＋ETF MA を組み合わせて市場レジーム判定を行う `ai.regime_detector`。
- ツール
  - Paper Trading の結果を検証するレポート生成スクリプト（`kabusys.tools.paper_verification_report`）。
- ユーティリティ
  - 環境設定管理（`.env` 読み込み）、プロセス優先度設定（Windows/Linux 用ラッパー）など。

---

## 主な機能一覧

- ExecutionEngine 起動／注文管理（OrderManager、OrderRepository、RiskManager、Reconciler）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch）
- DuckDB ベースのファクター計算・リサーチ関数群
- OpenAI を用いたニュースセンチメントスコアリング（バッチ処理・リトライ・検証済み）
- Streamlit ベースの監視ダッシュボード（読み取り専用）
- Paper Trading 向け差分保存・検証機能
- 環境依存設定の .env 自動読み込み（プロジェクトルート検出）

---

## 前提条件 / 必要なもの

- Python 3.8+（プロジェクトで明示されていないため適宜調整してください）
- 必要パッケージ（例）
  - duckdb
  - requests
  - psutil
  - streamlit（ダッシュボードを使う場合）
  - openai（OpenAI クライアント）
  - など（プロジェクトの requirements.txt があればそちらを利用してください）

---

## セットアップ手順（例）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成しアクティブ化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb / requests / psutil / streamlit / openai 等を個別にインストール）
4. プロジェクトルートに `data/` ディレクトリを作成
   - mkdir -p data
5. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - あるいは環境変数で設定する
6. DB 初期化は起動時に自動で行われます（monitoring 側は init_monitoring_db() による冪等作成）

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（"development" | "paper_trading" | "live"）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

注意: Settings クラスで値の妥当性チェックが行われます。必須項目が未設定だと ValueError が発生します。

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。
- テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動／主要コマンド）

1. ExecutionEngine を起動（本番 / ペーパートレード）
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH に保存され、本番 DB と分離されます。
     - 起動時に PID ファイル（data/execution.pid）を作成します。
     - 停止は管理者が `data/stop_requested.flag` を作成すると検出して終了します（run_execution/run_monitoring の両方が stop_flag を参照します）。

2. Monitoring を起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 補足:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV にかかわらず `sqlite_path`（デフォルト: data/monitoring.db）を使用して監視データを保存します。
     - 停止は `data/stop_requested.flag` を作成することで行えます。

3. Streamlit ダッシュボード（読み取り専用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 補足:
     - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine が書き込んでいることを前提とします。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - 補足:
     - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます（デフォルト: data/paper_trading.db）。

5. AI モジュール（ニューススコア / レジーム判定）
   - 直接モジュール関数を呼ぶかスクリプト経由で利用
   - 必須: OPENAI_API_KEY を設定
   - 例（Python から）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")

---

## 停止・強制停止の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_execution.py / run_monitoring.py がループ内でチェックしている停止フラグ。存在すると安全にシャットダウンします。
- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch が閾値を満たした際に書き込むファイル。ExecutionEngine 側で検出して停止するためのシグナル用（上書きは行わず冪等）。
- PID ファイル（data/execution.pid）
  - ExecutionEngine の稼働 PID を記録。SystemMonitor は PID 存在 / 生存チェックを行い stale PID を検出・削除します。

---

## ディレクトリ構成（概要）

以下は主要ファイル／ディレクトリの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングスクリプト
  - data/                         — 実行時データ（DB、PID、フラグなど）を置く想定ディレクトリ（プロジェクトルート）
  - execution/
    - execution_engine.py         — ExecutionEngine（起動 / セッション管理）
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    - ...                         — ブローカー API ラッパ等
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ定義 / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュースを LLM に投げて ai_scores に書き込む
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py          — プラットフォーム差分を吸収した優先度 / affinity 設定
  - monitoring/monitoring_db.py   — 監視用 DB 初期化・アクセス層

（実際のファイルや追加モジュールが他にもあります。上は主要コンポーネントの目次です。）

---

## 開発上の注意 / Tips

- Settings（kabusys.config.Settings）
  - 必須の環境変数が未設定だと ValueError を投げます。.env を作成して必要なキーを設定してください。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければなりません。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は起動時に冪等的にテーブルを作成し、既存 DB のスキーマ拡張（カラム追加）を一定程度行います。
- OpenAI API
  - レスポンスの検証、429/5xx に対するリトライ、部分失敗時の DB 更新保護（対象コード限定の DELETE→INSERT）などを実装しており、API エラー時もフェイルセーフに動く設計です。
- プロセス優先度
  - 起動スクリプトで set_process_priority("high") を呼んでいるため、権限がない OS では警告が出ることがあります（スキップされます）。

---

## トラブルシューティング

- 起動しても動かない / 必須環境変数が足りない:
  - Settings が例外を出力します。ログを確認し、足りない環境変数を .env に追加してください。
- Monitoring がデータを書き込めない:
  - `SQLITE_PATH` のパスやファイル許可を確認してください。streamlit からは読み取り専用で開くため MonitoringEngine を先に起動してください。
- OpenAI 関連で JSON パースに失敗する:
  - LLM の応答を厳密な JSON に整形するようプロンプトを工夫していますが、万が一パースに失敗した場合はログの警告によりスキップされ、全体処理は継続します。

---

README は以上です。実行方法や設定例についてさらに具体的なサンプル（.env.example、docker-compose、CI 用設定等）が必要であれば教えてください。