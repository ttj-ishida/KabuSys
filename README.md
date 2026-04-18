# KabuSys

日本株自動売買システムのライブラリ/実行スクリプト群。  
このリポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュースセンチメントやレジーム判定、ユーティリティ類を含みます。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化したシステムです。

- 実行エンジン（ExecutionEngine）: 発注管理、リスク管理、約定管理を行う。
- 監視（Monitoring）: システム状態、注文ログ、リスク指標をポーリングして永続化し、アラート/Kill Switch を管理。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限等。
- リサーチ: ファクター計算（モメンタム・バリュー・ボラティリティ）、IC 計算、将来リターン計算。
- AI モジュール: ニュースの NLP によるセンチメント算出（OpenAI 使用）、市場レジーム判定。
- ツール類: Paper Trading の検証レポート生成、設定ウィザード、設定検証 CLI 等。
- 永続化: DuckDB（分析用）と SQLite（監視・発注ログ）を併用。

設計上、AI / リサーチ / ポートフォリオ関連は本番発注コードと分離されており、Paper Trading 用の専用 DB を使って本番 DB と切り離した検証を行えます。

---

## 主な機能一覧（Features）

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker を使い分け）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連
  - config_setup: .env を対話的に作成/更新するウィザード
  - validate_config: .env と config/*.yaml の整合性チェック CLI
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - KillSwitch（条件に応じた kill.flag の書き込み）
  - MonitoringDB：SQLite に監視ログを永続化する抽象層
- ポートフォリオ
  - 候補選定・スコア重み・等配分・リスクベース配分
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケール調整）
- リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（OpenAI）
  - ニュースのセンチメントスコア化（ai_scores への書き込み）
  - マクロニュース + ETF MA による市場レジーム判定（market_regime テーブル）
  - 再試行・バックオフ、レスポンス検証、安全フォールバック実装
- ツール
  - paper_verification_report: Paper Trading DB（デフォルト data/paper_trading.db）から稼働率・成功率・レイテンシ等の検証レポートを生成

---

## セットアップ手順（Setup）

前提: Python 3.10+（typing における | 記法を使用しているため）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell/cmd)

3. 依存パッケージをインストール  
   requirements ファイルが無い場合は最低限以下をインストールしてください：
   pip install duckdb psutil openai

   - 任意: PyYAML（config/*.yaml の内容検証を行う場合）
     pip install pyyaml

   実際の運用ではプロジェクトに requirements.txt または poetry/pyproject 管理がある想定です。

4. 環境変数の設定（.env を作成）
   対話式ウィザードで .env を作成できます:
   python -m kabusys.config_setup

   または .env.example を参照して .env を作成してください。

5. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   警告を厳密に FAIL とする場合:
   python -m kabusys.validate_config --strict

6. データディレクトリ（logs, data など）が自動で作成されますが、権限が必要な場合は事前に用意してください。

---

## 主要な環境変数（抜粋）

- 必須（実行時に必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境 / DB
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
    - paper_trading の場合、MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH に保存
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジンの PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch フラグファイル（default: data/kill.flag）

- ログ / 実行設定
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログファイル保存ディレクトリ（default: logs/）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔秒（default: 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

- Paper Trading 固有
  - PAPER_FILL_MODE: MockBroker の fill モード（instant/partial/never/reject）

- AI（OpenAI）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）

---

## 使い方（Usage）

### 1) .env の作成
対話式で作成:
python -m kabusys.config_setup

作成後、設定を検証:
python -m kabusys.validate_config

### 2) 監視プロセスを起動
MONITOR_POLL_INTERVAL で間隔を変更可能（秒）:
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring

監視プロセスはプロジェクトルートの data/stop_requested.flag が作成されるとポーリングループを終了します。

### 3) 実行エンジンを起動（Execution）
KABUSYS_ENV によって挙動が変わります（paper_trading では MockBroker を使用）。
python -m kabusys.run_execution

停止方法:
- data/stop_requested.flag を作成すると起動中のエンジンが終了処理を行います。
- KillSwitch（監視からの判定）で data/kill.flag が書き込まれると ExecutionEngine は停止されます。

### 4) Paper Trading 検証レポート
データベースパスを指定して期間を指定して出力できます。
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
オプション: --db PATH を使って DB を指定（PAPER_TRADING_SQLITE_PATH 環境変数でも可）。

### 5) AI / レジーム判定をプログラムから呼ぶ例
（DuckDB 接続を作り、関数を呼び出す）
from datetime import date
import duckdb
from kabusys.ai import score_news  # または kabusys.ai.regime_detector.score_regime

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
print(f"written: {n_written}")

注意: OPENAI_API_KEY を .env に入れておくか api_key 引数で渡してください。

---

## 停止・Kill フラグの仕組み

- run_monitoring.py / run_execution.py はプロジェクトルートの data/stop_requested.flag を監視し、存在する場合は安全に終了します。
- KillSwitch（monitoring/kill_switch.py）は条件（ドローダウン超過など）で data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag の存在を検出して停止します。
- Execution の PID ファイルは data/execution.pid に書き出されます（起動管理や監視で利用）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート CLI
- utils/
  - logging_setup.py             — ロギング設定ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py             — SQLite 永続化レイヤ
  - monitoring_engine.py         — Monitor 統合ループ
  - system_monitor.py            — システム状態監視
  - risk_monitor.py              — ドローダウン・ポジション監視
  - kill_switch.py               — KillSwitch 実装
  - (trade_monitor 等...)
- execution/                      — 発注エンジン関連（OrderManager, BrokerFactory, ExecutionEngine等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し
  - regime_detector.py           — 市場レジーム判定
- data/ (runtime)
  - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid
- logs/ (ログ保存先)

（実際のファイルは src/kabusys 以下に展開されています）

---

## 注意事項 / 運用メモ

- KABUSYS_ENV が `live` の場合は本番運用です。LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。
- Paper Trading は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH を利用します。paper_trading に切り替えても本番 DB を上書きしない設計です。
- OpenAI を使う機能は API 呼び出し失敗時に安全なフォールバック（スコア 0.0 等）を行うよう実装されていますが、APIキーの管理・コスト・レイテンシには十分注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。権限やディスク空き容量に注意してください。
- .env は機密情報を含むため、絶対にコミットしないでください（config_setup.py の冒頭にも注意書きあり）。

---

## 連絡先 / 貢献

バグ報告や改善提案は issue を作成してください。機能拡張やドキュメント改善への PR は歓迎します。

---

この README はコードベースの現状（主要ファイルの実装）に基づいて作成しています。実運用時はプロジェクト固有の README / CONTRIBUTING / deployment 手順に従ってください。