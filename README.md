# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ＋起動スクリプト群）です。  
このリポジトリには、戦略・ポートフォリオ構築、リサーチ（DuckDB ベース）、実行エンジン／監視、AI を使ったニューススコアリングなどの主要機能が含まれます。

注意: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。

## 概要
- DuckDB / SQLite に保存された価格・ニュース・財務データを用いてファクター算出や特徴量解析を行うリサーチ機能。
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター上限など）に関する純粋関数群。
- ExecutionEngine（発注エンジン）および Monitoring（監視）コンポーネントの起動スクリプト。
- OpenAI を使ったニュースセンチメント評価（ai/news_nlp）および市場レジーム判定（ai/regime_detector）。
- 環境設定用ウィザード（.env 作成補助）、設定検証ツール、ペーパートレード検証レポート生成ツール等の CLI。

## 主な機能一覧
- 環境管理
  - .env 自動読み込み（プロジェクトルートを探索）
  - config_setup: 対話式 .env 作成・更新ツール
  - validate_config: .env と config/*.yaml の事前検証ツール
- 実行／監視
  - run_execution.py: ExecutionEngine 起動（実際の発注／ペーパートレード対応）
  - run_monitoring.py: SystemMonitor をポーリングで実行（監視ログ保存、kill/stop フラグ検出）
  - MonitoringEngine: System/Trade/Risk モニタを束ねアラート／Kill Switch 制御
- データ永続化（監視用）
  - monitoring_db: SQLite にテーブルを作成・読み書きする永続化層
- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 重み算出（等配分/スコア加重）
  - ポジションサイズ算出（risk_based / equal / score、単元株丸め、aggregate cap 調整）
  - セクター上限適用、レジーム乗数
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- AI
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai_scores へ書き込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- ユーティリティ
  - logging_setup: 統一ロギング（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率・成功率・レイテンシ等）

## 前提 / 必要環境
- Python 3.9+（ソースは型ヒントに依存）
- SQLite3（標準ライブラリ）
- 推奨 Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合、なくても警告扱い）
- 任意ツール:
  - jq 等（JSON 処理・デバッグ用）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください。）

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリ直下に移動
2. Python 環境を整える（venv 等）
3. 必要パッケージをインストール
4. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 主に必要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL — デフォルト INFO
     - PAPER_FILL_MODE — paper_trading の注文約定挙動 (instant|partial|never|reject)（デフォルト instant）
     - その他は config_setup の案内に従ってください
5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いにできます。

6. 必要なディレクトリを作成（ログ/データ等）
   - data/ — デフォルト DB / flag / pid ファイル保存場所
   - logs/ — ログファイル保存先（LOG_DIR 環境変数で変更可）

## 使い方（起動方法）
- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60）。
  - 監視は常に Settings.sqlite_path（本番 sqlite_path）を使用します（KABUSYS_ENV に関係なく）。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

- 実行（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます。
  - エンジンは data/execution.pid に PID ファイルを書きます。停止フラグ（data/stop_requested.flag）を検知すると停止します。
  - Kill Switch（監視側）が検出した場合、data/kill.flag が作成され ExecutionEngine を停止する仕組みがあります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 周り（プログラムから呼び出す例）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  - 注意: API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。API 呼び出しは失敗時にフォールバック動作が組まれていますが、キー未設定は例外になります。

## 主要設定（環境変数）一覧（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト instant
- OPENAI_API_KEY (AI 機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （アラート用、任意）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- LOG_DIR (ログディレクトリ、デフォルト logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0|1) — 本番では 0 推奨（1 にすると起動時に kill.flag を自動クリアする）

## 停止・フラグファイル
- data/stop_requested.flag
  - run_monitoring / run_execution のループを優雅に停止するためのフラグファイル。
- data/kill.flag
  - Monitoring の KillSwitch が作成するフラグ。ExecutionEngine 側ではこれを検出して停止する用途。
- data/execution.pid
  - ExecutionEngine の PID ファイル（起動時に書き込まれます）。

## ログ
- ログは標準出力（stdout）とタイムローテートされたファイルに出力されます（logs/<app_name>.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一して行われます。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

## 開発・デバッグのヒント
- validate_config による事前検証で必須環境変数やファイルパスの問題を検出できます。
- PyYAML が未インストールの場合、config/*.yaml の内容検証はスキップされます（警告）。
- psutil によるプロセス優先度設定は権限が必要な場合があります。AccessDenied は警告として処理されます。
- DuckDB の接続はモジュール単位で受け渡し、SQL と Python を組み合わせた計算を行います（research モジュール参照）。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings クラス（自動 .env ロード）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / CRUD ユーティリティ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （取引監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — 各モニタ統合
    - alert_manager.py       — （アラート送信機能）
  - execution/
    - execution_engine.py    — 実行エンジン（注文処理セッション）
    - broker_factory.py      — ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — OpenAI によるニュースセンチメント評価
    - regime_detector.py     — market_regime 判定（MA + macro LLM）
  - data/                    — (運用時に生成される) DB / flag / pid / logs 等
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

（上記以外にもユーティリティモジュールやテスト対象のコードが含まれます）

## 注意事項 / 運用上の留意点
- KABUSYS_ENV が `live` の場合は本番モードです。設定（API トークン、LINE 通知など）を慎重に扱ってください。validate_config は live のときに追加警告を出します。
- run_monitoring は Settings.sqlite_path（本番）を常に参照します。監視は paper_trading 環境でも本番監視 DB を見に行く設計になっています（意図的挙動）。
- paper_trading モードでは発注は MockBrokerClient により模擬的に処理され、DB は paper_sqlite_path（data/paper_trading.db）へ分離されます。
- OpenAI 使用部分は API コストとレートリミットに留意してください。news_nlp と regime_detector はリトライ/バックオフ処理を組み込んでいますが、API キーの管理は適切に行ってください。
- .env は機密情報（API トークン等）を含むため、絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

問題の報告や README の改善要望があれば教えてください。必要であれば起動例の詳細（systemd ユニット / docker-compose など）や、さらに細かいモジュール別ドキュメントも作成します。