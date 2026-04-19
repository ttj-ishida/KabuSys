CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
形式は "Keep a Changelog"（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 初回リリースを公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）を監視し、検出時に安全に停止する仕組みを実装。実行中のエンジンはスレッドで稼働し、停止フラグを検知すると engine.stop() を呼ぶ。
    - 実行用 PID ファイル（data/execution.pid）を扱う設定を追加。
    - DuckDB を分析用 DB（設定値で指定可能）として接続。
- 監視スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒、無効値は警告出力してデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する方針で実装。
    - 停止フラグ（project/data/stop_requested.flag）でループ停止。
    - 例外捕捉で poll ごとの事故耐性を確保（check_once() の例外はログ出力して次回まで待機）。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - 環境変数取得ユーティリティ Settings クラスを提供（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 関連設定等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のプロパティ実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 各設定項目のプロンプト、既存 .env 読み込み、マスクされたシークレット表示、保存確認を実装。
  - validate_config.py
    - .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや YAML ファイルの存在・パースチェック、live 環境時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコア全て 0 の場合のフォールバック（等金額配分）で警告ログを出力。
  - risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄を露出計算から除外可能）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップ、未知レジームは 1.0 でフォールバック）。
    - 既存ポジションの時価計算に price_map を使用、価格欠損時の注意点を TODO に明記。
  - position_sizing.py
    - ポジションサイズ決定ロジック calc_position_sizes を実装（risk_based / equal / score モード対応）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）でのスケールダウン、cost_buffer を用いた保守的コスト見積り、残差処理ロジックを実装。
    - TODO: 将来的に銘柄別 lot_size 対応の拡張を検討する旨を記載。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、ディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を考慮。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定関数を実装。
    - 権限不足や未対応環境では警告を出して安全にスキップする。
- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB 経由で定量ファクター（Momentum / Value / Volatility / Liquidity）を計算するモジュールを追加（設計方針と定数の実装）。モメンタム計算関数の骨格を含む。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計・閾値判定を実装し、PASS/FAIL 判定を出力。
    - --from/--to/--db オプションで期間と DB を指定可能。DB が存在しない場合のエラーメッセージを実装。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

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

Notes / Known limitations
- run_monitoring は意図的に KABUSYS_ENV に依存せず本番 sqlite_path を使う設計上の決定があるため、開発環境で監視を分離したい場合は監視用 sqlite パスを手動で上書きする必要がある点に注意してください。
- position_sizing と risk_adjustment の一部ロジックは価格欠損時のフォールバック（前日終値や取得原価の利用）を未実装で、将来の改善項目として TODO に記載されています。
- process_priority や CPU affinity の設定は権限や OS に依存するため、失敗時は警告出力して継続する実装です。
- research/factor_research の実装はいくつかの関数で部分的な実装（骨格）を含むため、完全なデータフローの検証が必要です。

Contributing
- 変更の提案やバグ報告はリポジトリに Issue を立ててください。開発用の .env を作成するには python -m kabusys.config_setup を利用し、設定検証は python -m kabusys.validate_config を実行してください。