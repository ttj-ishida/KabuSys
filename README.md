# KabuSys

日本株向け自動売買システムの実装サンプル（ライブラリ／起動スクリプト群）

このリポジトリは、発注エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含むモジュール群を提供します。設計方針として「実運用を想定した堅牢性」「環境分離（paper_trading と live）」「フェイルセーフ」を重視しています。

概要・意図
- ExecutionEngine：発注・リスク管理・注文管理をまとめた実行エンジン（paper_trading ではモックブローカーを使用）
- Monitoring：システム状態・注文ログ・リスク監視・Kill Switch 実装
- Portfolio：銘柄選定・重み計算・ポジションサイズ算出（純粋関数群）
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI：ニュース記事を LLM（OpenAI）で評価し銘柄スコアやマクロセンチメントを算出
- Tools：ペーパートレード検証レポート生成などユーティリティ

主な特徴
- 環境分離：KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）に書き込み、本番 DB とは完全に分離
- 監視（Monitoring）：
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを持つ SQLite ベースの永続化
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine により定期チェック、アラート、Kill Switch 発動
- AI モジュール：
  - news_nlp：OpenAI へのバッチ送信、結果のバリデーション、ai_scores への書き込み
  - regime_detector：ETF 1321 の MA200 とマクロニュースを組合せて市場レジーム判定
- ロギング：
  - 統一的な logging 設定（コンソール + 日次ローテートログ）
- 開発支援：
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

必須・推奨依存パッケージ（例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合）
（実際は requirements.txt に合わせてインストールしてください）

セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... ; cd <repo>

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実プロジェクトでは requirements.txt を用意している場合はそちらを利用してください。

4. 初期ディレクトリを作る（データ / ログ）
   - mkdir -p data logs

5. 環境変数設定（.env の作成）
   - 対話式ウィザードで .env を作成（推奨）
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な値を設定するか、環境変数で上書きしてください。

6. 設定検証
   - python -m kabusys.validate_config
   - 本番準備時は厳格モードで警告も FAIL 扱いにする:
     - python -m kabusys.validate_config --strict

重要な環境変数（代表的なもの）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（任意）: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（任意）: paper_trading での約定モード（instant / partial / never / reject）
- LOG_LEVEL（任意）: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（任意）: ログ出力ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL（任意）: run_monitoring のポーリング間隔（秒, デフォルト 60）

使い方（起動・実行）

- 監視プロセス起動（プロセス優先度設定・ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は監視用 DB の初期化（init_monitoring_db）を行います。
  - 監視プロセスはリポジトリルート直下の data/stop_requested.flag が作成されるとループを抜けて終了します（手動停止用）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、書き込み先は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）で本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
  - 停止は data/stop_requested.flag を書いてエンジンに検知させるか、Kill Switch（data/kill.flag）で外部トリガーする仕組みがあります。

- .env の作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- Paper Trading 検証レポート出力（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（--db PATH）

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出すことで ai_scores / market_regime に書き込みます。
  - 実行例（スクリプト呼び出しは用意されていないため、Python REPL 等で呼び出します）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, date(2026,4,1), api_key="...")

停止・Kill Switch の仕組み（運用メモ）
- ExecutionEngine の停止は複数手段で可能:
  - data/stop_requested.flag を作成 → run_execution/run_monitoring が検知して終了
  - Kill Switch（監視側が条件を評価して data/kill.flag を作成）→ ExecutionEngine が検知して停止
- Settings.kill_flag_clear_on_start が 1 のとき、Execution 起動時に kill.flag を自動クリア（本番では 0 推奨）

ログ
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler により日次ローテート、30 日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトから呼び出して統一している
- LOG_DIR 環境変数でログディレクトリを上書き可能

ディレクトリ構成（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み機能を含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・永続化 API
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文ログ等の監視コンポーネント）※実ファイル参照
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成 / 操作
    - monitoring_engine.py    — 各 Monitor を束ねて実行するエンジン
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（発注ループ）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/ （実行時に生成されることが想定）
    - *.db, *.pid, kill.flag, stop_requested.flag など

開発・運用時の注意点
- .env を誤って公開しないこと（README 内でも注意書き）。
- KABUSYS_ENV=live では取り扱いに細心の注意を（validate_config にてライブ環境用の警告あり）。
- OpenAI API を使う機能はネットワーク依存・レート制限や料金が発生するため、テスト時はモック化推奨。
- monitoring は監視用 DB へ必ず書き込む（run_monitoring は環境にかかわらず設定された sqlite_path を使う設計）。
- paper_trading モードは本番 DB を汚さないための分離を徹底していますが、環境変数の設定ミスに注意してください。

トラブルシューティング
- 起動時に必須環境変数がない場合は validate_config で検出できます。まず validate_config を実行してください。
- OpenAI 関連が失敗する場合、OPENAI_API_KEY の設定とネットワーク接続・クォータを確認してください。
- ログファイルが出力されない場合は LOG_DIR の書き込み権限やログディレクトリ作成の失敗（起動時に警告出力）を確認してください。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。初回は data ディレクトリが存在するか確認してください。

貢献・拡張ポイント（例）
- stocks マスタに単元情報を持たせて position_sizing の lot_size を銘柄別に対応
- monitoring のアラート送信（LINE / Slack）の追加実装
- trade_monitor のさらに詳細な検査ルール追加
- テスト用モジュールと CI の整備（ユニットテスト / モック）

ライセンス・著作権
- （ここにプロジェクトのライセンス情報を記載してください）

以上。README に追加して欲しいコマンドや構成の詳細、あるいは特定モジュールの利用例（例えば ExecutionEngine の API や AI モジュールの呼び出しサンプル）があれば指示ください。