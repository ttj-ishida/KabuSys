# KabuSys

日本株向けの自動売買・リサーチ基盤コンポーネント群。  
バックテストや戦略本体とは切り離した、実行（ExecutionEngine）、監視（Monitoring）、リサーチ（Research）、ポートフォリオ構築（Portfolio）、AI（ニュースセンチメント／レジーム判定）などのユーティリティ群を含みます。

主な目的は「本番口座での注文実行と運用監視」「Paper Trading による検証」「DuckDB を用いたファクター計算・探索」「LLM を用いたニューススコアリング／レジーム判定」です。

---

## 機能一覧

- Execution
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - ブローカークライアントの抽象化（Paper/LIVE 切替）
  - OrderManager / OrderRepository / Reconciler（再起動後のリコンシリエーション）
  - RiskManager（発注制限等）
- Monitoring
  - SystemMonitor（CPU/Memory/Disk、プロセス PID、データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン、保有上限監視）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止指示）
  - AlertManager（LINE へのプッシュ通知）
  - MonitoringEngine（各モニタを束ねたポーリングループ）
  - Streamlit ダッシュボード（監視用 UI）
- Research / Data
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン / IC 計算、統計サマリー
- Portfolio construction
  - 候補選定、等加重・スコア加重、ポジションサイズ計算（lot 単位丸め、aggregate cap）
  - セクター上限適用、レジーム乗数
- AI
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコアリング）
  - レジーム検出（ETF MA200 乖離 + マクロニュースの LLM 判定）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- 設定管理
  - Settings（.env / .env.local の自動ロード、環境変数のラップ）
  - 環境に応じた挙動（KABUSYS_ENV: development / paper_trading / live）

---

## 必要条件

- Python 3.10+
- SQLite（標準ライブラリ）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- ネットワーク（LINE / ブローカー / OpenAI を使う場合）

pip インストール例:
```
pip install duckdb psutil requests openai streamlit
```
（プロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作る・有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成（ルートの .env または .env.local）
   - Settings モジュールはプロジェクトルート（.git / pyproject.toml）を基に自動で .env をロードします。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH, KILL_FLAG_PATH 等のパス設定
   - LOG_LEVEL（DEBUG/INFO/…）
6. 必要ならデータディレクトリを作成:
```
mkdir -p data
```

---

## 使い方

- ExecutionEngine を起動（本番は KABUSYS_ENV=live、検証は paper_trading）
```
# デフォルト: KABUSYS_ENV=development
python -m kabusys.run_execution

# Paper Trading
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- Monitoring（監視ループ）を起動
```
# ポーリング間隔は env MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
python -m kabusys.run_monitoring
```
- Streamlit ダッシュボードを起動（監視 DB の読み取り専用で開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- AI モジュール（プログラム的に呼び出す）
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（引数で上書き可能）。呼び出しは DuckDB 接続を渡してください。

注意点:
- run_execution は起動時にプロセス優先度を "high" に設定し、実行中は PID ファイルを生成／使用します（Settings.pid_file_path）。
- run_monitoring は常に本番の sqlite_path を使って監視ログを書き込みます（KABUSYS_ENV に依存せず本番 DB を参照する仕様）。
- Paper Trading モードではブローカークライアントはモック実装が使われ、paper_trading 用 DB（data/paper_trading.db）へ記録され、本番 DB と分離されます。

環境変数の注意:
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。1 以上の整数を指定。0 以下や不正値はデフォルト 60 秒にフォールバック。
- KILL_FLAG_*: KillSwitch が data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillFlag の自動クリアは Settings.kill_flag_clear_on_start で制御できます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py (プロジェクト情報)
  - config.py (Settings, .env 自動ロード)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...（注文実行周り）
  - monitoring/
    - monitoring_db.py (SQLite スキーマ + 永続化 API)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - research/
    - factor_research.py (momentum / volatility / value)
    - feature_exploration.py (forward returns / IC / summary)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (マクロ + ETF MA200 でレジーム判定)
  - data/ (想定: DuckDB / SQLite のファイル置き場、例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - utils/
    - process_priority.py (プロセス優先度・CPU affinity 設定ユーティリティ)

---

## データベース & ファイル

- DuckDB: prices_daily / raw_financials / raw_news / ai_scores / market_regime などの大規模分析データを収める（設定: DUCKDB_PATH, デフォルト data/kabusys.duckdb）。
- SQLite (監視): monitoring 用の永続化（system_status / trade_logs / positions / risk_logs / dashboard）。Settings.sqlite_path（data/monitoring.db がデフォルト）。
- Paper Trading 用 SQLite: KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して実取引 DB と分離。
- PID ファイル / kill.flag: Settings.pid_file_path, Settings.kill_flag_path（デフォルト data/execution.pid, data/kill.flag）

MonitoringDB は init_monitoring_db() で必要なテーブルとインデックスを冪等に作成します（既存 DB に対するマイグレーションも一部含む）。

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV を適切に設定する（paper_trading / live）:
  - paper_trading: 実際のブローカー接続は行わずモック挙動で検証。専用 DB に記録されます。
  - live: 実ブローカー接続、API 資格情報を必ず保護して設定してください。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須。これが無い場合は該当機能は動作しません（例外やフォールバック挙動あり）。
- MONITOR_POLL_INTERVAL は監視ループの負荷と検知遅延のトレードオフに注意（デフォルト 60 秒）。
- プロセス優先度の設定は OS 権限に依存するため失敗する可能性があり、その場合は警告ログに留まります。
- KillSwitch による停止はファイル存在チェックで行われるため、手動で kill.flag を作成すると ExecutionEngine が停止対象になります。逆に start 時に古い kill.flag が残っていると意図せず停止するため、必要であれば Settings.kill_flag_clear_on_start を有効にして起動時にクリアしてください。
- LINE 通知は設定漏れ時にログのみでスキップされます。通知のクールダウン管理があるため短時間で同一種の通知が多数送られることは抑制されます。

---

## トラブルシューティング

- .env が読み込まれない／別の .env を使いたい
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にし、必要な環境変数を明示的にセットしてください。
- Monitoring が走らない / データが記録されない
  - run_monitoring を起動したプロセスのログに警告がないか確認。MONITOR_POLL_INTERVAL の値や DB ファイルパス（書き込み権限）を確認してください。
- OpenAI 呼び出しでエラー
  - API キー、ネットワーク、レート制限。モジュール側でリトライ・フォールバック処理がありますが、継続的に失敗する場合はキー・ネットワークを確認してください。
- Streamlit で DB を開けない
  - DB のパスを確認。monitoring ダッシュボードは read-only URI を使って開くため、既存プロセスが DB をロックしていても読めるように工夫していますが、URI 作成やファイル権限に依存します。

---

以上がこのコードベースの概要と利用方法です。運用や拡張（ブローカープラグイン追加、戦略モジュール接続、DuckDB データ投入など）に関する具体的な質問があれば追加で案内します。