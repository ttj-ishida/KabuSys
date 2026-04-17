# KabuSys

日本株向けの自動売買システムのコアライブラリ群です。シグナル生成、ポートフォリオ構築、発注エンジン、監視、研究用ユーティリティ、AI を使ったニュース評価などのコンポーネントを含みます。

## 概要
このリポジトリは以下の機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・注文調整を行う
- 監視サブシステム（MonitoringEngine）: システム/注文/リスクの定期チェックとアラート、Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定、重み算出、ポジションサイジング、セクター制約
- 研究用モジュール: ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターンやIC計算
- AI モジュール: ニュースのセンチメント評価（OpenAI）と市場レジーム判定
- 各種 CLI/ツール: 設定ウィザード、設定検証、ペーパートレード検証レポート等
- 永続化: DuckDB（分析用途） / SQLite（監視・発注履歴）

設計方針として、ルックアヘッドバイアスを避ける実装、フェイルセーフ（API失敗時のフォールバック）、および運用での堅牢性を重視しています。

## 主な機能一覧
- 環境設定ウィザード（.env の対話式生成）
- 起動前チェック（.env と config/*.yaml の検証）
- ExecutionEngine：ブローカークライアント抽象化、OrderManager / RiskManager / Reconciler の連携
- MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を定期実行しアラート・Kill Switch を管理
- Paper Trading モード（完全に本番 DB と分離された SQLite に記録）
- Paper Trading 検証レポート生成ツール（uptime / 成立率 / レイテンシ など）
- ニュース NLP（OpenAI）による銘柄単位のセンチメント付与（ai_scores テーブルへの書き込み）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ポートフォリオ構築補助（候補選定 / 重み付け / ポジションサイズ算出 / セクター制約）
- 小規模な DB マイグレーション（監視 DB のカラム追加等を自動で行う）

## 前提（要件）
- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合、任意）
- 標準ライブラリ: sqlite3 等

（プロジェクトに requirements.txt がある場合はそれを使用してください。なければ上記パッケージを個別にインストールしてください。）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows の場合: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じてプロジェクト固有の requirements をインストール）
4. .env の作成（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
     - 対話式に各種環境変数を入力して .env を生成します
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict オプションを付けると警告も失敗扱いになります
5. （オプション）パッケージとして開発インストール
   - pip install -e .

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）: 実行モード
  - paper_trading: MockBroker を使い、paper DB（デフォルト data/paper_trading.db）に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB 上書き）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア設定に注意）

## 使い方（実行例）
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は .env の KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db に記録されます
    - 起動中に data/stop_requested.flag が存在すると起動を中止・停止します
    - 実行中は data/execution.pid に PID を書きます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 指定または OPENAI_API_KEY 環境変数
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止・Kill Switch
  - 手動停止: プロセスループ（run_monitoring / run_execution）はプロジェクト配下の data/stop_requested.flag を検知すると終了します（ファイル作成で停止要求）
  - KillSwitch（自動）: リスク条件を満たした場合、Settings.kill_flag_path（デフォルト data/kill.flag）に理由を記述して ExecutionEngine に停止を促します

## 注意点 / 運用メモ
- Paper Trading モードでは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）機能を利用するには OPENAI_API_KEY の設定が必須です。API 呼び出しはリトライやフォールバックの保護がありますが、キーがないと関数は ValueError を投げます。
- 監視 DB 初期化は init_monitoring_db() により冪等に実行され、簡易マイグレーション（カラム追加）も行います。
- ログレベルは LOG_LEVEL 環境変数で制御できます。デフォルトは INFO。
- Windows / Linux のプロセス優先度の差分は内部ユーティリティで吸収していますが、OS の権限により設定に失敗する場合があります（警告ログが出ます）。

## ディレクトリ構成（主要ファイル）
以下は主要なファイル・モジュールの構成例（src/kabusys 以下）。実際のツリーはこの他に細かな実装ファイルがあります。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - config_setup.py                — .env 対話ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_monitoring.py              — 監視ループ起動スクリプト
    - run_execution.py               — 実行エンジン起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュースセンチメント（OpenAI 呼び出し）
      - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層（監視ログ）
      - monitoring_engine.py         — 各 Monitor の束ね
      - system_monitor.py            — システム・データ鮮度監視
      - trade_monitor.py             — 注文滞留・約定異常検知
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — Kill Switch（フラグ書き込み）
      - alert_manager.py             — （アラート送信管理 — 実装ファイルに詳細）
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 発注数量計算
      - risk_adjustment.py           — セクター制約・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py           — ファクター計算（momentum/value/vol）
      - feature_exploration.py       — IC, forward returns, summary
      - __init__.py
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - execution/ (発注周りの実装: BrokerFactory 等)
    - portfolio/, monitoring/ etc. （上記参照）

## サンプル .env（最小例）
以下は .env に書く代表的な項目の例です（実際は config_setup を使って生成してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

※ .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。

## 開発・テストに関する補足
- モジュールの多くは純粋関数または依存注入可能な設計になっており、ユニットテストやモックが可能です（OpenAI 呼び出しはテストで差し替える想定）。
- DuckDB 接続を引数で渡す設計のため研究用コードの単体テストが容易です。
- 設定自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

不明点や README に追加したい項目（例えば CI のセットアップ方法、より詳細なデプロイ手順、監視アラートの設定方法など）があれば教えてください。必要に応じてセクションを追加・拡張します。