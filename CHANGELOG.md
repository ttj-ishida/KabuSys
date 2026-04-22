CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在の時点で未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------

Added
- パッケージ初期リリース: KabuSys v0.1.0 を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き対応（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 停止フラグ (data/stop_requested.flag) 検出でループ終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite(DB) を使用（本番 DB と完全分離）。
    - ブローカークライアントは BrokerClientFactory から生成。paper_trading 環境では MockBrokerClient 想定（分離保存: data/paper_trading.db）。
    - Engine は別スレッドで実行。停止フラグ (data/stop_requested.flag) 検知時に安全に停止。PID ファイル管理をサポート。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。
    - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、クォートとバックスラッシュエスケープ、インラインコメント処理をサポート。
    - Settings クラスを提供。主要な設定プロパティをラップ（J-Quants / kabu API / LINE / DB / 監視閾値 / 環境判定など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject のみ許容）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（不正値は ValueError）。
- 設定ユーティリティと CLI
  - config_setup.py
    - 対話式ウィザードを追加。.env の初期作成・更新を支援。既存 .env の読み込み・Enter による既存値再利用、機密値のマスク表示、最終確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数・パス・config/*.yaml の存在などをチェック）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数または引数で制御。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定を追加（Windows / POSIX 対応）。無効なレベルは ValueError。
    - set_cpu_affinity() を追加し、プロセスの CPU affinity 固定をサポート。権限不足等は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を追加。既存ポジションのセクター時価比を基に新規候補を除外するロジックを提供。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - 発注株数計算ロジック（calc_position_sizes）を追加。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregated cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページ考慮）を実装。スケールダウン時の残差配分アルゴリズムを備える。
  - portfolio/__init__.py にて主要関数のエクスポートを提供。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite データベースを読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計・判定するレポート生成スクリプトを追加。
    - デフォルト DB パスは data/paper_trading.db。--db / PAPER_TRADING_SQLITE_PATH で指定可能。
    - パスが見つからない場合のエラーメッセージと閾値（稼働率 99%、成功率 90% 等）による PASS/FAIL 判定を提供。
- リサーチ（開発中）
  - research/factor_research.py（開発中のファクター計算モジュールを追加）
    - Momentum / Value / Volatility / Liquidity を計画。DuckDB 接続を受け、prices_daily / raw_financials テーブルを使って計算する設計。
    - モジュール内に定数や calc_momentum の骨格、P95 等のユーティリティが含まれる（現時点でファイル末尾に未完の実装あり）。
- パッケージ初期化
  - __init__.py にてバージョン (0.1.0) と主要サブパッケージ名を定義。

Changed
- （該当なし。初期リリースのため変更履歴は追加に集中）

Fixed
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数を扱う .env ファイルは生成時に明示的に Git にコミットしないよう注意喚起を追加（config_setup.py のヘッダコメント）。

Notes / 実装上の注意点
- .env パーサは多くのケースをサポートするが、複雑なエスケープやマルチライン値は想定していません。
- monitoring の DB 接続は設計上「環境にかかわらず本番 sqlite_path を使う」仕様です。paper_trading 実行時に監視だけ別 DB にしたい場合は設定やコードの見直しが必要です。
- research/factor_research.py はまだ未完の関数実装が存在します（今後のリリースで完成予定）。
- process_priority や CPU affinity の設定は権限に依存するため、権限不足時は警告を出してスキップします。
- validate_config, config_setup, paper_verification_report はそれぞれ CLI として python -m で実行可能です。

Authors
- このリリースに含まれる実装は KabuSys 開発チームによるものです。

License
- 本プロジェクトのライセンス表記はリポジトリ内の LICENSE を参照してください。