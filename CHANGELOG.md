CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース日付はソースコードから推測した最新更新日を使用しています。

Unreleased
----------

- 現時点で未リリースの小修正やドキュメント改善を予定しています。

0.1.0 - 2026-04-23
------------------

Added
- 初回公開リリース: KabuSys — 日本株自動売買システムのコアモジュール群を追加。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
- 実行用エントリスクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient を利用する。停止フラグ、PID 管理、スレッド実行の監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- 設定・環境管理:
  - config.py: .env 自動ロード、.env の柔軟なパース（export 形式、クォート、インラインコメントの扱い）、Settings クラス（環境変数のラッパー）を実装。各種検証（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証、パス系のプロパティなど）を提供。
  - config_setup.py: .env を対話式で作成・更新するウィザード（既存値の再利用、シークレットマスク表示、保存時確認）を追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。--strict オプションで警告を fail 扱いにできる。PyYAML 未インストール時のスキップ・警告や本番環境向けチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実装。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。stdout へ出力する StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。LOG_DIR 作成失敗時はファイル出力をフォールバック。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。権限不足時に安全にフォールバックして警告を出力。
- ポートフォリオ構築モジュール（純粋関数群）:
  - portfolio/portfolio_builder.py:
    - select_candidates(): スコア降順、同点は signal_rank でブレークする候補選定。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重の重み計算。全スコアが 0 の場合は警告を出して等重にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中上限チェック（既存保有時価ベース）と新規候補の除外。"unknown" セクターは除外対象外とする仕様。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): risk_based / equal / score の配分方式を実装。損切り率・lot_size（単元）丸め、max_position_pct / max_utilization の考慮、cost_buffer を加味した aggregate cap のスケーリングと残差処理（lot 単位での再配分）を実装。
- 解析・リサーチ補助:
  - research/factor_research.py（ファクター計算フレームワーク）: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等を計算する設計を導入（モジュール冒頭に設計方針と定数を明記）。モメンタム計算関数のインターフェースが追加（実装途中の箇所あり）。
- ユーティリティ・ツール:
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（デフォルトしきい値をスクリプト内定義）。--from/--to/--db オプションをサポート。

Changed
- run_monitoring と run_execution の挙動:
  - どちらも起動直後にプロセス優先度を "high" に設定するよう調整。
  - run_execution は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離するように実装。
- ログ挙動:
  - logging_setup はデフォルトで stdout を使用（stderr ではない）し、ログディレクトリ作成に失敗した場合に console-only にフォールバックする堅牢性を追加。
- .env 自動ロード:
  - プロジェクトルートの判定を .git または pyproject.toml で行い、テストや特殊ケース向けに KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能にした。

Fixed
- .env パーサにおける実用性向上:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理することで現実的な .env ファイルを正しく読み込めるようにした。
- run_monitoring のポーリング間隔取得:
  - MONITOR_POLL_INTERVAL の値が不正（文字列や 0 以下）だった場合にデフォルトにフォールバックし、ログで警告を出すように改善（time.sleep に負の値を渡さないよう保護）。

Security
- .env 取り扱いに関する注意喚起を config_setup に明記（.env を Git にコミットしない旨のヘッダを追加）。
- config.validate の本番チェックで LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険値を警告。

Documentation
- 各モジュールに docstring を充実させ、使用方法・設計方針・引数/戻り値仕様・注意点（例: price 欠損時の TODO）を明記。
- config_setup と validate_config に CLI の使い方・オプション例を追加。

Known issues / Notes
- research/factor_research.py の一部（calc_momentum 以降）は実装途中の箇所があり、Full なファクター計算は今後の作業が必要。
- calc_position_sizes の lot_size は現状全銘柄共通の固定値（デフォルト 100）。将来的に銘柄毎の lot_map に対応することがコメントで検討されている。
- apply_sector_cap の説明にある通り、price_map に 0.0 が含まれる場合にエクスポージャーが過少見積りされる可能性があり、将来的なフォールバック価格導入が注記されている。

リリースノートについて不明な点や、より詳細な変更点（コミット単位、差分）を希望される場合は、その旨をお知らせください。