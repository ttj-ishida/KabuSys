# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行バイナリ群。  
本リポジトリは戦略のリサーチ・ポートフォリオ構築・発注エンジン・監視・AI（ニュースセンチメント・レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つコンポーネントで構成されています。

- 取引ロジックの実行（ExecutionEngine）
- 注文管理（OrderManager / OrderRepository）
- 再起動時の自動復旧（Reconciler）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュースを用いた AI センチメント（OpenAI を利用）
- 市場レジーム判定（MA とマクロニュースの融合）
- 監視（System / Trade / Risk の監視、LINE 通知、kill flag）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計上の注意点：
- Paper Trading（`KABUSYS_ENV=paper_trading`）時はブローカークライアントをモック化し、専用の SQLite DB（`data/paper_trading.db`）を使用して本番 DB と完全分離します。
- データ系は DuckDB（時系列・ファクタ計算用）と SQLite（監視 / 発注ログ等）を併用します。
- .env / .env.local からの自動読み込みを行います（無効化可）。

---

## 主な機能一覧

- Execution
  - OrderManager: 注文作成・同期・キャンセル管理
  - Reconciler: 起動時にブローカーと突合して不整合を検出・修正
  - RiskManager（設定に基づく制限・サーキットブレーカー等）※実装の一部は本コードに示されています
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringDB: 監視ログの永続化（SQLite）
  - AlertManager: LINE へのプッシュ通知（クールダウンあり）
  - KillSwitch: flag ファイルにより ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Portfolio
  - ファクター計算（momentum, volatility, value 等）
  - 特徴量解析・IC 計算
  - 候補選定と配分（等分、スコア重み、リスクベース）
  - セクター上限・レジーム乗数・ポジション計算（単元丸め、aggregation cap）
- AI
  - news_nlp: ニュースをまとめて OpenAI に渡し銘柄単位のセンチメントを生成、ai_scores へ書き込み
  - regime_detector: ETF MA とマクロニュースセンチメントを合成して daily regime を判定
- ツール
  - paper_verification_report: Paper Trading DB の検証レポート出力
  - streamlit_dashboard: Monitoring DB を参照するダッシュボード

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化することを推奨します（venv, pyenv 等）。

2. 依存ライブラリのインストール（例）
   - 以下は本コードで使用されている主要パッケージの例です。プロジェクト内に requirements.txt がある場合はそちらを利用してください。
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     pip install duckdb psutil requests openai streamlit

3. ディレクトリと DB 初期化
   - data フォルダを作成:
     mkdir -p data
   - 監視 DB / Paper DB は起動スクリプトが自動でテーブル作成（マイグレーション含む）します。手動で用意する必要は基本的にありません。

4. 環境変数（.env）
   - プロジェクトルートに `.env` や `.env.local` を置くことで設定を読み込みます（自動読み込みはデフォルトで有効）。
   - 主な環境変数（デフォルトを併記）:
     - KABUSYS_ENV = development | paper_trading | live (default: development)
     - OPENAI_API_KEY = <your_openai_key>
     - JQUANTS_REFRESH_TOKEN = <required for J-Quants 使用時>
     - KABU_API_PASSWORD = <kabuステーションパスワード>
     - LINE_CHANNEL_ACCESS_TOKEN = (任意, 通知用)
     - LINE_USER_ID = (任意, 通知用)
     - SQLITE_PATH = data/monitoring.db
     - DUCKDB_PATH = data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
     - PAPER_FILL_MODE = instant | partial | never | reject (default: instant)
     - LOG_LEVEL = INFO
     - MONITOR_POLL_INTERVAL = 60（秒、run_monitoring で参照）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1（自動ロードを無効化）

5. 権限・プロセス設定について
   - Windows / Linux のプロセス優先度設定には psutil を使用します。権限不足等で設定できない場合は警告が出て処理は継続します。

---

## 使い方

以下は主要な起動・ツール利用例です。

- 実行エンジン（ExecutionEngine）起動
  - 本番モード:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading モード（モックブローカー・分離 DB 使用）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行はデーモン化や systemd 管理下で動かすことを想定しています。起動時に PID ファイル（data/execution.pid デフォルト）を作成します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト: 60）。
  - 監視は常に「本番の sqlite_path」を使用して監視ログを書き込みます（環境に依存しない）。

- 停止フラグ / kill flag
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して順次停止します（run_execution は起動前に既存フラグがあれば起動を中止）。
  - data/kill.flag は KillSwitch により生成され、ExecutionEngine に停止を促します（例: ドローダウン超過）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で Monitoring DB を参照し、Overview / Positions / Orders / System 情報を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI モジュール（ニュースセンチメント / レジーム）
  - OpenAI API キーを設定（OPENAI_API_KEY）。
  - ニューススコアリング（プログラム内呼び出し例）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

- テスト用 / ユーティリティ
  - MonitoringEngine.run_once を使えば単一サイクルで複数のモニターを実行できます（ユニットテスト等に便利）。

注意:
- 実際の発注・ブローカー連携は BrokerClientFactory 等の実装に依存します。Paper 環境では MockBrokerClient が使用され、専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- OpenAI 呼び出しのリトライ・バリデーション等はモジュール内部で実装されていますが、API 利用料とレート制限に注意してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

（リポジトリは src/kabusys 配下に実装を持つ想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込み、Settings クラス
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading での挙動切替）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
      - Paper Trading DB の検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → OpenAI による銘柄別センチメント計算・ai_scores へ書込
    - regime_detector.py
      - マクロニュース + ETF MA による日次レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py
      - SQLite スキーマ作成・CRUD。MonitoringDB クラスを提供
    - system_monitor.py
      - CPU/メモリ/disk/process/data freshness のチェック
    - trade_monitor.py
      - 滞留注文・価格異常チェック
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag の作成 / 削除ロジック
    - alert_manager.py
      - LINE 送信（クールダウン・失敗ハンドリング）
    - monitoring_engine.py
      - 複数 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py
      - Streamlit を使った可視化スクリプト
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - execution_engine.py (エンジン本体: run_session など)
    - broker_factory.py / broker_api.py（ブローカー抽象）
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
    - process_priority.py
    - __init__.py
  - data/ （実行時に使用されるディレクトリ例）
    - monitoring.db (SQLite)
    - paper_trading.db (Paper trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag, ...

---

## 運用上の注意・推奨事項

- Paper Trading と本番 DB は必ず分離すること。環境変数 `KABUSYS_ENV=paper_trading` を使用してください。
- OpenAI キーなどのシークレットは `.env` に保管せず、運用環境では安全なシークレット管理を推奨します。
- プロセス優先度や CPU affinity の設定は権限に依存するため、実行環境（コンテナ / ホスト）で事前に確認してください。
- 監視（MonitoringEngine）は `MONITOR_POLL_INTERVAL` を適切に設定し、LINE 通知トークン・ユーザーの設定とクールダウンを確認してください。
- kill.flag / stop_requested.flag により安全停止を実装しています。自動化スクリプトや運用ドキュメントで停止手順を明確にしておくことを推奨します。

---

## 参考コマンドまとめ

- 実行（本番）
  KABUSYS_ENV=live python -m kabusys.run_execution

- 実行（Paper Trading）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視開始
  python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載されていない内部 API（ユーティリティ関数やクラス）については、各モジュールの docstring を参照してください。もし README の補足（インストール用の requirements.txt、systemd ユニット例、Dockerfile 例、より詳細な運用手順など）が必要であれば知らせてください。