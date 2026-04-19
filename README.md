README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の Python パッケージです。本コードベースは以下の主要機能で構成されています。

- 発注／実行エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- ファクター計算・リサーチ（research）
- ニュース NLP / レジーム判定（AI モジュール）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

設計思想のポイント
- Paper Trading（検証）と Live（本番）で DB を分離して安全性を確保
- DuckDB を用いた分析用データレイヤ、SQLite を監視・発注ログ用に使用
- OpenAI を使ったニュースセンチメント/レジーム判定は外部 API をオプションとして利用
- `.env` を用いた環境変数管理をサポート（interactive ウィザードあり）
- ログは stdout と日次ローテートされるファイルの二重出力

主な機能一覧
----------------
- run_execution: 発注エンジンの起動／実行（KABUSYS_ENV に応じて paper_trading 用 MockBroker を使用）
- run_monitoring: System / Trade / Risk 各モニタのポーリング監視ループ
- config_setup: 対話式で .env を作成／更新するウィザード
- validate_config: .env と config/*.yaml の基本チェックツール（--strict オプションあり）
- tools.paper_verification_report: Paper Trading 結果の検証レポート生成
- portfolio: 候補選定、重み計算、位置サイズ計算、セクターキャップ、レジーム乗数
- research: ファクター計算（momentum/volatility/value）、将来リターン、IC 計算など
- ai.news_nlp / ai.regime_detector: ニュースを LLM でスコアリングし ai_scores / market_regime テーブルに書込む
- utils: ロギングセットアップ、プロセス優先度・CPU affinity 設定など
- monitoring: system_monitor, trade_monitor, risk_monitor, kill_switch, alert_manager, monitoring_engine, persistent DB（SQLite）ラッパー

セットアップ手順（ローカル）
-------------------------
前提: Python 3.10+ を推奨（typing の | 演算子などを使用）

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 主要パッケージ:
     - duckdb
     - psutil
     - openai（AI モジュールを使う場合）
     - pyyaml（validate_config で config YAML の検証を行う場合に必要）

   （注）requirements.txt がない場合は above を個別にインストールしてください。

4. 環境変数を準備
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または `.env` を手動作成（ルートに配置）。よく使う環境変数例:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意。アラート用）

5. 設定の妥当性チェック（実行前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると warning もエラー扱いになり exit(1)

使い方（起動 / 運用）
--------------------
基本は複数プロセスで動かします。主に ExecutionEngine（発注）と Monitoring（監視）を別プロセスで起動します。

1. ExecutionEngine 起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録します（本番 DB と分離）。
     - 起動時に data/execution.pid（デフォルト）へ PID を書きます。
     - data/stop_requested.flag が存在する場合は起動を中止します。

2. Monitoring 起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - Settings に基づき SQLite（監視 DB）と DuckDB に接続して SystemMonitor のポーリングループを実行します。
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは常に本番側に記録）。

3. Kill Switch / ディスク上のフラグ
   - モニタリング中に KillSwitch が条件を満たすと data/kill.flag が作成され、ExecutionEngine の停止トリガーになります。
   - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットすると起動時に clear されます（本番では 0 を推奨）。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB パスを指定できます。
   - 返す指標: 稼働率、注文成功率、送信率、レイテンシ（P95）など。閾値に基づき PASS/FAIL を判定します。

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行モード。development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

ロギング
-------
- 共通ユーティリティ kabusys.utils.logging_setup を使用してログを設定します。
- 出力先:
  - コンソール (stdout)
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト）。LOG_DIR 環境変数または引数で変更可。
- ログレベルは LOG_LEVEL 環境変数で制御します。

AI（OpenAI）関連
----------------
- ai.news_nlp、ai.regime_detector は OpenAI を用いてニュースセンチメントやマクロセンチメントを算出します。
- 実行には OPENAI_API_KEY が必要です。API の失敗に対してはフェイルセーフ（0 相当の中立値）で継続する設計です。
- レスポンスの検証・リトライ・バッチ処理など堅牢性に配慮された実装になっています。

ディレクトリ構成（主要ファイル）
--------------------------------
（パッケージルート: src/kabusys/ 以下を想定）

- kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings 定義（.env 自動ロード機能含む）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py           — ニュースを LLM でスコアリングして ai_scores に書込む
    - regime_detector.py    — マクロ + ma200 で市場レジーム判定
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ初期化 + ラッパークラス
    - system_monitor.py     — システム／データ鮮度監視
    - trade_monitor.py      — 発注ログ監視（stale orders / anomaly など）
    - risk_monitor.py       — ドローダウン／ポジション上限監視
    - kill_switch.py        — kill.flag の作成/クリア
    - monitoring_engine.py  — 各 Monitor を束ねる実行ループ
    - alert_manager.py      — アラート送信管理（LINE など）
  - execution/              — ExecutionEngine, OrderManager, BrokerFactory 等（発注ロジック）
  - portfolio/              — portfolio_builder, position_sizing, risk_adjustment
  - research/               — factor_research, feature_exploration
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (想定: リポジトリ外でも可)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
  - config/ (YAML 設定群: system_config.yaml 等を想定)

開発／運用上の注意点
-------------------
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の取り扱いに注意してください（誤って自動クリアしないことを推奨）。
- Paper Trading と本番の SQLite は分離されています。paper_trading 起動時は常に PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI の呼び出しはレート制限や一時的なエラーに備えたリトライ実装がありますが、API キーの管理・コストに注意してください。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。権限・パスを適切に設定してください。
- SystemMonitor は PID ファイルの監視やデータ鮮度チェックを行い、異常を監視 DB に永続化します。

よく使うコマンドまとめ
--------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（例: "0.1.0"）。
- ライセンスはリポジトリの LICENSE ファイルを参照してください（存在する場合）。

フィードバック・拡張案
---------------------
- 銘柄ごとの lot_size を stocks マスタで管理して position_sizing を拡張する案がコード内でコメントされています。
- AI モジュールは JSON レスポンス検証やバッチ処理を実装済みで、モデル変更やプロンプトチューニングで精度改善できます。
- 監視／アラートの送信先（LINE 以外）を増やす場合は AlertManager を拡張してください。

以上。必要であれば README を英語版に翻訳したり、systemd 用のサービスユニットや Dockerfile のテンプレートを追加で作成できます。どの情報をさらに詳しく追加しますか？