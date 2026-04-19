CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本バージョン 0.1.0 を公開（初回リリース）。
- コアアプリケーション:
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定。
- 環境設定・管理:
  - config モジュールを追加:
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）を実装。
    - .env パース機能を独自実装（export 形式、引用符・エスケープ、インラインコメント対応）。
    - Settings クラスを提供し、環境変数から各種設定（DB パス、API トークン、閾値、環境判定など）を取得・検証。
    - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - config_setup CLI を追加:
    - 対話式ウィザードで .env を作成 / 更新する機能。
    - 秘匿項目はマスク表示、デフォルト値のサポート、保存前の確認プロンプト。
  - validate_config CLI を追加:
    - 必須環境変数や KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML 任意）。
    - --strict オプションで警告をエラー扱いに可能。
- 実行 / 監視:
  - run_execution スクリプトを追加:
    - ExecutionEngine の起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper_trading の場合は Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session を別スレッドで実行。停止フラグ（data/stop_requested.flag）による安全停止処理。
    - PID ファイル管理（data/execution.pid）。
  - run_monitoring スクリプトを追加:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境にかかわらず monitoring は本番 sqlite_path を使用（監視 DB は共通）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt による終了もハンドリング。
    - check_once() 実行中の例外を捕捉してループ継続（監視プロセスの頑健化）。
- データベースと分析:
  - DuckDB / SQLite の接続を利用する設計を導入（duckdb_path / sqlite_path を Settings で管理）。
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db）呼び出しにより、監視テーブルの存在を保証（冪等）。
- ロギング & プロセス制御:
  - utils.logging_setup を追加:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日分保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続。
    - デフォルト LOG_LEVEL/LOG_DIR の解決順を実装。
  - utils.process_priority を追加:
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を提供。
    - psutil のアクセス拒否等を安全にハンドリングし、失敗時は警告ログでスキップ。
- ポートフォリオ構築ライブラリ:
  - portfolio パッケージを追加（純粋関数群）:
    - portfolio_builder:
      - select_candidates: スコア降順で候補選定（タイブレークとして signal_rank を利用）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア比率による配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中を検出して新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告のうえ 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method に応じた発注株数算出（"risk_based" / "equal" / "score" をサポート）。
      - 単元株丸め（lot_size）、per-position 上限、aggregate cap（available_cash）を実装。資金超過時はスケーリングと端数配分ロジックを用意。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
- リサーチ / ファクター計算:
  - research.factor_research モジュール（ファクター計算設計、モメンタム・ATR 等の定数や calc_momentum 等の実装スタブ/開始）。
  - DuckDB を使った prices_daily / raw_financials に基づくファクター計算方針。
- ツール:
  - tools.paper_verification_report スクリプトを追加:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し、閾値に基づき PASS/FAIL を判定。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

Fixed
- 環境変数パースや .env 読み込みに伴うエラーを安全に扱うよう改善:
  - .env ファイルの読み込み失敗時に警告を出し続行（テスト環境等での堅牢性向上）。
  - MONITOR_POLL_INTERVAL に不正な値が設定された場合、警告を出してデフォルトにフォールバック。
- ログディレクトリ作成失敗時にプロセスが停止しないように改善（ファイルハンドラをスキップして stdout のみで継続）。
- プロセス優先度・CPU affinity 設定で権限不足や未対応 OS の場合に例外を投げず警告でスキップするよう修正。

Changed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 外部シークレットは .env に記載する設計のため、.env を Git にコミットしない旨を config_setup のコメントで明示。

Notes / 今後の改善点（コード内コメントより推測）
- position_sizing:
  - 銘柄ごとの lot_size を将来サポートするための拡張の余地あり（現在は全銘柄共通）。
  - 価格欠損時（0.0）の扱いで過少評価される可能性があるため、フォールバック価格の導入を検討。
- risk_adjustment.calc_regime_multiplier:
  - 未知レジームに対する警告があるが、運用方針に応じた追加レジーム対応が必要。
- research.factor_research:
  - calc_momentum 実装が途中で切れているため、完全実装（各ファクター計算・正規化）が必要。
- テスト:
  - PyYAML がインストールされていない場合の挙動があり、CI 環境での依存関係明示が望ましい。

--- 

この CHANGELOG は、提供されたソースコードの内容から実装された機能や動作を推測して作成しています。実際のリリースノートとして利用する場合は、リリース日や変更の意図、責任者などをプロジェクト実態に合わせて調整してください。