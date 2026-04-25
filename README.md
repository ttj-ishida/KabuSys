# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリは、戦略研究（ファクター計算・特徴量解析）、ポートフォリオ構築、ポジションサイジング、発注実行、モニタリング、AI ベースのニュース解析までを含むモジュール群を提供します。

---

## プロジェクト概要

主な目的：
- DuckDB / SQLite を用いた時系列データ解析とログ永続化
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算）
- 発注エンジン（ExecutionEngine）と安全監視（Monitoring）
- ニュースを LLM（OpenAI）でセンチメント評価し投資判断に活用する機能
- ペーパートレード用の分離された DB を用いた検証手段（paper_trading）

重要な設計方針：
- 本番とペーパートレードの DB は分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアスを避ける設計（date.today() などを直接参照しない）
- API 呼び出しはリトライやフォールバックを伴うフェイルセーフ設計
- ロギングは統一的に設定（stdout + 日次ローテートファイル）

---

## 機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（実際の注文処理）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築モジュール:
  - 銘柄選定: select_candidates
  - 重み計算: calc_equal_weights, calc_score_weights
  - セクター制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier
  - 発注株数計算: calc_position_sizes
- 研究用モジュール:
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン / IC / 統計要約: calc_forward_returns, calc_ic, factor_summary
- AI モジュール:
  - ニュース NLP スコアリング（OpenAI 使用）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（OpenAI + MA200）: kabusys.ai.regime_detector.score_regime
- モニタリング永続化（SQLite）: monitoring_db + MonitoringDB クラス
- Kill Switch（data/kill.flag）による安全停止判定

---

## 前提条件（依存ライブラリ）

必須（最低限）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)

オプショナル:
- PyYAML（config/*.yaml の詳細検証を行う場合）
- そのほかプロジェクトで使用するブローカー SDK 等（実際の発注連携時）

インストール例:
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布されたパッケージを展開する
2. 仮想環境を作成し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML
3. .env を作成
   - 対話式ウィザードを実行:
     python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないこと
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使用する場合）

4. （任意）設定検証を実行:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）

5. 初期データディレクトリを作成（通常は実行時に自動作成されますが手動で用意することも可能）
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 使い方

起動スクリプト類はモジュール実行（python -m ...）で利用します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - --env-file で .env のパスを指定可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB を使用（デフォルト: data/paper_trading.db）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 停止時は data/stop_requested.flag を作成すると実行中エンジンが停止する
    - 実行中に作成される PID ファイル: data/execution.pid

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）を使用（KABUSYS_ENV に関わらず本番 DB を参照）
  - 停止は data/stop_requested.flag を作成する（存在を検知してループ終了）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数も使用可能）

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定してから関数を呼ぶ（ライブラリ API）
  - 例: Python から
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)  # conn は duckdb 接続
  - API キー未設定の場合は例外を投げる

ログ:
- ログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。ログディレクトリは環境変数 LOG_DIR、ログレベルは LOG_LEVEL で調整可能。

停止 / Kill Switch:
- 監視ロジックはリスク閾値を超えた場合に data/kill.flag を書き込んで ExecutionEngine 側に停止を促します（KillSwitch）
- ユーザ操作でエンジンを即停止させたいときは data/stop_requested.flag を作成してください（run_execution / run_monitoring が検知して終了します）
- 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は起動時に kill.flag を自動で削除する設定も可能（本番は 0 推奨）

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパスを上書き可能

設定ウィザードで作成される項目一覧は `kabusys/config_setup.py` を参照してください。

自動 .env ロード:
- デフォルトでプロジェクトルートの `.env` と `.env.local` を起動時に読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定読み込みと Settings クラス
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/ （実行時に生成される想定）
    - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil 使用）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ & MonitoringDB（永続化層）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — （取引監視ロジック、コード内に存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各 Monitor の束ねとポーリング
    - alert_manager.py — （アラート配送ロジック）
  - execution/ — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, Reconciler 等）
  - portfolio/ — ポートフォリオ構築モジュール（builder, position_sizing, risk_adjustment）
  - research/ — ファクター計算・特徴量探索（factor_research, feature_exploration）
  - ai/ — OpenAI ベースの機能（news_nlp, regime_detector）
  - monitoring/ — 監視用モジュール群（上記）
  - monitoring/monitoring_db.py — DB 初期化 / マイグレーションを含む（テーブル定義）
  - その他: data パイプラインや stats 等、研究 / データ加工用モジュール

（注）リポジトリの完全なファイル一覧は実際のツリーを参照してください。上記はこのコードベース中で特に重要なモジュールを抜粋しています。

---

## 開発者向けメモ / トラブルシューティング

- SQLite / DuckDB ファイルパスの親ディレクトリが存在しない場合、validate_config は警告を出します。実行スクリプトは起動時に必要に応じてディレクトリを作成することがありますが、権限エラー等に注意してください。
- ログディレクトリ作成に失敗するとファイルハンドラは無効化され、コンソール出力のみになります（警告が stderr に出ます）。
- psutil の優先度 / affinity 操作は権限が必要になる場合があります。許可がないと警告が出ますが処理は継続されます。
- AI 機能を利用する場合、API のレート制限やネットワークエラーに対して内部でリトライ実装がありますが、キーの残高・利用制限には注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB を破壊せずに列を追加する簡易マイグレーションを行いますが、複雑な変更は手動で対処してください。

---

## よく使うコマンドまとめ

- .env 作成:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- ExecutionEngine 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要機能と運用方法の概要を示します。より詳細な設計意図やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等のドキュメント）がプロジェクトに含まれている場合、それらも参照してください。質問や補足ドキュメントの追加要望があれば教えてください。