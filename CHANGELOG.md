CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （今後のリリース用のプレースホルダ）

[0.1.0] - 2026-04-19
--------------------
最初の公開リリース。以下の主要機能・ユーティリティ・CLI を含みます。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - 環境変数の厳密チェック用ヘルパ（_require）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 各種環境変数プロパティを提供（J-Quants / kabuAPI / DB パス / Paper Trading モード等）。
    - PAPER_FILL_MODE の妥当性検証、環境別フラグ（is_live / is_paper / is_dev）を提供。

- .env 対応強化
  - export プレフィックス、クォートされた値、エスケープ、行末コメント等を扱えるパーサを実装。
  - .env の読み込み／書き込みユーティリティ実装（config_setup.py）（対話式ウィザードを提供）。
  - config_setup: 対話式で .env を作成/更新。シークレット項目をマスク表示して保存。

- 設定検証 CLI
  - validate_config.py 実装。
    - 必須 / 任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査。
    - DB パスや config/*.yaml の存在確認（PyYAML があればパース検証）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプション（警告を FAIL 扱い）。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine を組み立てて起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの抽象化、OrderRepository/OrderManager/ RiskManager/Reconciler の組み立て。
    - Engine をデーモンスレッドで実行し、data/stop_requested.flag による停止検知、PID ファイル指定対応。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視 DB は環境に関わらず production sqlite_path を使用（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ検知で安全に終了。

- ロギング・プロセス管理ユーティリティ
  - logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティ。
    - LOG_DIR / LOG_LEVEL に基づく解決、既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）。
  - process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows と POSIX を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足等は警告してスキップ。

- ポートフォリオ構築・リスク管理機能（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重。全銘柄スコアが 0 の場合は等分配にフォールバック（警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑制するフィルタ（sell_codes の除外対応、"unknown" セクターの扱い）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear のマップ、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method("risk_based" | "equal" | "score") に対応した株数決定ロジック。
    - lot_size 単位で丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮して調整。
    - aggregate scaling 時の再配分アルゴリズム（fractional remainder を使った安定的な追加配分）。
    - TODO 留意点をコメントに記載（将来的な銘柄別 lot_size 対応、価格欠損時のフォールバック等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を算出するレポートを標準出力に出力。
    - P95 の計算、期間フィルタ（--from/--to）、各閾値を定義して PASS/FAIL 判定を行う。
    - DB が存在しない・テーブルがない場合のフォールバック（OperationalError をキャッチ）。

Changed
- ログ出力を stdout に一本化（StreamHandler を stdout に設定）。cron/Task Scheduler 等からの取り扱いを考慮。
- .env の読み込み順序を OS 環境 > .env.local > .env に明確化、既存 OS 環境は protected として上書き防止。

Fixed
- 不正な MONITOR_POLL_INTERVAL 値による time.sleep の ValueError を回避するため、0 以下や非数値の場合はデフォルトへフォールバックし警告を出力。

Notes / Implementation details
- run_monitoring は監視用 DB（monitoring.db）を環境に依らず使用する設計になっている点に注意（監視データは本番 DB に記録される想定）。
- run_execution は paper_trading 環境時に paper_trading.db を使用し、本番 DB とデータ分離を行う。
- config_setup の .env 書き込み時、セキュリティの観点から .env を絶対に Git にコミットしない旨をヘッダに記載。
- process_priority の実行は OS 権限に依存するため、失敗時は警告ログを出力して処理を継続する。
- portfolio や position_sizing は純粋関数（副作用なし）で設計されているため、テストが容易。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合の過少見積りについて注記あり。将来的に前日終値や取得原価でのフォールバックを検討する旨をコメントで残している。
- position_sizing の将来的拡張: 銘柄別 lot_size を持たせる設計への拡張予定（コード内に TODO）。
- research.factor_research モジュールは大きな実装を含むが、ソース末尾で calc_momentum の定義が途中で切れている（未完の可能性）。次リリースでの完成が見込まれる。

Migration notes
- ログ設定、プロセス優先度設定を省略していた既存の運用スクリプトは、setup_logging() と set_process_priority() の呼び出しを追加することで、標準化されたログ出力・プロセス優先度を利用できます。
- 環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading を完全に本番と分離するため、KABUSYS_ENV=paper_trading 設定時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を利用すること。

Security
- シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存されうるため、.env をリポジトリに含めない運用（.gitignore への追加）を強く推奨。

-----

今後のリリースでは以下を予定しています:
- research.factor_research の完成と単体テスト整備
- portfolio のユニットテスト強化およびパラメータ検証の追加
- 運用改善のため監視アラート（LINE 通知等）とドキュメントの充実

もし CHANGELOG に追加してほしい点（例: リリース日や担当者、より詳細な変更点の分割）があれば教えてください。