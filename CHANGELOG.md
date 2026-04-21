Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
<https://keepachangelog.com/ja/1.0.0/>

Unreleased
---------

(未リリースの変更はここに記載します。)

0.1.0 - 2026-04-21
------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコアモジュール群を追加。
  - src/kabusys/__init__.py
    - バージョン定義 __version__ = "0.1.0" を追加。
- 起動スクリプト / 実行系
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する概念を導入（本番 DB と完全分離）。
    - BrokerClientFactory を用いたブローカークライアント生成と、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag により安全に停止可能。PID ファイルを書き出す仕組みあり（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - src/kabusys/run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値は警告を出してデフォルトにフォールバック。
    - 監視 DB（SQLite）は環境にかかわらず本番 sqlite_path を使用して接続・初期化する設計（監視は本番データに対して行う想定）。
    - stop_requested.flag による停止、KeyboardInterrupt による優雅な終了、例外時のロギングでループ継続。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順序・オーバーライドルールを実装（OS 環境変数は保護）。
    - 複雑な .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを実装し、各種環境変数をプロパティ経由で取得（DB パス、PID/kill flag、閾値、Paper トレード設定等）。
    - PAPER_FILL_MODE のバリデーション、有効値: instant|partial|never|reject。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）と LOG_LEVEL の検証。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加（質問 → 確認 → .env 保存）。
    - デフォルト値、選択肢、シークレット入力（マスク表示）をサポート。既存 .env の読み込みと Enter による再利用に対応。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の基本検証を行う CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml 存在チェックと（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的ロギングセットアップ関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップし警告出力。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX(nice) の差分吸収、permission エラー時は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
    - スコア全 0 の場合のフォールバック（等金額配分）と警告出力を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を追加（売却予定銘柄を除外、"unknown" セクターは制限対象外）。
    - レジームに応じた資金乗数 calc_regime_multiplier を実装（bull:1.0, neutral:0.7, bear:0.3、未知レジームはフォールバックして 1.0 とし警告）。
  - src/kabusys/portfolio/position_sizing.py
    - 株数計算ロジック calc_position_sizes を実装。
    - allocation_method に応じた計算 ("risk_based", "equal", "score")、単元 (lot_size) の丸め、per-position 上限・aggregate cap を考慮したスケーリングと残差配分ロジックを実装。
    - cost_buffer を用いてスリッページ・手数料を保守的に見積もる。
  - src/kabusys/portfolio/__init__.py
    - 主要関数をパッケージ公開。
- 研究・分析ユーティリティ
  - src/kabusys/research/factor_research.py（実装途中）
    - ファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、出来高等の計算方針と定数定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計方針を記載。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 指標計算、期間フィルタ（--from, --to）、閾値と Pass/Fail 判定を実装。
    - 閾値（初期設定）:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
- DB 初期化
  - src/kabusys/monitoring/monitoring_db.py を参照して監視テーブルの初期化を run_execution/run_monitoring が起動時に保証（冪等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Known issues
- research/factor_research.py は実装の途中でファイル末尾が未完（calc_momentum の途中で切れている）。今後のリリースで完成予定。
- 一部の箇所で将来的な拡張や TODO コメントあり（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック）。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでの安全フォールバックを行うが、期待どおりに動作しない環境があり得る（警告を出してスキップ）。
- 設定ファイル（config/*.yaml）の検証は PyYAML がインストールされている場合のみ実行。未インストール時はスキップして警告を出す。
- monitoring はあえて「環境にかかわらず本番 sqlite_path を使用する」設計になっている。テスト時は意図的に挙動に注意すること。

参考: 実行可能な CLI
- python -m kabusys.config_setup   — .env ウィザード
- python -m kabusys.validate_config [--strict]  — 設定検証
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]  — Paper 検証レポート

作者注
- 初回公開リリース。今後は research モジュールの完成、細かなバグ修正、テスト・ドキュメントの充実を予定しています。