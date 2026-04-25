KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本コードベースには以下の主要機能を含みます:
- 発注・Execution エンジン（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC・統計解析）
- AI ベースのニュースセンチメント・レジーム判定（OpenAI 統合）
- 開発用ユーティリティ（.env ウィザード、設定検証、レポート生成）
- ロギング・プロセス優先度などの共通ユーティリティ

特徴一覧
--------
- 環境切替: KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に完全分離して記録
- 安全設計:
  - Kill Switch（data/kill.flag）で Engine を停止可能
  - 監視コンポーネントが稼働率・滞留注文・ドローダウン等を検出しアラート／Kill を発動
- AI 統合:
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント評価（ai_scores テーブルへ書込）
  - regime_detector: ETF とマクロニュースを組み合わせて日次レジーム判定
- ポートフォリオ構築:
  - 候補選定、等ウェイト／スコア重み、リスクベースのポジションサイズ算出、セクターキャップやレジーム乗数の適用
- レポーティング:
  - paper_verification_report によりペーパートレードの稼働性・約定率・レイテンシ指標を出力
- 設定管理:
  - .env 対話式ウィザード（config_setup）、事前チェック（validate_config）

セットアップ手順
---------------
1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なライブラリの一例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML （config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数（.env）設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参考にしてください）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI機能を使う場合）
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB）
     - LOG_LEVEL（DEBUG/INFO/...）

   - 自動 .env ロード
     - ライブラリ起動時にプロジェクトルート (.git または pyproject.toml) を検出し `.env` / `.env.local` を自動読み込みします。
     - 自動読み込みを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告も FAIL として扱えます:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成
   - data/ と logs/ はランタイムで自動作成されますが、必要に応じて手動で作成して権限を確認してください。

基本的な使い方
-------------
- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパー混同を避けるため、KABUSYS_ENV に応じて挙動が変わります。
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag を監視して自発停止します。
    - Kill Switch が発動すると data/kill.flag を書き込み ExecutionEngine に停止信号を送ります（設定により起動時に kill.flag を自動クリアするかどうかを制御できます）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 指定がない場合、DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照します。
  - 出力内容: 稼働率、注文成功率、送信率、レイテンシ（P95 など）と PASS/FAIL 判定

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

設定に関する注意事項
-------------------
- KABUSYS_ENV の値は development / paper_trading / live のいずれかにしてください。live 設定は本番発注につながりますので注意してください。
- paper_trading モードでは本番 DB を汚さないよう PAPER_TRADING_SQLITE_PATH を使用します（デフォルト: data/paper_trading.db）。
- Kill Switch:
  - KillSwitch は監視結果に応じて data/kill.flag を作成し ExecutionEngine に停止を促します。
  - 起動時に kill.flag を自動クリアするかは KILL_FLAG_CLEAR_ON_START 環境変数で制御します（デフォルト 0）。
- ロギング:
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日分保持）。
  - LOG_DIR, LOG_LEVEL 環境変数で調整できます。

ディレクトリ構成
----------------
（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py              — パッケージ定義, version
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・読み書きラッパー
    - system_monitor.py      — CPU/メモリ/Disk・データ鮮度の監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成 / クリア
    - monitoring_engine.py   — 各モニタを束ねたポーリングロジック
    - trade_monitor.py       — （滞留注文・約定異常等のチェック）※参照あり
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け関数
    - position_sizing.py     — 株数計算・集約キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計集計
  - ai/
    - news_nlp.py            — ニュースを LLM へ投げて銘柄ごとスコアを生成・DB に書込
    - regime_detector.py     — ETF MA とマクロニュースを組み合わせてレジーム判定（DB書込）
  - （execution/*.py, data/*.py, strategy/*.py などのサブパッケージが存在します）

運用・デバッグのヒント
---------------------
- ログの確認: logs/<app_name>.log と標準出力（systemd / supervisor のログ）を併用して原因調査します。
- プロセス優先度: 起動スクリプトは開始時に set_process_priority("high") を呼びます。権限のない環境では警告を出してスキップします。
- 停止・再起動:
  - 手動停止フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution のポーリングループが検知して終了します。
  - Kill Switch により安全に Execution を停止させたい場合は監視ロジック経由で data/kill.flag が作成されます。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して冪等でカラム追加等の簡易マイグレーションを行います。

ライセンス・貢献
----------------
この README はコードベースに基づく簡易ドキュメントです。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

補足（よくある質問）
-------------------
- Q: MONITOR_POLL_INTERVAL の最小値は?
  - A: 環境変数で秒数を指定できますが、1 未満や 0 以下は無効扱いされデフォルト 60 秒にフォールバックします。
- Q: AI 機能を使うには?
  - A: OPENAI_API_KEY を .env に設定してください。API 呼び出しは rate limit や 5xx に対してリトライ／フェイルセーフ処理がありますが、コストとレイテンシにご注意ください。

必要であれば、README をより詳細な起動手順（systemd / docker-compose 例）、API 使用例、設定サンプル（.env.example）などで拡張できます。どの追加ドキュメントが必要か教えてください。