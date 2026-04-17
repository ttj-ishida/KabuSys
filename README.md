# KabuSys

日本株自動売買システム（KabuSys）のリポジトリREADMEです。  
このREADMEはコードベースの主要コンポーネントの概要、セットアップ、実行方法、ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのプロトタイプです。  
主な責務は次の通りです。

- 市場データ／戦略に基づく銘柄選定とポートフォリオ構築
- 注文発行・注文状態管理・リコンシリエーション（ExecutionEngine）
- 実行ログ・監視ログの永続化 (SQLite / DuckDB)
- 稼働監視・アラート・自動停止（Kill Switch）
- Paper Trading モード（実際のブローカーと分離した検証環境）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP（OpenAI）を用いた銘柄センチメントと市場レジーム判定
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

設計方針の特徴として、DBへの書き込みは明示的で冪等性を意識した実装、外部API呼び出し系はフェイルセーフ（失敗時はスキップ・フォールバック）となっています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコンシリエーション（Reconciler）
  - Paper Trading モード（MockBrokerClient、別SQLiteファイル）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・実行プロセス確認
  - TradeMonitor：滞留注文、約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：重大リスクの際に停止フラグを書き込み ExecutionEngine を停止
  - AlertManager：LINE Push を使った通知（クールダウン対応）
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索・IC計算などのユーティリティ
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限等）
- AI
  - news_nlp: OpenAI を使った記事センチメント → ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 要件（概略）

- Python 3.9+
- ライブラリ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード起動時）
- SQLite（標準ライブラリで利用）
- ネットワーク（OpenAI / LINE API を使う場合）

実際の依存関係はプロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする
2. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限:
     - pip install duckdb psutil requests openai streamlit
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込みます（OS環境変数が優先）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

サンプル（.env に書く例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO
- PAPER_FILL_MODE=instant  # instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

注意: `.env.example` をプロジェクトに置いている場合はそれを参考にしてください。

---

## 実行方法（主要コンポーネント）

実行はパッケージモジュールとして行います。プロジェクトルートで以下コマンドを実行してください。

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 補足:
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に関係なく）。
    - 停止フラグ: data/stop_requested.flag を監視して存在すればループを抜けます。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録します。本番 DB と完全に分離されます。
    - 実行時プロセスは data/execution.pid に PID を書きます。停止は data/stop_requested.flag によるシグナルで行います。
    - 実行開始前に settings.kill_flag_clear_on_start が真であれば kill.flag をクリアできます（設定に依存）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - またはダッシュボード起動後に左上で Refresh ボタンを押して手動更新が可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュールの利用（プログラムから）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続（raw_news / news_symbols / ai_scores を参照）
    - api_key が None の場合は OPENAI_API_KEY 環境変数を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 設定と環境変数（主なもの）

- KABUSYS_ENV: environment（development | paper_trading | live）、デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH: Settings で参照されるパス

Settings モジュールは `.env` / `.env.local` をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用メモ / フラグ類

- stop_requested.flag
  - パス: project_root/data/stop_requested.flag（run_monitoring と run_execution が参照）
  - 存在すると監視／実行ループが停止して終了します。外部の運用ツールから停止を指示するために使用します。

- kill.flag
  - パス: Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch が重大リスクを検出した際に書き込みます。ExecutionEngine の起動時に検出されると起動を抑止する運用が可能です。
  - KillSwitch は冪等にファイルを書きます（既存なら上書きしない）。

- PID ファイル
  - 実行時に data/execution.pid に PID を書きます。SystemMonitor は PID ファイルを見て実プロセスの存在確認を行い、古い（stale）PID ファイルを検出したら削除して記録します。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル／インデックス作成を行い、既存 DB に対して必要なカラム追加等の簡易マイグレーションを行います（例: dashboard.peak_value、trade_logs.latency_ms）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 監視ログ層（init / MonitoringDB）
    - monitoring_engine.py         — 複数 Monitor を束ねるエンジン
    - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py             — 滞留注文・価格異常検出
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — 停止フラグ制御
    - alert_manager.py             — LINE Push 通知
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... (その他注文関連)
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み付け
    - risk_adjustment.py           — セクター上限 / レジーム乗数
    - position_sizing.py           — 株数決定・スケーリング・単元丸め
  - research/
    - factor_research.py           — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI）→ ai_scores 書込
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - process_priority.py          — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/                           — 実行時に利用するファイル（DB / flags / pid 等）

---

## 開発メモ / 注意点

- Paper Trading と Live の DB は分離されています。paper_trading モードは `settings.is_paper` 判定で専用 sqlite を使用するため、本番 DB を上書きする心配はありません。
- AI 機能（news_nlp / regime_detector）は OpenAI API を利用します。API キーがない場合は ValueError を送出するか、内部でフォールバック（macro sentiment = 0）する箇所があります。API エラーはリトライ・フェイルセーフになっています。
- プロセス優先度は set_process_priority("high") 等で起動時に設定します。権限不足等で失敗する場合は警告が出てスキップされます。
- .env のパースは堅牢化されており、クォート・エスケープ・インラインコメント等を考慮します。プロジェクトルートは .git または pyproject.toml によって自動検出されます。
- MonitoringEngine.run は例外を捕捉してループ継続する設計です。テスト用に run_once で 1 回だけ実行することもできます。

---

## トラブルシューティング

- Execution が起動しない
  - data/kill.flag が存在すると起動を抑止する場合があります。必要に応じて削除してください（KillSwitch.clear を使うか手動で削除）。
  - data/execution.pid が残っていてプロセスが存在しない場合、SystemMonitor が stale PID を検出して削除します。実行開始前に削除しておくことも可能です。

- Streamlit で DB を読み込めない
  - Dashboad は監視 DB を読み取り専用で開きます。ファイルパスやパーミッションを確認してください。
  - 例: streamlit run ... -- --db data/monitoring.db

- OpenAI 呼び出しが頻繁に失敗する
  - OPENAI_API_KEY が正しいか確認してください。RateLimitError 等は指数バックオフで再試行されますが、連続で失敗すると処理がスキップされます。

---

README は以上です。詳しい実装や API の挙動はソースコードの docstring と関数コメントを参照してください。必要なら各モジュールごとの詳細な開発ドキュメントも作成できます。