# KabuSys

日本株向け自動売買システムのコアライブラリ。ポートフォリオ構築、発注実行、監視、リサーチ、AI ベースのニュース解析などの機能群を含むモジュール群です。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な目的は以下です。

- 市場データ（DuckDB）を用いたファクター／リサーチ処理
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行エンジン（実証用の Paper Trading 分離）
- 実行・システム監視（リスク監視、Kill Switch、アラートトリガ）
- ニュースを LLM で評価してスコアリング（OpenAI 利用）
- 運用支援ツール（.env ウィザード、設定検証、検証レポート）

設計方針として、DB（SQLite / DuckDB）を中心に非同期ではなくシンプルな同期処理で構成され、運用時の安全策（paper vs live 分離、kill flag、監視ログ）を重視しています。

---

## 主な機能一覧

- 実行スクリプト
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring

- 設定関連
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 監視（Monitoring）
  - system_monitor: システム資源、プロセス状態、データ鮮度を監視
  - trade_monitor: 発注ログの整合性・遅滞・約定異常を検出（モジュールあり）
  - risk_monitor: ドローダウンやポジション上限を評価し必要なら risk_logs / dashboard を更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込むことで ExecutionEngine を停止
  - monitoring_engine: 上記モニタを束ねたポーリングループ

- 発注関連
  - ExecutionEngine（EngineConfig）: 発注の実行・セッション管理（paper_trading 時は MockBroker）
  - OrderManager / OrderRepository / Reconciler / RiskManager

- ポートフォリオ構築
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap / calc_regime_multiplier
  - calc_position_sizes（リスクベース、等分配、スコア加重 等）

- リサーチ
  - calc_momentum / calc_volatility / calc_value（DuckDB の prices_daily / raw_financials を使用）
  - calc_forward_returns / calc_ic / factor_summary（特徴解析）

- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM による銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM 評価を合成して market_regime を算出

- ツール
  - tools.paper_verification_report: Paper Trading 結果を集計して PASS/FAIL レポートを生成

- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config モジュール: .env 自動読み込み、Settings クラスで環境変数をラップ

---

## セットアップ手順（開発 / 運用の簡易手順）

下記は最小限のセットアップ例です。プロジェクトルートは src/ を含むディレクトリです。

1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - (このリポジトリに requirements.txt がある場合はそれを使ってください)
   - 主要な依存例:
     - pip install duckdb psutil openai

   ※ 実際の依存は環境に応じてプロジェクトの requirements.txt を参照してください。

3. ディレクトリ作成（必要に応じて）
   - mkdir -p data logs

4. 対話式で .env を作る（推奨）
   - python -m kabusys.config_setup
   - これにより .env が生成されます（生成後、python -m kabusys.validate_config で検証してください）

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: LLM 機能を使う場合は必須（news_nlp / regime_detector）
   - KABUSYS_ENV: execution 挙動に影響（development / paper_trading / live）
     - paper_trading のとき発注は MockBroker に切り替わり、専用 DB に記録されます

6. 追加（任意）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - PAPER_FILL_MODE（paper_trading 時の約定挙動。instant|partial|never|reject）

---

## 使い方（主要なコマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 対話式に入力して .env を生成します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります（exit code 1）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_sqlite_path（data/paper_trading.db 等）へ記録
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 実行中に data/stop_requested.flag を作成するとエンジンを停止
    - プロセス優先度を "high" に設定します（プラットフォーム依存で成功しないことがあります）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（監視 DB）に接続して監視テーブルを初期化
    - SystemMonitor.check_once() をポーリング
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - stop フラグ（data/stop_requested.flag）でループを終了します
    - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH: PAPER_TRADING_SQLITE_PATH を上書き
  - 出力: 稼働率、注文成功率、レイテンシなどの集計と PASS/FAIL 判定

- AI 系（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の接続（duckdb.connect(...)）を渡して利用します
  - OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡してください

---

## 停止 / Kill スイッチ

運用上の停止方法:

- 停止要求（run_monitoring / run_execution のループ停止）
  - data/stop_requested.flag を作成する（任意の内容で可）。起動ループはこのファイルを検知して終了します。

- 実行エンジン強制停止（Kill Switch）
  - 監視側（KillSwitch）が条件を満たすと data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill flag のクリア設定を持ちます（Settings.kill_flag_clear_on_start）。
  - kill.flag の存在は本番停止トリガとして扱われます（運用注意）。

---

## 代表的な環境変数（主要なもの）

（Settings クラス / validate_config.py の内容に基づく）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- LOG_DIR — ログの保存先（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必須
- PAPER_FILL_MODE — paper_trading 時のモック約定ルール（instant|partial|never|reject） デフォルト: instant
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒） デフォルト: 60
- KILL_FLAG_CLEAR_ON_START — 本番での kill.flag 自動クリア（0/1） デフォルト: 0

例（.env の最小例）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## ディレクトリ構成（主要ファイル）

（src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを LLM でスコア化して ai_scores 書き込み
    - regime_detector.py      — マーケットレジーム判定（MA + マクロニュース）

  - monitoring/
    - monitoring_db.py        — SQLite の監視テーブル作成・永続化 API
    - system_monitor.py       — システム資源・データ鮮度監視
    - trade_monitor.py        — 発注ログ監視（ファイルに含まれる想定）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch（data/kill.flag 書込）
    - monitoring_engine.py    — 各モニタの統合ポーリング・アラート連携
    - alert_manager.py        — （警告・通知連携。コードベースに存在）

  - execution/
    - execution_engine.py     — ExecutionEngine（セッション管理）
    - broker_factory.py       — ブローカークライアント生成（MockBroker など）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - data/
    - pipeline.py              — DuckDB prices_daily 等を扱うユーティリティ（参照される）
    - stats.py                 — 正規化ユーティリティ（zscore 等）

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - logging_setup.py
    - process_priority.py
    - 他ユーティリティ群

- data/                       — デフォルト DB / フラグ / pid 等を配置（実行時に作成）
- logs/                       — ログ出力先（デフォルト）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では .env の秘匿情報管理に注意してください（.env を Git にコミットしない）。
- Kill Switch / stop flag の挙動を十分に理解した上で運用してください。特に KILL_FLAG_CLEAR_ON_START=1 は本番で危険です。
- OpenAI を利用する機能は API コストとレスポンス不安定性（レート制限）に注意してください。news_nlp/regime_detector はリトライ・フォールバック実装がありますが、API キーが漏れないようにしてください。
- Paper Trading と Live は DB を分離しているため（paper_sqlite_path）、誤って本番 DB に書き込まないように設定を確認してください。

---

## 参考コマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はリポジトリ内のコード構成とコメントに基づいて作成しています。詳細な運用手順や依存パッケージ一覧はプロジェクトの top-level ドキュメント（requirements.txt / ops ドキュメント）があればそちらを優先してください。必要であれば、README に追加するコマンド例や .env のサンプルを作成します。