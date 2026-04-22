# KabuSys

日本株向け自動売買システムのコードベースです。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ファクター計算・リサーチ、AI を使ったニュース NLP、ポートフォリオ構築ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します。

- ExecutionEngine：発注・約定管理・リスク管理を行う実行エンジン
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録（本番 DB と分離）
- Monitoring：システム稼働状況・注文状態・リスク（ドローダウンやポジション上限）を定期チェックし、kill flag で ExecutionEngine を停止可能
- AI：ニュースのセンチメント評価（OpenAI）や市場レジーム判定（ma200 + マクロセンチメント）
- Research：DuckDB 上の株価・財務データからファクターを計算（Momentum / Volatility / Value 等）や IC 計算
- Portfolio：銘柄選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- Tools：ペーパートレード検証レポート等ユーティリティ
- Utils：ログ設定、プロセス優先度設定など共通ユーティリティ
- 設定・検証：対話式 .env 作成ウィザード、起動前設定検証ツール

設計方針の例：
- 本番データベースとペーパートレード DB を分離（設定により切替）
- DuckDB を分析用に利用（prices_daily, raw_financials 等を想定）
- LLM 呼び出しは失敗してもフェイルセーフで継続（スコアを欠損にする等）
- ルックアヘッドバイアス回避（date.today() 等を直接参照しない設計の配慮）

---

## 主な機能一覧

- 実行（Execution）
  - 発注管理、OrderRepository / OrderManager、RiskManager、Reconciler、ExecutionEngine（pid ファイル・停止フラグ対応）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/Disk、プロセス生存、データ鮮度
  - TradeMonitor：取引ログの滞留・価格異常検出（実装ファイルは該当ディレクトリ）
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新・リスクログ
  - MonitoringEngine：各 Monitor を束ねるポーリングループ、KillSwitch 評価、AlertManager 経由で通知
- AI
  - news_nlp.score_news：ニュースを LLM へ送り銘柄別センチメントを ai_scores へ書き込み（OpenAI 使用）
  - regime_detector.score_regime：ETF (1321) MA200 比 + マクロニュースでレジーム判定・DB 書き込み
- Research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、統計サマリ
- Portfolio
  - 候補選択（select_candidates）
  - 等重・スコア重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- CLI / ツール
  - .env 作成ウィザード：`python -m kabusys.config_setup`
  - 設定検証：`python -m kabusys.validate_config`
  - 監視ループ起動：`python -m kabusys.run_monitoring`
  - 実行エンジン起動：`python -m kabusys.run_execution`
  - ペーパートレード検証レポート：`python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順（ローカル開発向け）

以下は開発環境の一般的な手順例です。実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください。

1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 本リポジトリで想定される主要依存例：
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時）
   - （requirements.txt がない場合は上のパッケージを個別にインストールしてください）

3. ディレクトリ作成（ログ・データ保存用）
   - mkdir -p data logs

4. 初期設定（.env）
   - 対話式ウィザードで .env を作る：
     - python -m kabusys.config_setup
   - または手動で .env を作成。重要な環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/…）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）

   - 自動 .env ロード:
     - プロジェクトルート（.git または pyproject.toml が存在する場所）を基準に `.env` / `.env.local` を自動読み込みします。
     - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1)

6. DB 初期化
   - 監視用 SQLite はスクリプトが起動時にテーブル作成（冪等）します。
   - DuckDB の分析テーブル（prices_daily / raw_financials / raw_news 等）は外部データソースから投入する必要があります（スクリプトでデータを用意してください）。

注意:
- .env や機密情報は Git にコミットしないでください。

---

## 使い方（起動コマンド例）

- 実行エンジンの起動
  - 環境により KABUSYS_ENV を設定してください（paper_trading は MockBrokerClient を使用）。
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を "high" に設定し、SQLite / DuckDB に接続
    - Paper トレード時は PAPER_TRADING_SQLITE_PATH に記録
    - data/stop_requested.flag があると起動しない / 実行中に検知で停止

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - Monitoring は .env の KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを記録します
  - 停止フラグ: data/stop_requested.flag を配置すると監視ループが終了します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート（SQLite DB が必要）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH で DB ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI モジュールの利用（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、target_date（date 型）、api_key（None の場合は環境変数 OPENAI_API_KEY を使用）
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に呼び出し可能
  - OpenAI API キーが必要（OPENAI_API_KEY）

ログ設定:
- 全起動スクリプトは共通の logging 設定関数 setup_logging を使用します（logs/<app_name>.log に日次ローテーションで出力）。

停止・Kill Switch:
- KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine は起動時および実行中にこのフラグをチェックします。
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアされます（本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他（代表）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI を使用する場合に必須
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- LOG_DIR: ログ保存先（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

詳しくは `kabusys/config.py` を確認してください。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリの主要ファイル・ディレクトリ（src/kabusys 以下）の簡易ツリーです。実際のツリーはさらに細分化されています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証ツール
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py        — （滞留注文・約定異常等検出）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （通知管理: LINE 等、実装場所）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                — ExecutionEngine 関連（OrderManager, BrokerFactory, RiskManager 等）
  - data/                     — 実行時に生成される (data/monitoring.db, data/paper_trading.db, data/kill.flag, data/*.pid など)
  - logs/                     — ログ出力先（デフォルト）

注:
- monitoring_db.py は DB スキーマの作成とマイグレーションを行います（冪等）。
- 実際に ExecutionEngine や TradeMonitor の具体実装ファイルは execution/ 以下に配置されています（今回の抜粋では詳細省略）。

---

## 開発上の注意事項

- 機密情報 (.env) は絶対にリポジトリにコミットしないでください。
- 本番モード（KABUSYS_ENV=live）では LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。
- run_monitoring は監視用 DB に常に "本番" sqlite_path を使います（KABUSYS_ENV に関わらず）。
- paper_trading モードは本番 DB と完全分離しているためテストに適しています。
- OpenAI など外部 API 呼び出しはレイテンシや失敗を考慮して設計されていますが、API キーやコストには注意してください。
- システム優先度の設定や CPU affinity は OS により挙動が異なります（psutil を使用）。権限不足で設定できない場合は警告が出ます。

---

必要に応じて README の補足（依存関係の正確なリスト、データ投入スクリプト、CI/デプロイ手順、各モジュールの詳細設計ドキュメント）を追加できます。どの情報を優先して追加しますか？