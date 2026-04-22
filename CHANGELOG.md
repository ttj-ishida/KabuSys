# Changelog

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠します。セマンティックバージョニングを使用します。

- リリースノートの文言・日付はコードベースの内容から推測して作成しています。
- 不明な外部参照（例: リリース配布 URL 等）は省略しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-22

Added
- 初期リリース。自動売買フレームワーク「KabuSys」の基礎機能を追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を介して本番 / モックブローカーを切替。
    - 停止制御: data/stop_requested.flag を監視し、flag 検出で安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動する CLI エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - 停止制御: 上位プロジェクトの data/stop_requested.flag を監視してループを終了。
    - DuckDB を分析 DB として接続。
- 設定管理
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
    - .env パース実装（クォート、エスケープ、コメントの扱いに対応）。
    - Settings クラスを提供。J-Quants / kabuAPI / DB パス / Paper Trading モード等のプロパティを定義し、妥当性チェック（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
    - settings = Settings() の単一インスタンスをエクスポート。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - シークレット項目のマスク表示、既存値の再利用、選択肢・デフォルト提示をサポート。
- 構成検証
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パース検証（PyYAML がある場合）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR の環境変数または引数で設定可能。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX (Linux, macOS, FreeBSD) を吸収するプロセス優先度設定。
    - set_process_priority(level) で "high" / "normal" / "low" を設定。権限不足等は警告でフォールバック。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（実行環境制約でスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定: select_candidates (スコア降順、タイブレークは signal_rank)。
    - ウェイト計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化。全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限: apply_sector_cap（既存ポジションと価格マップを参照して同一セクターの新規候補を除外）。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に応じて資金乗数を返す。未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 株数計算: calc_position_sizes
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot）丸め、1 銘柄上限（max_position_pct）、総投入上限（max_utilization）を考慮。
      - cost_buffer（手数料・スリッページ見積り）と aggregate cap によるスケールダウンと残差処理（lot 単位で再配分）を実装。
      - 現行設計では lot_size は全銘柄共通（将来的に拡張予定）。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg / max / P95）等を計算。
    - P95 の計算実装、閾値（稼働率 >=99%、成功率 >=90%、送信率 >=95%、P95 <=200ms）に基づく PASS/FAIL 判定を出力。
- research/factor_research.py
  - DuckDB 接続を用いたファクター計算モジュール（Momentum / Value / Volatility / Liquidity 等の計算に着手）。
  - 設計メモと定数を定義（horizon 等）。一部関数は実装途中で切れているが、設計方針が含まれる。
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （特に記載なし）

Notes / 注意事項
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- run_monitoring は監視データを本番 sqlite に書き込む設計です。監視データの分離が必要な場合は設定を見直してください。
- process_priority の設定は OS と実行ユーザーの権限に依存します。権限不足時は警告ログを出してスキップします。
- 一部モジュール（特に分析系）は今後の拡張を想定した TODO コメントがあります。

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0