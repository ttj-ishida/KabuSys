# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群です。本リポジトリは以下を含みます: 発注実行エンジン起動スクリプト、監視（Monitoring）周りのコンポーネント、ポートフォリオ構築の純粋関数群、リサーチ用ファクター計算、ニュース NLP / レジーム判定の AI モジュール、ユーティリティ類、および各種 CLI（.env ウィザード・設定検証・検証レポート生成）など。

注意: この README はソースコード（src/kabusys 下）に基づいて作成しています。実運用では .env に機密情報が含まれるため Git にコミットしないでください。

---
目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（重要 / よく使うもの）
- 停止・Kill Switch の運用
- ディレクトリ構成（主要ファイル）
- 備考 / トラブルシューティング

---

プロジェクト概要
- KabuSys は日本株自動売買システムのライブラリ群です。発注ロジックのエンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュース NLP を使った AI スコアリング、レジーム判定などを含みます。
- 設定は .env ファイルや環境変数で行います。config モジュールから Settings クラス経由でアクセスします。
- Paper trading（模擬発注）モードをサポートし、本番 DB と分離して記録できます。

主な機能一覧
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視を実装
- Monitoring 起動スクリプト（run_monitoring.py）
  - システム状態・データ鮮度・取引ログ・リスク（ドローダウン等）などの定期ポーリングと永続化
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視は本番データを参照）
- Monitoring 永続化レイヤ（monitoring_db.py）
  - system_status、trade_logs、positions、risk_logs、dashboard テーブルを持つ SQLite スキーマ
  - マイグレーション処理も含む
- Kill Switch（kill_switch.py）
  - 条件（ドローダウン、ポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
- MonitoringEngine（monitoring_engine.py）
  - 各 Monitor（SystemMonitor、TradeMonitor、RiskMonitor）を束ねてアラート送信や Kill Switch 評価を実施
- Portfolio（portfolio/*.py）
  - 候補選定、等金額／スコア加重の重み計算、セクター制限、ポジションサイズ計算（単元株丸め、リスクベース配分など）
  - すべて純粋関数（DB 参照なし）
- Research（research/*.py）
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、IC（Information Coefficient）計算、統計サマリーなど
- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI API（gpt-4o-mini 等）を使ってニュースのセンチメントを銘柄ごとにスコア化 / マクロセンチメントを算出して市場レジーム判定へ利用
  - レート制限・ネットワーク断・5xx を考慮したリトライ・フォールバック設計
- CLI 支援ツール
  - 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式に生成）
  - 設定検証: python -m kabusys.validate_config（.env と config/*.yaml を検査）
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順（最小）
1. Python 仮想環境を作成・有効化
   - 推奨: Python 3.9+（コードスタイルから推測。プロジェクト要件に合わせてください）

2. 必要パッケージをインストール
   - 最低依存例:
     pip install duckdb psutil openai
   - オプション（YAML 検証など）:
     pip install PyYAML
   - （実際の requirements.txt がある場合はそれを利用してください）

3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードを使わない場合は .env.example を参考に .env を作成して環境変数を設定してください
   - 重要: .env を Git にコミットしないでください

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も FAIL 扱いになります

使い方（主要コマンド）
- Execution（注文エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）
    - 停止: data/stop_requested.flag を作成すると起動中ループが検知して停止します

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。1 未満の値は無視されデフォルトにフォールバック
  - Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依存せず）

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 結果がエラーの場合は exit(1) します。--strict を付けると警告も失敗扱いになります

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

- AI / レジーム判定（ライブラリ関数として利用）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - どちらも OpenAI の API キーが必要（引数で渡すか OPENAI_API_KEY 環境変数をセット）

環境変数（重要なもの）
- 必須（validate_config でチェックされる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用周り（主なもの）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper trading 専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper trading 時の成行/部分約定挙動（instant|partial|never|reject）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（1 = 自動クリア、推奨は 0）

停止・Kill Switch の運用
- Stop フラグ（外部からループ停止）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループは次回サイクルで検知して終了します
- Kill Switch（強制停止のための安全弁）
  - Monitoring 内で条件（ドローダウン超過やポジション上限超過）を満たすと data/kill.flag を作成します
  - ExecutionEngine は起動時・運用中に kill.flag の存在を参照して停止する設計
  - Settings.kill_flag_clear_on_start = 1 にすると起動時に kill.flag を自動でクリアします（本番では推奨しません）

ログ
- kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しています
- デフォルトログディレクトリ: logs/
- 日次ローテーション（TimedRotatingFileHandler、30日分保存）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（ファクトリ / engine / order_manager 等）※詳細は各ファイル
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

備考 / トラブルシューティング
- DuckDB / psutil / openai がインストールされているかを確認してください。PyYAML は validate_config の YAML 検証時に使われます（未インストール時は YAML 内容検証をスキップします）。
- Monitoring は「監視対象として本番の monitoring DB を参照する」設計になっています。監視設定を変える場合は Settings を確認してください。
- run_monitoring の MONITOR_POLL_INTERVAL は整数秒を想定しています。0・負値・非数は無視され、デフォルト（60 秒）にフォールバックします。
- Paper trading と本番の DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）。Paper trading を使うときは環境変数を正しく設定してください。
- .env の自動読み込みは config.py がプロジェクトルート（.git か pyproject.toml）を見つけられる場合に動作します。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にしてください。

最後に
- この README はコードベースの主要な使い方と構成をまとめたものです。実運用時は各コンポーネント（ExecutionEngine、BrokerClient、戦略ロジック、運用手順）を十分にテスト・レビューしてください。

質問や、README に追加したい具体的な使用例（.env のサンプル、起動スクリプトの systemd ユニット例、Docker 化など）があれば教えてください。必要に応じて追記します。