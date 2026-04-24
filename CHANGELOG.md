CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  
セマンティックバージョニングを採用しています。

フォーマット
-----------
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回公開リリース。以下の主要コンポーネントを追加。
  - 実行用スクリプト
    - run_execution.py
      - ExecutionEngine の起動スクリプトを実装。起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db がデフォルト）を使用して本番 DB から完全に分離。
      - ブローカークライアント生成（BrokerClientFactory）、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。
      - 停止用フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。停止フラグ検知時に安全に停止する処理を実装。
  - 監視用スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。初期でプロセス優先度を "high" に設定。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックして警告出力。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様（監視データは本番 DB に記録）。
      - stop flag（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt に対するハンドリングと接続クローズを保証。
  - 設定管理
    - config.py
      - 環境変数の読み込み／取得を統一する Settings クラスを提供。
      - .env 自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。優先順位: OS環境変数 > .env.local > .env。
      - クォートやエスケープ、コメント処理に対応した .env パーサ実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
      - 各種設定プロパティ（J-Quants, kabu API, DuckDB/SQLite パス, PAPER_FILL_MODE, PID/kill flag パス, 監視閾値, 環境カテゴリチェック 等）を提供。環境値のバリデーションを実装。
    - config_setup.py
      - .env を対話式に作成／更新するウィザードを実装。既存 .env の読み込み/再利用、シークレットマスク表示、保存確認を備える。
  - 設定検証ツール
    - validate_config.py
      - .env と config/*.yaml の事前検証 CLI を実装。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）等を行う。
      - --strict モード（警告を FAIL 扱い）をサポート。live 環境時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - ロギング／プロセス制御ユーティリティ
    - utils/logging_setup.py
      - 共通ログ設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
      - ログレベルとログディレクトリの解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
    - utils/process_priority.py
      - Windows / POSIX 間の差分を吸収するプロセス優先度設定と CPU affinity 設定を提供（psutil ベース）。
      - set_process_priority: high/normal/low の抽象レベルをサポートし、アクセス拒否等の例外時に警告を出してスキップ。
      - set_cpu_affinity: 指定コア数にプロセスをピン留め。検証と例外ハンドリングを実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）を実装。既存保有をもとにセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外。
      - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（'bull'/'neutral'/'bear' をサポート、未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - 発注株数決定ロジックを実装。allocation_method に "risk_based", "equal", "score" をサポート。
      - risk_based：risk_pct / stop_loss_pct ベースで目標株数を算出。単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）を適用。
      - aggregate cap 超過時はスケーリングして、残余で端数を lot 単位に復元するアルゴリズムを実装。cost_buffer により手数料・スリッページを保守的に見積もる。
  - リサーチ（ファクター計算）基盤
    - research/factor_research.py（モメンタム等の計算ロジック骨子を実装）
      - DuckDB を使って prices_daily / raw_financials を参照する設計。1M/3M/6M リターン、MA200 差分、ATR、出来高指標等の計算を想定した定数・補助関数を実装（関数群は DuckDB 接続を受ける純粋関数として設計）。
  - ユーティリティ・ツール
    - tools/paper_verification_report.py
      - ペーパートレード（paper_trading）用 SQLite DB を参照して検証レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、閾値（稼働率 99%, 成功率 90% 等）に基づく PASS/FAIL 判定を行う。
      - DB 不在やテーブル欠損時に安全に N/A を返す耐障害性を実装。
  - パッケージ初期化
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- （該当なし：初回リリース）

Fixed
- .env パーサや各種ツールにおいて、実行時に陥りやすい例外を捕捉してフォールバックする実装を多く導入（例: MONITOR_POLL_INTERVAL の不正値、ログディレクトリ作成失敗、psutil の権限制約など）。

Security
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes
- Paper Trading と本番 DB の分離設計により、ペーパートレード実行時のデータはデフォルトで data/paper_trading.db に保存され、本番 SQLite（data/monitoring.db）とは分離されます。運用時は環境変数 PAPER_TRADING_SQLITE_PATH などでパス変更可能です。
- マルチプラットフォーム対応のため、プロセス優先度や CPU affinity の設定は実行環境によって挙動が異なります。権限不足や未対応 OS の場合は警告を出して安全にスキップします。
- ログ出力は標準出力（stdout）優先で、ファイル出力は logs/<app_name>.log に日次ローテーションで保存（デフォルトで 30 日分保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

--- 
（この CHANGELOG は、提供されたソースコードから実装されている機能を推測して作成しています。実際の変更履歴やリリースノートは運用ルールに合わせて適宜調整してください。）