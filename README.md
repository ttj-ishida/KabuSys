KabuSys — 日本株自動売買システム（簡易ドキュメント）
概要
このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。
主な目的は以下です。
- 売買戦略の研究（ファクター計算 / 特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 実行エンジン（ブローカーラッパ、発注管理、リコンシリエーション）
- 監視機構（システム稼働・注文監視・リスク監視・アラート）
- AI モジュール（ニュース NLP によるセンチメント評価・市場レジーム判定）
- 開発用 / 検証用ツール（Paper Trading レポート等）

特徴（主な機能）
- research: DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）および IC / サマリー計算
- portfolio: 候補選定、等金額・スコア加重の重み計算、リスク調整（セクター上限、レジーム乗数）、株数計算（単元丸め・集約キャップ）
- execution: ブローカーファクトリ、OrderManager / Reconciler による起動時リコンシリエーション、注文状態管理
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor のポーリング、MonitoringDB（SQLite）での永続化、LINE によるアラート、kill.flag による外部停止信号
- ai: OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価および市場レジーム判定（API キー必須）
- tools: Paper Trading の検証レポート出力スクリプト（kabusys.tools.paper_verification_report）
- 開発向けの Streamlit ダッシュボード（監視データの可視化）

必要条件（主要ライブラリ）
- Python 3.10+
- duckdb
- psutil
- openai
- streamlit (ダッシュボード利用時)
- requests

（推奨インストール例）
pip install duckdb psutil openai streamlit requests

設定・環境変数
このプロジェクトは .env / .env.local を自動読み込みします（ただし OS 環境変数が優先）。
自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時必須）
- PAPER_FILL_MODE: Paper Trading の約定モード（"instant"|"partial"|"never"|"reject"、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を削除するか（"1" で有効）
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時はログのみ）

セットアップ手順（開発用）
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   pip install duckdb psutil openai streamlit requests
4. 必要な環境変数を .env または .env.local に記載（.env.example を参考に作成してください）
   例（最低限）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     KABUSYS_ENV=development
     OPENAI_API_KEY=...
5. デフォルト DB フォルダを作成
   mkdir -p data

使い方（主要コマンド）
- 監視ループ起動（Monitoring）
  MONITOR_POLL_INTERVAL を秒で指定してオーバーライドできます（省略時 60）
  python -m kabusys.run_monitoring
  （または：python src/kabusys/run_monitoring.py）
  監視は常に本番用の sqlite_path（settings.sqlite_path）を使用します。

- 実行エンジン起動（Execution Engine）
  KABUSYS_ENV=paper_trading にすると MockBrokerClient が使用され、DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に分離されます。
  python -m kabusys.run_execution
  （または：python src/kabusys/run_execution.py）

- Streamlit ダッシュボード（監視データ参照）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション例:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）

- AI モジュール（ニュース NLP / レジーム判定）
  - ai.score_news / ai.regime_detector.score_regime を呼び出して使用
  - OPENAI_API_KEY が必要です。API 呼び出しは gpt-4o-mini を想定しています。
  - 実行時は API 呼び出しのレート制御・リトライを実装済み

監視・運用に関する注意点
- kill.flag による停止
  - KillSwitch が条件に合致すると KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込み、ExecutionEngine 側で検知して停止できます。
  - 起動時に kill.flag をクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。

- PID ファイル
  - ExecutionEngine は PID ファイル（Settings.pid_file_path）を書き込みます。SystemMonitor は PID ファイルの stale を検出・除去します。

- DB の分離
  - paper_trading 環境時は紙トレード用の SQLite に完全分離して記録します（実際の送受信や残高はモック）。

ディレクトリ構成（主なファイル・フォルダ）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理（.env 自動読み込み）
    - utils/
      - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - research/
      - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - portfolio/
      - portfolio_builder.py    — 候補選定・重み計算
      - position_sizing.py      — 株数決定・キャップ/スケール処理
      - risk_adjustment.py      — セクター上限・レジーム乗数
    - ai/
      - news_nlp.py             — ニュースセンチメント取得（OpenAI）
      - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
    - monitoring/
      - monitoring_db.py        — SQLite スキーマ + 永続化 API
      - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
      - trade_monitor.py        — 注文滞留 / 約定異常検出
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - alert_manager.py        — LINE 通知ラッパー
      - kill_switch.py          — kill.flag の読み書きロジック
      - monitoring_engine.py    — 各モニタを束ねるエンジン
      - streamlit_dashboard.py  — Streamlit ダッシュボード（ローカル監視）
    - execution/
      - order_manager.py       — 発注フロー（注文作成・送信・状態遷移）
      - reconciler.py          — 起動時の注文/ポジション照合
      - （ほか Broker/Repository 等の実装が想定される）
    - tools/
      - paper_verification_report.py — paper_trading の検証レポート出力
- data/                           — デフォルト DB / PID / flag ファイルの格納先（実行時作成推奨）

実運用上の補足
- データ新鮮性の判定は DuckDB 内の prices_daily の最終日付を基準とします。_FRESHNESS_DAYS（デフォルト 3 日）を超える場合は警告・アラート対象になります。
- AI 関連は API 呼び出しに依存するため、API キー・レート制限・コストに留意してください。API エラー時は安全側のフォールバック処理が多数実装されています（例: macro_sentiment=0.0）。
- モジュールは外部依存を最小化する設計（DuckDB + 標準ライブラリ）を心掛けていますが、実行環境によりネイティブ依存（psutil 等）の権限エラーが発生することがあります。

ライセンス・貢献
本リポジトリのライセンス情報はプロジェクトルートの LICENSE / pyproject.toml を参照してください（無い場合は管理者に確認してください）。

以上。運用や追加の使い方（ブローカー接続設定、strategy 実装、CI テスト方法など）について追記が必要であれば教えてください。