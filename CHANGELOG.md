CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。
本ファイルは Keep a Changelog の形式に準拠しています。
タグは semantic versioning に基づきます。

[Unreleased]
------------

- なし（次のリリースにて反映予定）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション公開
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` としてリリース。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止判定にプロジェクト直下の data/stop_requested.flag を使用。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用の SQLite（data/paper_trading.db）を使用し MockBrokerClient を利用することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。停止時は execution.pid / stop flag を参照して安全に停止処理を行う。

- 設定管理・ウィザード・検証
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env/.env.local の自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .git または pyproject.toml を基にプロジェクトルートを自動検出。
    - .env の各行パーサを実装。export プレフィックスやシングル/ダブルクォート、インラインコメント、エスケープシーケンス等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値 等）。PAPER_FILL_MODE のバリデーション実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE 設定 / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env を読み込み、既存値の再利用やシークレットマスキングに対応。
    - 保存時のテンプレートコメント付き書き出しを実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML 未インストール時はスキップ）、本番用ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点のタイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中度による候補除外ロジック。sell_codes を除外して計算できる。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告後に 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジック。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積もり）反映、残余キャッシュに基づく端数配分の再配分ロジックなどを実装。

- ユーティリティ
  - utils.logging_setup: 統一的ログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler・30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。
    - Windows/Linux/macOS（対応OS）で適切な優先度を設定し、失敗時は警告でスキップ。
    - set_cpu_affinity によるプロセスを最初の N コアに固定する機能を提供（例外ハンドリングあり）。

- ツール
  - tools.paper_verification_report: Paper Trading 向け検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（環境変数）または --db で DB 指定可能。
    - システム安定性（稼働率 / ポーリング数）、注文成功率（Created/Filled/Sent）、リスク却下数、API レイテンシ（avg/max/P95）を集計して出力。
    - デフォルトの合格基準を設定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - P95 計算、日付フィルタリング、欠損テーブルに対するフォールバック処理を実装。

- リサーチ（部分追加）
  - research.factor_research: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクター計算する設計（実装途中でトランケートあり）。

Changed
- DB 周りの扱い
  - 監視（monitoring）は KABUSYS_ENV に依存せず本番 sqlite_path を使用する方針を明示。
  - run_execution は paper_trading 時に paper_sqlite_path を使用して本番データと完全分離。

Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてクォート内のバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応を実装し、.env 読み込みの信頼性を高めた。
- ログディレクトリ作成失敗時のフォールバック処理を追加（ファイルハンドラが作れない場合でもコンソールログ継続）。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- research.factor_research の実装は一部でトランケートされており、完全なファクター計算ロジックは今後のリリースで完了予定。
- position_sizing や apply_sector_cap は入力データ（価格や sector_map）が欠損する場合に保守的にスキップやフォールバックする実装だが、将来的により厳密なフォールバック（前日終値やマスタ参照）を導入する余地がある。
- 一部機能（例: BrokerClientFactory の Mock/実ブローカーの挙動、ExecutionEngine の詳細）は実際のブローカー接続に依存するため、本番運用前にステージングでの十分な検証を推奨。

References
- 実行例や CLI の使い方は各モジュール冒頭の docstring / help を参照してください（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。

--- 
（この CHANGELOG はコード内容から推測して作成しています。細部は実際の開発履歴に応じて調整してください。）