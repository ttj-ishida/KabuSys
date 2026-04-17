# KabuSys

日本株向けの自動売買 / リサーチ / 監視フレームワーク（ミニマル実装）。  
このリポジトリは、発注エンジン、監視コンポーネント、ファクター計算、AIベースのニューススコアリング等を含むモジュール群で構成されています。

## 概要
- 発注（ExecutionEngine）と監視（MonitoringEngine）を分離して実装。
- Paper Trading モードを用意し、本番 DB と分離してテスト可能（MockBroker を使用）。
- DuckDB を利用した時系列データ処理（prices_daily / raw_financials 等）。
- OpenAI（gpt-4o-mini）を用いたニュース NLP スコアリング / マクロ判定機能。
- SQLite を用いた監視ログ保存 & Streamlit ダッシュボードによる可視化。
- プロセス優先度や CPU affinity をプラットフォーム差分を吸収して設定可能。

## 主な機能
- Execution
  - 起動時のリコンシリエーション（Reconciler）
  - 注文作成 / 同期 / 管理（OrderManager, OrderRepository）
  - Paper Trading モード（MockBrokerClient）と専用 SQLite（data/paper_trading.db）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文滞留 / 約定異常価格検出
  - ドローダウン・ポジション上限監視と Kill Switch（kill.flag）の自動生成
  - 監視ログ永続化（MonitoringDB）
  - Streamlit ダッシュボード
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン / IC 計算、特徴量サマリー
  - 候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム乗数
- AI
  - ニュース記事のセンチメントスコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 動作要件（目安）
- Python 3.10+
- 必要なサードパーティライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリで利用）
- ネットワーク環境（OpenAI を使う場合）

※ requirements.txt は本リポジトリに含まれていないため、上記パッケージを適宜インストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

## 環境変数（代表）
主な設定は環境変数または .env / .env.local にて指定します。自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

重要な変数（抜粋）:
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス指定

例 (.env):
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
MONITOR_POLL_INTERVAL=60
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

## セットアップ手順
1. リポジトリをチェックアウト
2. Python 仮想環境の作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. .env を作成して必要な環境変数を設定
5. 初期 DB（DuckDB / SQLite）ファイルを用意
   - monitoring の初期テーブルは run_monitoring / run_execution 実行時に自動で作成されます（init_monitoring_db）。

## 使い方（主なコマンド）
- ExecutionEngine の起動
  - 本番または paper_trading モードに応じて動作します。Paper の場合は MockBroker を使用し、データは data/paper_trading.db に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に PID ファイル（Settings.pid_file_path）を書き出します。data/stop_requested.flag が存在すると起動せず終了します。

- Monitoring の起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path の DB を使用します（監視は本番 DB を参照する設計）。

- Streamlit ダッシュボード（監視の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート（CLI）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI・レジーム判定（プログラム呼び出し例）
  - ニューススコアリング:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

## 停止 / Kill シグナル
- run_execution / run_monitoring はプロジェクトの data ディレクトリにある制御ファイルを参照します。
  - data/stop_requested.flag : 監視ループ / エンジンの起動・継続を停止するチェックに使用。作成されると起動停止処理が行われます（スクリプトはこれを参照して終了します）。
  - data/kill.flag : KillSwitch によって書き込まれ、ExecutionEngine に停止を促します（監視コンポーネントがリスク条件を検出した場合に生成）。
  - data/execution.pid : ExecutionEngine の PID を保存（process health チェックに使用）。
- Kill flag を手動で消す場合:
  ```
  rm data/kill.flag
  ```
  または、KillSwitch.clear() を使用してプログラムから削除できます。

## 主要ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: Monitoring ポーリング起動スクリプト
  - utils/
    - process_priority.py: プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py: 注文発行・状態管理
    - order_repository.py: Orders DB 操作（SQLite）
    - reconciler.py: 再起動時の同期・復旧ロジック
    - broker_factory.py / broker_api.py: ブローカークライアント関連
    - ...（ExecutionEngine 本体等）
  - monitoring/
    - monitoring_db.py: 監視用 SQLite スキーマ & MonitoringDB クラス
    - system_monitor.py: システム状態・データ鮮度チェック
    - trade_monitor.py: 注文滞留・約定異常チェック
    - risk_monitor.py: ドローダウン・ポジション上限チェック
    - kill_switch.py: kill.flag の生成/削除
    - alert_manager.py: LINE プッシュ通知ラッパー
    - monitoring_engine.py: 各 Monitor を束ねる実行ロジック
    - streamlit_dashboard.py: Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け
    - position_sizing.py: 発注株数算出
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py: 将来リターン, IC, 統計サマリー
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI）
    - regime_detector.py: 市場レジーム判定（OpenAI + ma200）
  - tools/
    - paper_verification_report.py: Paper Trading レポート生成 CLI

（実際のコードベースを参照してより詳細なファイル一覧を確認してください）

## 開発時の注意点 / 設計メモ
- Settings は環境変数駆動。必須変数が未設定だと起動時に例外を投げます。
- Monitoring はどの KABUSYS_ENV でも Settings.sqlite_path（監視 DB）を参照する設計です（監視は本番 DB を想定）。
- Paper Trading は本番 DB と完全分離するため、PAPER_TRADING_SQLITE_PATH を利用します。
- OpenAI など外部 API はネットワーク障害や 5xx を想定してリトライやフォールバックを行う実装になっています（AI 関連の詳細は各モジュール内コメントを参照してください）。
- 一部関数はテストのしやすさを考慮して API 呼び出し部分を分離しており、単体テストでモック可能です（例: _call_openai_api のパッチ）。

## 追加・拡張案（参考）
- 銘柄ごとの lot_size をマスターで管理し、position_sizing で使用する。
- モニタリング用のメトリクス収集を Prometheus Exporter で追加。
- ExecutionEngine の可観測性向上（トレース / メトリクス）。
- DuckDB のスキーマ・ETL パイプライン補強（prices_daily / raw_financials の自動更新ジョブ等）。

---

詳細な実装や API の振る舞いは各モジュールの docstring / コメントを参照してください。README にない具体的な使い方や補足が必要であれば、用途に合わせてサンプルや手順を追加します。