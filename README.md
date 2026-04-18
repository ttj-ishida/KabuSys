# KabuSys

日本株向け自動売買システムの一部コードベース。ポートフォリオ構築・リサーチ・監視・実行・AI によるニュース評価などのコンポーネントを含みます。

以下は本リポジトリの概要・機能・セットアップ・利用方法・主要ディレクトリ構成の説明です。

---

プロジェクト概要
- 日本株自動売買システムのコアライブラリ群（ポートフォリオ構築、ポジションサイジング、リスク調整、監視、ExecutionEngine 起動スクリプト、AI ニューススコアリング等）。
- DuckDB / SQLite を用いた分析・ログ永続化、OpenAI を利用したニュースセンチメント評価機能を含む。
- 実行環境は `KABUSYS_ENV` によって `development` / `paper_trading` / `live` を切り替え可能。`paper_trading` は本番 DB と分離して専用の SQLite（デフォルト: `data/paper_trading.db`）を使用します。

主な機能一覧
- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等加重 / スコア加重のウェイト計算
  - ポジションサイズ計算（risk-based, equal, score）
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（OpenAI）連携
  - ニュース記事を集約して LLM による銘柄ごとのセンチメント（ai_scores）を生成
  - マクロニュース + ETF（1321）MA200乖離で市場レジーム判定（bull/neutral/bear）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック、monitoring DB へのログ
  - TradeMonitor / RiskMonitor: 注文・リスク関連の監視、ダッシュボード更新、kill switch の評価
  - MonitoringEngine: 各モニタを束ねて定期実行、アラートトリガー
  - KillSwitch: `data/kill.flag` により ExecutionEngine に停止シグナルを送出
- 実行（Execution）
  - ExecutionEngine 起動スクリプト。`paper_trading` 環境では MockBroker を利用して本番 DB と分離
- ユーティリティ
  - `.env` 生成ウィザード（対話式）
  - 設定検証 CLI（YAML 解析は PyYAML 任意）
  - Paper Trading の検証レポート生成スクリプト

依存（主要）
- 必須（実行に必要）
  - Python 3.9+
  - duckdb
  - psutil
- AI 機能を使う場合
  - openai（OpenAI の公式クライアント）
  - OpenAI API キー（環境変数 `OPENAI_API_KEY` または関数引数）
- 任意
  - PyYAML（config/*.yaml の内容検証用、`kabusys.validate_config` が利用）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／チェックアウト
2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
   - validate 用に PyYAML も使うなら: pip install pyyaml
   - ※ requirements.txt があればそれを利用してください（本コードベースには含まれていない想定）。
4. .env の初期作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI機能を使う場合）※ .env に直接書く際は取り扱いに注意
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗としたい場合: python -m kabusys.validate_config --strict
6. データディレクトリの準備（自動作成されるが手動で作ることも可）
   - mkdir -p data logs

環境変数（重要なものとデフォルト）
- KABUSYS_ENV (default: development) — 実行モード（development / paper_trading / live）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY — AI モジュールの API キー
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default: 60）
- PID / flag 関連:
  - data/execution.pid （ExecutionEngine の PID ファイル）
  - data/stop_requested.flag （手動で作成すると run_monitoring / run_execution のループを停止するトリガ）
  - data/kill.flag （KillSwitch が書き込む停止フラグ）

注意: Monitoring は KABUSYS_ENV に関わらず `sqlite_path`（本番監視 DB）を使用します。Execution は `paper_trading` の場合、paper 用 SQLite を別途用います（分離保証）。

---

使い方（主要スクリプト）
- 環境設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit(1)

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と完全分離）。
    - 起動時に `data/stop_requested.flag` が既に存在すると起動しません。
    - 停止は `data/stop_requested.flag` を作成することで行えます（監視プロセス / スクリプトが検出して停止処理を行います）。
    - Execution 起動中、`data/execution.pid` に PID が書かれます。

- 監視ループ起動（SystemMonitor 等のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は `sqlite_path`（デフォルト: data/monitoring.db）を使用します。
  - 監視中に `data/stop_requested.flag` を検出するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（`PAPER_TRADING_SQLITE_PATH` 環境変数を上書き）
  - 出力: コンソールに検証レポート（稼働率、注文成功率、レイテンシなど）を表示

- AI 関連（ニューススコア / レジーム判定）
  - 実行には `OPENAI_API_KEY` が必要（引数で渡すことも可能）。
  - モジュール関数:
    - kabusys.ai.score_news — ニュースを評価して `ai_scores` テーブルへ保存
    - kabusys.ai.regime_detector.score_regime — 市場レジームを判定して `market_regime` テーブルへ保存
  - 注意: OpenAI 呼び出しは外部 API コストが発生します。API キー、利用制限、コストに注意してください。

ログ
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` を通じて統一的に行います。
- デフォルトログディレクトリ: `logs/`
- ログファイル: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日分保持）
- コンソールログは stdout に出力されます。

停止・Kill Switch
- 監視プロセスと実行エンジンの停止:
  - `data/stop_requested.flag` を作成すると run_monitoring / run_execution がそれを検出して終了または停止処理を行います。
- 強制停止（リスクによる自動停止）:
  - KillSwitch はリスク条件（ドローダウン超過、ポジション上限超過など）を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止信号を送ります。
  - `KillSwitch.clear()` は起動時のクリアに使え、`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアする挙動になります（本番では危険なので通常は 0 を推奨）。

注意点・ベストプラクティス
- 本番環境（KABUSYS_ENV=live）では `.env` に機密情報を平文で置く際に適切な管理が必要です（Git にコミットしない）。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で設定しないことを推奨（Kill Switch が自動でクリアされるため安全性が低下します）。
- validate_config の結果を --strict モードで CI に組み込むと設定ミスを早期に検出できます。
- AI モジュールは外部 API 依存のため失敗時のフォールバック（スコア 0.0 等）ロジックを組み込んでありますが、APIキー漏洩・コスト制御に注意してください。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py         — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py           — SQLite テーブル作成・永続化操作
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照される)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照される)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/
    - execution_engine.py (参照される)
    - broker_factory.py (参照される)
    - order_manager.py (参照される)
    - order_repository.py (参照される)
    - reconciler.py (参照される)
    - risk_manager.py (参照される)
  - monitoring/ (上記)
  - research/ (上記)
  - portfolio/ (上記)
  - その他モジュール...

（注）上は抜粋で、実際のファイル数・構成はリポジトリ内の `src/kabusys` を参照してください。

サンプル .env（最低限）
- .env.example を参考に設定してください。最低限必要な環境変数:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_api_password
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - LOG_LEVEL=INFO

FAQ / トラブルシューティング
- DuckDB / SQLite 関係のファイルパスの親ディレクトリが存在しないと警告が出ますが、起動時に自動作成されることが多いです。問題がある場合は手動で `data/` や `logs/` を作成してください。
- validate_config で PyYAML が見つからない場合は YAML 検証はスキップされます（必要なら `pip install pyyaml`）。
- OpenAI の呼び出しでレート制限や一時エラーが発生した場合は、該当モジュールは指数バックオフでリトライし、最終的にフォールバックして続行する設計です。

貢献
- バグ修正・機能追加は PR を歓迎します。機密情報は絶対にコミットしないでください（.env は Git に含めない）。

---

この README はコードベース（src/kabusys 以下）の主要部分を元に作成しています。実際に運用する前に `python -m kabusys.validate_config` で設定を検証し、必要な依存のインストールと .env の適切な管理を行ってください。