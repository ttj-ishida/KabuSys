README
======

概要
----
KabuSys は日本株向けの自動売買・調査基盤の骨組みを提供するプロジェクトです。
主要機能は戦略に基づくポートフォリオ構築、発注実行（paper / live 切替対応）、監視・アラート、研究用ファクター計算、ニュースの NLP スコアリングなどを含みます。モジュールは小さな責務に分かれており、テストしやすく、運用での安全性（Kill Switch、監視、ログ回転など）を重視した設計です。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV によるモード切替: development / paper_trading / live
  - paper_trading モードは MockBroker を利用し、paper_trading 用 DB に記録して本番 DB と完全分離
  - リスク管理、注文管理、約定リコンシリエーションなどの仕組みを備える

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - システム稼働率、データ鮮度、滞留注文、ドローダウンなどを監視し、必要時に kill.flag を書き込む Kill Switch を持つ
  - MONITOR_POLL_INTERVAL によるポーリング間隔の調整（デフォルト 60 秒）

- Research / Portfolio
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - ポートフォリオ候補選定、等配分/スコア配分、リスク調整、単元株丸めを行う純粋関数群

- AI（OpenAI 統合）
  - ニュース記事を GPT 系モデルでセンチメント分析し ai_scores に格納
  - マクロニュースを用いた市場レジーム判定（bull / neutral / bear）
  - OpenAI API のエラー時はフェイルセーフで継続（デフォルトで 0.0 にフォールバック等）

- 運用補助ツール
  - .env ウィザード（config_setup.py）で対話式に環境変数ファイルを作成
  - validate_config で起動前に設定の妥当性チェック
  - paper_verification_report によるペーパートレードの検証レポート生成

セットアップ手順
---------------
前提
- Python 3.10 以上（Union types の | を使用）
- SQLite（標準ライブラリ）および DuckDB（Python パッケージ）
- ネットワークアクセスが必要な機能（OpenAI, kabuステーション 等）を使う場合は各種 API キーが必要

1. 依存パッケージのインストール（例）
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - pip を使う例:
     pip install duckdb psutil openai pyyaml

2. プロジェクトルートに移動（.env 自動読込機能はプロジェクトルートを .git または pyproject.toml で判定します）

3. .env の初期作成
   - 対話式ウィザードを実行して .env を作成:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - .env は絶対に Git にコミットしないこと

4. 設定検証（任意）
   - 起動前に設定を検証:
     python -m kabusys.validate_config
   - 警告を FAIL としたい場合:
     python -m kabusys.validate_config --strict

5. （AI 機能を使う場合）OpenAI API キー
   - 環境変数 OPENAI_API_KEY を設定
   - news_nlp / regime_detector は API キーが必須（未設定時は ValueError となる）

6. ログディレクトリ
   - デフォルトで logs/ にアプリ別ログ（execution.log / monitoring.log など）を出力する
   - LOG_DIR 環境変数で変更可能
   - 日次ローテーション（30 日分保持）

主要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能で必要）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 SQLite、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

使い方（起動・ツール）
--------------------
主要スクリプトはモジュールとして起動できます。

- ExecutionEngine の起動
  - 本番/ペーパー/開発モードは KABUSYS_ENV で切替
  - 実行:
    python -m kabusys.run_execution
  - paper_trading モードのとき、MockBroker を使用して PAPER_TRADING_SQLITE_PATH に記録します。
  - 実行中は data/execution.pid（デフォルト）が作成され、停止シグナルは data/stop_requested.flag で与えることができます（スクリプトは起動時に stop flag を検知したら起動を中止します）。

- Monitoring の起動
  - 実行:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は Settings.sqlite_path を常に使用（monitoring は環境にかかわらず production sqlite_path を参照）

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH （PAPER_TRADING_SQLITE_PATH の代替）

停止 / Kill
-----------
- run_execution / run_monitoring スクリプトはプロジェクト data ディレクトリ内の stop_requested.flag を見てループを終了します。
  - 停止させたい場合は data/stop_requested.flag を作成してください（任意の内容を含めてよい）
- Kill Switch（実行中の自動停止トリガ）
  - リスク条件（ドローダウン閾値やポジション上限超過等）を満たすと monitoring 側が Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます
  - ExecutionEngine は起動時に kill.flag の存在を検査し、必要に応じて起動を抑止できる設計です
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で消去します（本番では 0 を推奨）

ログ
----
- 共通のログ設定ユーティリティ setup_logging を利用し、コンソール（stdout）とファイル（日次ローテーション）に出力します。
- デフォルトのログディレクトリ: logs/
- アプリ別ファイル: logs/execution.log, logs/monitoring.log など
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI

  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py       — 統一的なロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

  - execution/               — 発注関連（Engine、BrokerFactory、OrderManager 等）
    (※詳細は実装ファイル群)

  - monitoring/
    - monitoring_db.py       — 監視 DB のスキーマ・永続化層
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 注文関連の監視（滞留注文など）※実装参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 個別 Monitor を束ねる

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py     — momentum/value/volatility 等の DuckDB ベース計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングするロジック
    - regime_detector.py     — マクロ + MA200 を用いたレジーム判定

  - tools/
    - paper_verification_report.py — ペーパー取引の検証レポート生成

運用上の注意
-------------
- KABUSYS_ENV=live の場合は実際に発注が行われます。十分に検証を行い、必須環境変数（特に API キー類）や LINE 通知設定を確認してください。
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- デフォルトの DB / log ディレクトリ（data/, logs/）が作成されていることを確認してください。プログラムは起動時に自動作成を試みますが、権限エラー等で失敗する場合があります。
- OpenAI API を使う機能はネットワーク／コストが発生します。レート制限やエラーに対する扱いは実装済みですが、運用方針は別途検討してください。

補足（開発者向け）
------------------
- Settings クラスは .env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- Monitoring は監視用 SQLite（Settings.sqlite_path）を使用します。Execution は paper_trading モード時に別 SQLite（paper_sqlite_path）を使って本番データと分離します
- ロギングは setup_logging で統一しているため、すべての起動スクリプトはこれを最初に呼び出してください
- psutil を使ってプロセス優先度や CPU affinity を設定していますが、権限のない環境では警告を出してスキップされます

以上。プロジェクトの各モジュールやスクリプトの詳細な使い方・引数・内部ロジックについては該当ファイルの docstring / コメントを参照してください。