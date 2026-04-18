# KabuSys

日本株自動売買システム（軽量プロトタイプ）  
このリポジトリは、銘柄選定・ポジションサイズ計算・発注エンジン・監視・AIベースのニュースセンチメント評価などを備えた自動売買基盤の一部実装です。

---

目次
- プロジェクト概要
- 主な機能
- 前提（Prerequisites）
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動 / 実行例）
- 重要ファイル・運用フロー
- ディレクトリ構成（抜粋）
- 開発・テストに関する補足

---

## プロジェクト概要
KabuSys は、以下のコンポーネントで構成される日本株向けの自動売買システムです。

- Strategy / Research: ファクター計算、特徴量探索、将来リターン計算
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム調整
- Execution: ブローカークライアントを通じた発注管理、リスク管理、約定ログ
- Monitoring: システム稼働監視、取引ログ監視、リスク監視、Kill Switch
- AI: OpenAI（LLM）を用いたニュースセンチメント評価・市場レジーム判定
- Tools: ペーパートレード検証レポート作成等の補助ツール

設計方針として、DuckDB（分析用）と SQLite（監視・履歴用）を併用し、本番とペーパートレードでデータベースを分離する仕組みがあります。

---

## 主な機能
- ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- ポートフォリオ候補選択および重み付け（等配分／スコア加重）
- 単元・コスト・利用可能現金を考慮したポジションサイズ計算（ロット丸め、スケーリング）
- 発注のログ保存・約定レイテンシ測定・リスクイベント記録
- System / Trade / Risk のポーリング監視とアラート（Kill Switch）
- OpenAI を用いたニュースのセンチメントスコアリング（ai_scores へ書き込み）
- Paper Trading 向けの検証レポート生成スクリプト

---

## 前提（Prerequisites）
- Python >= 3.10（typing の新構文を利用しているため）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証で使用、必須ではない）
- SQLite は標準ライブラリで使用可能

インストール例（最低限）:
pip install duckdb psutil openai pyyaml

（実際の requirements.txt がある場合はそちらを使用してください。）

---

## セットアップ手順

1. リポジトリルートに移動（パッケージは src/kabusys に存在します）

2. .env の作成（対話ウィザード）
   python -m kabusys.config_setup
   - ウィザードで必要な環境変数を対話的に設定して .env を生成します。
   - 生成された .env は Git にコミットしないでください（機密情報含む）。

3. 設定検証
   python -m kabusys.validate_config
   - オプション --strict を付けると警告も失敗扱いになります。

4. 必要なディレクトリ自動作成（ログ・データ）
   - デフォルトで以下のパスを使います。事前に作成しておくと確実です。
     - data/ (SQLite、PID、フラグファイル)
     - logs/ (ログファイル)

5. データベース
   - DuckDB（分析用）デフォルト: data/kabusys.duckdb
   - SQLite（監視 DB）デフォルト: data/monitoring.db
   - ペーパートレード時の SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合はこちらを使用）

注意: config モジュールは自動でプロジェクトルートの .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 環境変数（主なもの）

主に config_setup で設定するものを列挙します（デフォルト値があるものは併記）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN（任意, アラート用）
- LINE_USER_ID（任意）
- KILL_FLAG_CLEAR_ON_START (0/1)（本番は 0 推奨）
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")（paper_trading 動作指定）

その他、運用時に使うもの:
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）
- OPENAI_API_KEY（AI モジュールで使用）
- LOG_DIR（ログ出力先、デフォルト logs/）
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）

---

## 使い方（実行例）

### .env 作成と検証
1. 対話式で .env を作る:
   python -m kabusys.config_setup

2. 検証:
   python -m kabusys.validate_config
   # 厳密チェック:
   python -m kabusys.validate_config --strict

### ExecutionEngine（発注エンジン）起動
- 本番（KABUSYS_ENV=live）やペーパー（paper_trading）を .env で指定後に実行:
  python -m kabusys.run_execution

- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は PID を data/execution.pid に書きます

停止:
- 管理者が ExecutionEngine を停止させたい場合は Kill Switch（kill.flag）や stop flag を使う
  - KillSwitch（監視が検出して書き込む）: data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルを受けられる設計です
  - 手動で停止したい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring はこのファイルを監視して終了します）

### Monitoring（監視プロセス）起動
- 監視ループ起動:
  python -m kabusys.run_monitoring

- 特記事項:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルに記録します
  - 監視では system_status / trade_logs / risk_logs / dashboard などのテーブルを作成します（init_monitoring_db）

### Paper Trading 検証レポート
- スクリプト実行:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプションで --db に SQLite パスを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数を優先）

### AI（ニューススコアリング / レジーム判定）をプログラムで呼ぶ
- DuckDB 接続を作成して関数を呼び出す例（概念）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

- OpenAI API キーは OPENAI_API_KEY 環境変数、または関数引数で渡します。API エラー時はフェイルセーフ（スコア 0 等）で継続する設計です。

---

## 重要ファイル・運用フロー

- data/stop_requested.flag
  - run_execution.py と run_monitoring.py はこのファイルを監視し、存在すると安全に終了します。

- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine の強制停止トリガーに使われます。
  - Settings.kill_flag_clear_on_start が 1 のとき、起動時に自動クリアされる設定があるため本番での誤設定に注意してください。

- PID ファイル
  - data/execution.pid に実行プロセスの PID を書きます（run_execution）。

- ログ
  - デフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30世代保存）
  - stdout にもログが出力されます（StreamHandler）。

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（.env 自動ロード）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースセンチメント評価（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（テーブル作成/CRUD）
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — （取引監視: ファイルにあるが省略）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch ロジック
  - monitoring_engine.py   — 複数モニタを束ねるエンジン
  - alert_manager.py       — （アラート送信: ファイルにあるが省略）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定（ロット丸め・aggregate cap 等）
  - risk_adjustment.py     — セクター制約・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — IC / forward returns / summary 等
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに execution パッケージや data 関連の実装があります。）

---

## 開発・運用に関する補足
- 環境（KABUSYS_ENV）が `paper_trading` の場合、MockBrokerClient を用いるため本番ブローカーとの混同は避けられます。ペーパートレードは専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- Monitoring は監視データを常に（環境に関係なく）本番 SQLITE_PATH に書き込むようになっている点に注意してください（run_monitoring の実装上の仕様）。
- OpenAI を利用する機能は API コストが発生するため、キー管理と実行頻度に注意してください。
- config/_auto loading_: configモジュールはプロジェクトルートを `.git` または `pyproject.toml` から推定し、自動で .env を読み込みます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ロギング: setup_logging をすべての起動スクリプトで呼び出すことで統一的なログ管理を行なっています。ログディレクトリ作成に失敗するとコンソールのみで出力されます。

---

必要であれば README に含めるべきコマンド例（systemd サービス定義、Docker 化、requirements.txt の内容、サンプル .env.example）なども作成します。どの情報を追記するか教えてください。