# KabuSys

日本株自動売買システムの簡易実装群（ライブラリ＋実行スクリプト）。  
このリポジトリには取引エンジン起動スクリプト、監視（Monitoring）周り、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI を使ったニュース NLP / レジーム判定、ツール類が含まれます。

主な目的はプロダクションに近い構成での自動売買・監視パイプラインの実装例を提供することです。

---

## 機能一覧

- Execution（発注）関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler による起動時リコンシリエーション
  - Paper Trading モード（本番 DB と完全分離・MockBroker を使用）

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイル書き込みによる ExecutionEngine 停止シグナル
  - AlertManager: LINE プッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額／スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（リスクベース、利用可能現金のスケーリング、単元株丸め）

- Research（リサーチ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI を利用）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA による市場レジーム判定（bull/neutral/bear）
  - API 呼び出しは堅牢なリトライ・バリデーション実装

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 必要条件（推奨）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準で Python に同梱）
- ネットワーク接続（ブローカー/API/LINE/OpenAI 使用時）

依存関係はプロジェクト配布に requirements.txt があればそちらを利用してください。無ければ個別にインストールします：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリをリポジトリルートにする。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. 環境変数を設定する（.env をプロジェクトルートに置くと自動読み込みされます — 後述の挙動参照）。
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN（J-Quants API を使うコンポーネントで必要）
   - KABU_API_PASSWORD（kabuステーション API を使う場合に必須）
   任意/デフォルトあり:
   - OPENAI_API_KEY（AI 機能を使う場合に必要）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant / partial / never / reject、デフォルト instant）
   - PID_FILE_PATH / KILL_FLAG_PATH 等

4. DB 初期化は起動スクリプトが内部で行います（monitoring のテーブル作成は init_monitoring_db による冪等処理）。

.env 自動読み込みについて:
- プロジェクトルートは .git または pyproject.toml を基準に自動検出します。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要スクリプト）

実行はパッケージを直接実行する方法が想定されています（リポジトリルートで実行するか PYTHONPATH に src を追加してください）。

- Monitoring（常駐ポーリング）
  - 簡易起動:
    python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を high に設定します（psutil を利用）。
    - SQLite（monitoring DB）と DuckDB に接続し SystemMonitor のポーリングを開始します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に記録）。

- Execution（発注エンジン）
  - 起動:
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
    - プロセス優先度を high に設定します。
    - 起動時に Reconciler による自動リコンシリエーションが行われます（OrderSent 状態の照合など）。

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    --from / --to: YYYY-MM-DD 形式で期間指定
    --db: SQLite DB ファイル (優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db)
  - 出力: 標準出力に検証サマリ（稼働率、注文成功率、送信率、P95 レイテンシなど）。基準値を下回ると FAIL 表示。

- Streamlit ダッシュボード（監視データ可視化）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 読み取り専用で SQLite DB を開き、Positions / Orders / System / Overview を表示します。

- AI 機能
  - ニューススコア生成:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（api_key 引数で直接渡すことも可能）
    - モデルは gpt-4o-mini を想定、レスポンスのバリデーション・リトライ実装あり
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同じく OPENAI_API_KEY が必要

注意: AI 機能は API エラー時にフェイルセーフとしてスコアをゼロで扱う等の保護が入っていますが、API キー未設定では例外になります。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション用）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

---

## 実行例（環境変数を付けて）

監視を 30 秒間隔で起動する例:
```bash
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

Paper Trading モードで Execution を起動する例:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

Paper 検証レポート（DB 指定）:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

Streamlit ダッシュボード:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

---

## 注意点・設計上のポイント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。OS 環境変数は上書きされません（.env.local は上書き可）。
- Monitoring の DB 初期化（テーブル作成・マイグレーション）は init_monitoring_db が冪等に行います。
- Paper Trading モードは本番 DB とは別ファイルを使うため、誤って本番の注文データを汚さないよう設計されています。
- AI の呼び出しには OpenAI SDK（OpenAI API）が必要。API 呼び出しはバッチ・リトライ・レスポンスバリデーションを行っていますが、利用時はコスト・レートリミットに注意してください。
- プロセス優先度設定（psutil 経由）や CPU affinity 設定は実行環境（権限）に依存し、失敗時はログを記録してスキップします。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールと簡単な説明です。

- src/
  - kabusys/
    - __init__.py — パッケージ定義（バージョン等）
    - config.py — 環境変数 / 設定管理
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
    - run_execution.py — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
      - system_monitor.py — システム状態 / データ鮮度チェック
      - trade_monitor.py — 注文滞留 / 約定異常監視
      - risk_monitor.py — ドローダウン・ポジション監視
      - kill_switch.py — kill.flag 管理
      - alert_manager.py — LINE 通知
      - monitoring_engine.py — 複数 Monitor を束ねたエンジン
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py — 発注ワークフロー（Order 作成・送信等）
      - reconciler.py — 起動時リコンシリエーション
      - （その他: broker_factory, execution_engine, order_repository 等が存在する想定）
    - portfolio/
      - portfolio_builder.py — 候補選定・重み計算
      - position_sizing.py — 発注株数計算（リスク制限、単元丸め）
      - risk_adjustment.py — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py — Momentum, Volatility, Value 等のファクター計算（DuckDB）
      - feature_exploration.py — 将来リターン、IC、統計サマリ
    - ai/
      - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコア
      - regime_detector.py — マクロ + ETF MA によるレジーム判定（OpenAI）
    - utils/
      - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
    - data/ (想定されるデータディレクトリ)
      - kabusys.duckdb (デフォルト DUCKDB_PATH)
      - monitoring.db / paper_trading.db (SQLite)

（実際のリポジトリには上記以外にも補助モジュールが含まれます。ここでは主要なものを抜粋しています。）

---

## 最後に

この README はコードベース内の docstring / 設計コメントに基づいて作成しています。実際に運用する際は各種 API キー・ブローカー接続・資金管理設定の正当性を十分に確認してください。テスト環境（paper_trading）を活用して安全に検証することを強く推奨します。