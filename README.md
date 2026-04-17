# KabuSys — 日本株自動売買システム (README)

以下はソースツリー（src/kabusys）に基づく README です。システムの概要、機能、セットアップ方法、実行方法、主要ディレクトリ構成や重要な環境変数について日本語でまとめています。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムの骨組みです。  
主な責務は次のとおりです。
- シグナルに基づく発注・注文管理（ExecutionEngine）
- システム稼働・注文状態・リスク（ドローダウン等）の監視
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リサーチ用ファクター計算（DuckDB ベース）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- Paper Trading（モックブローカー）用の分離された DB での検証機能
- モニタリング用のストリームリットダッシュボードや検証レポート生成ツール

設計方針としては、DB（SQLite / DuckDB）を中心に、外部 API 呼び出しや副作用を局所化し、ユニットテストしやすい純粋関数群と永続化層の分離を行っています。

---

## 主な機能一覧
- Execution
  - 発注フロー管理（OrderManager, OrderRepository）
  - リコンシリエーション（再起動時の注文・ポジション整合）
  - Paper Trading 用モックブローカー（環境 `paper_trading`）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション数上限監視
  - KillSwitch: 重大条件で ExecutionEngine を停止するための flag 書き込み
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視ダッシュボード）
- Portfolio
  - 銘柄候補選定、等配分/スコア加重計算、リスク調整（セクター上限・レジーム乗数）、株数決定（単元丸め・利用可能現金反映）
- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC 計測、統計サマリー
- AI
  - raw_news の NLP スコアリング（OpenAI）
  - 市場レジーム判定（ETF ma200 とマクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件
- Python 3.10+（型注釈や match を使用している可能性があるため、3.10以上を推奨）
- SQLite（Python に標準搭載）
- 必須 Python パッケージ（一例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- ネットワークアクセス（実ブローカー・OpenAI 等を使う場合）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してインストールしてください。）

例（venv を使う場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順（概要）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くことが可能）
   - 自動で .env / .env.local が読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. データディレクトリを作成（例: data/）
6. （Paper Trading を使う場合）PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH 等を設定

重要な環境変数の例（後述のセクション参照）を .env に記載しておくと便利です。

---

## 重要な環境変数（主なもの）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）、デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 関連機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

設定ミスや未設定時は Settings クラスが ValueError を投げます（必須項目のみ）。

---

## 実行方法（主要なエントリポイント）

- ExecutionEngine（注文実行）
  - 目的: 発注エンジンを起動し、ブローカーとやり取りします。
  - 実行:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されるため本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません（停止保護）。
    - 実行中に停止させるには kill.flag を作成するか stop_requested.flag を置きます。

- Monitoring（SystemMonitor の簡易起動スクリプト）
  - 目的: SystemMonitor のポーリングループを起動して system_status 等を定期記録します。
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。監視ログは production DB に保存される仕様です。

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ただし監視 DB にアクセス可能である必要があります（読み取り専用 URI を使用）。

- Paper Trading 検証レポート
  - 目的: Paper Trading DB から指標（稼働率、注文成功率、レイテンシ等）を集計してレポートを標準出力に出す。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
    - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます。

- AI 関連（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して使います（OpenAI API キーが必要）。

---

## フラグファイル / PID ファイルについて
- data/execution.pid: ExecutionEngine が自身の PID を書き込むパス（Settings.pid_file_path）
- data/kill.flag: KillSwitch が書き込む停止フラグ（Settings.kill_flag_path）。存在すると ExecutionEngine の停止指令となります。
- data/stop_requested.flag: run_execution / run_monitoring の起動ループで使用される停止指示ファイル（スクリプト内で参照）。

これらはファイルベースの簡易なプロセス制御に使われます。clear / remove する運用に注意してください（KillSwitch.clear() 等が用意されています）。

---

## ディレクトリ構成（主要ファイル）
（プロジェクトルートに src/ を置く構成を前提）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数 / .env 自動ロード）
  - run_execution.py
  - run_monitoring.py

  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py, broker_api.py, ...（ブローカー抽象）
    - order_record.py, order_repository.py, order_*（注文周り）

  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - run_monitoring.py（ループ起動スクリプト）

  - portfolio/
    - portfolio_builder.py        — 候補選定、等重/スコア重み
    - position_sizing.py          — 株数計算、ロット丸め、集約キャップ
    - risk_adjustment.py          — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py          — momentum / volatility / value
    - feature_exploration.py      — 将来リターン / IC / 統計
    - __init__.py

  - ai/
    - news_nlp.py                 — raw_news を OpenAI で評価して ai_scores に格納
    - regime_detector.py          — マクロセンチメント＋ETF ma200 で regime 判定
    - __init__.py

  - tools/
    - paper_verification_report.py

  - data/（実行時に生成されることを想定）
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid / kill.flag / stop_requested.flag

---

## 開発メモ / 注意事項
- Paper Trading と本番データは明確に分離されるよう設計されています。KABUSYS_ENV=paper_trading を指定すると ExecutionEngine は PAPER_TRADING_SQLITE_PATH を使用しますが、Monitoring（run_monitoring）は常に sqlite_path（本番想定）を使用します。運用時に意図しない DB 上書きを避けるため注意してください。
- Settings はプロジェクトルート（.git または pyproject.toml）を自動的に探索して .env / .env.local をロードします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / CPU affinity の設定は psutil を利用しています。権限不足や未対応 OS では設定に失敗する場合があります（警告が出てスキップされます）。
- OpenAI 関連機能は API のレート制限・一時エラーに対してエクスポネンシャルバックオフでリトライしますが、API キー未設定の場合は ValueError を投げます。
- DuckDB は SQL を用いた高速な分析に利用します。prices_daily / raw_financials / raw_news 等のテーブルを前提にファクター計算や NLP ベース処理が実装されています。
- monitoring_db.init_monitoring_db はスキーマの冪等初期化＆簡易マイグレーション（カラム追加）を行います。既存 DB を壊さないように注意してください。

---

README は以上です。必要ならば次の内容も追加できます:
- 具体的な .env.example（テンプレート）
- よくあるトラブルシューティング（権限、psutil のパーミッション、DuckDB のファイルロック等）
- CI / テストの実行方法やユニットテストの記載

追記希望があれば教えてください。