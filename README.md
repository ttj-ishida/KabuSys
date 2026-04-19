# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・リサーチ基盤「KabuSys」のコア実装です。  
システム監視・発注エンジン・ポートフォリオ構築・ファクター計算・AI ニュース解析などのコンポーネントを含みます。

主な設計方針（抜粋）
- 本番/ペーパートレードを分離（paper_trading モードでは MockBrokerClient を使用し、専用の SQLite を利用）
- DuckDB を使った時系列・ファクター計算（分析用）
- SQLite を使った監視・発注ログ永続化
- OpenAI を利用したニュース NLP / レジーム判定（API キー必須）
- ログは統一的に設定（stdout + 日次ローテーションファイル）

---

## 機能一覧
- 実行エンジン起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により本番 / paper_trading を切替）
- 監視・アラート
  - run_monitoring.py：SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch 等
- 環境設定・検証
  - config_setup.py：.env を対話式に生成/更新するウィザード
  - validate_config.py：環境変数や config/*.yaml の事前チェック CLI
- リサーチ / ファクター計算
  - research.calc_momentum / calc_volatility / calc_value、feature_exploration（IC、統計）
- ポートフォリオ構築
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
- AI 関連
  - ai.news_nlp.score_news：ニュース記事から銘柄毎にセンチメントを算出（OpenAI 必須）
  - ai.regime_detector.score_regime：マクロ + ETF MA200 で市場レジームを判定
- ツール
  - tools.paper_verification_report：ペーパートレード DB から検証レポートを出力

---

## セットアップ手順（開発 / 実行環境構築）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - 例:
     $ python -m venv .venv
     $ source .venv/bin/activate  # macOS / Linux
     $ .venv\Scripts\activate     # Windows (PowerShell は別コマンド)

2. 必要なパッケージをインストール
   - 依存関係はプロジェクトの requirements.txt / pyproject.toml に記載されていることを想定します。主な必要パッケージ：
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証や YAML 生成時に任意で必要）
   - 例:
     $ pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード）
   - 初期設定を行うには:
     $ python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を環境変数に設定

4. 設定検証（起動前チェック）
   - 生成した .env と config/*.yaml をチェック:
     $ python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     $ python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要に応じて）
   - デフォルトでは `data/` 以下に DB やフラグファイルを配置します。起動時に自動作成される箇所もありますが、権限等に注意してください。

---

## 主な環境変数とデフォルト（重要なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite — デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用） — デフォルト: 60
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject） — デフォルト: instant

※ .env は絶対にリポジトリにコミットしないでください（config_setup.py も出力にその注意書きがあります）。

---

## 使い方（起動/実行例）

- ExecutionEngine（発注エンジン）を起動
  - 実行:
    $ python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - エンジンは PID ファイル（デフォルト data/execution.pid）を書きます。
    - 停止は監視側から kill.flag を書くか stop_requested.flag を置くことで行います（後述）。

- Monitoring（監視ループ）を起動
  - 実行:
    $ python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 挙動:
    - SystemMonitor（CPU/MEM/DISK・データ鮮度・PID 存在チェック）を定期実行し、SQLite（monitoring.db）へログを保存
    - KillSwitch ロジックで条件を満たすと data/kill.flag を書き、ExecutionEngine 停止を促します
    - 停止用フラグファイル data/stop_requested.flag を検出すると監視ループを終了します

- ペーパートレード検証レポートを生成
  - 実行:
    $ python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB:
    - PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必須
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

---

## ログ・プロセス管理
- ログ出力: kabusys.utils.logging_setup.setup_logging を通じて stdout と logs/<app_name>.log（デイリー・30日保持）に出力されます。
- デフォルトログディレクトリ: logs/
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び、可能な範囲でプロセス優先度を上げます（psutil を使用）。

---

## 停止・Kill Switch（安全停止）
- kill.flag（デフォルト: data/kill.flag）
  - Monitoring の KillSwitch が条件（例: ドローダウン閾値超過、ポジション上限超過）を満たすと書き込まれます。
  - ExecutionEngine は kill.flag の存在を検知して停止することを意図しています。
- stop_requested.flag（デフォルト: data/stop_requested.flag）
  - run_monitoring.py / run_execution.py の起動ループはこのファイルの存在をチェックし、存在するとループを終了（プロセス停止）します。
- 起動時の kill flag 自動クリア
  - Settings.kill_flag_clear_on_start を環境変数 KILL_FLAG_CLEAR_ON_START=1 で有効化できますが、本番 (KABUSYS_ENV=live) では危険な設定なので推奨されません。

---

## ディレクトリ構成（主要ファイル）
（この一覧は src/kabusys 以下の主要モジュールを抜粋したものです）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        (参照：trade 関連ロジック)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        (通知管理)
  - execution/                — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag / stop_requested.flag

---

## 注意事項 / 運用に関するメモ
- 本番運用時は KABUSYS_ENV=live を設定します。validate_config の警告を必ず確認してください（LINE 通知等の設定ミスは重大）。
- paper_trading モードは発注をシミュレーションしますが、挙動の差分（fill モード等）を理解してから評価してください（PAPER_FILL_MODE）。
- OpenAI を利用する処理は API コストと遅延を伴います。rate limit やエラー時は実装がリトライとフォールバックを行う設計ですが、運用での監視が必要です。
- DB のバックアップ・ログローテーション・権限設定は運用環境に合わせて用意してください。
- .env ファイルは機密情報を含むため絶対にコミットしないでください。

---

もし README に追加したい箇所（詳細な起動オプション、各モジュールの API リファレンス、デプロイ手順、Docker サポート例など）があれば教えてください。必要に応じて追記・整形します。