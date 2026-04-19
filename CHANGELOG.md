Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリースを追加。
- 実行用スクリプト:
  - run_execution.py
    - ExecutionEngine 起動エントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - Engine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視 DB を一元管理）。
    - 起動時にプロセス優先度を "high" に設定。
    - data/stop_requested.flag で監視ループの終了を検知。
- 環境設定 / 検証:
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。環境変数の保護（OS 環境を上書きしない / .env.local による上書き）をサポート。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、環境モード、閾値など）を取得・バリデーション。
    - PAPER_FILL_MODE などの列挙的設定の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。既存値の再利用、シークレットマスク表示、保存確認をサポート。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML がある場合）などを検証。--strict で警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）:
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタ（既存ポジションを考慮）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値はフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ保守見積り）を実装。
    - TODO: 将来的に銘柄毎の lot_size をサポートする旨の注釈を追加。
- ユーティリティ:
  - utils/logging_setup.py
    - 共通のログ初期化関数 setup_logging を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。ログディレクトリ作成に失敗してもフォールバックしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）と CPU affinity 設定を抽象化。Windows / POSIX の差を吸収し、アクセス権限がない場合は警告を出してスキップ。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。指定期間（--from / --to）または DB 全体を対象にシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を計算して判定（PASS/FAIL）する。
    - P95 パーセンタイル計算、閾値（稼働率 99%、注文成功率 90% など）を定義。
- データリサーチ:
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム等のファクターを計算するモジュール骨子を追加。モメンタム期間や ATR 等の定数を定義し、calc_momentum の実装を開始（一定のスキャン範囲バッファ等を考慮）。
    - （注）このファイルは一部実装が継続中（ソース末尾に未完の記述あり）。
- パッケージメタ:
  - __init__.py にてバージョン __version__="0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Changed
- n/a（初回リリース）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / Known limitations
- factor_research.py の一部関数（calc_momentum 以下）は実装途中の箇所があり、追加実装が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0 や None）の場合には該当銘柄をスキップする設計。将来的に価格フォールバック（前日終値など）を導入する予定。
  - lot_size は現状グローバル固定。銘柄別単元数サポートは TODO。
- apply_sector_cap: "unknown" セクターは上限適用除外となるため、マスタ不整合に注意。
- ログディレクトリ / ログファイル作成に失敗した場合、ファイル出力はスキップされコンソール出力のみで継続する設計（運用時に権限・パスを確認すること）。
- run_monitoring / run_execution は stop フラグ（data/stop_requested.flag）および PID ファイル / kill flag により外部からの制御を想定。

Upgrade / Migration
- 初回リリースのため特別な移行手順はありません。実運用前に validate_config.py で設定チェックを行ってください。

Authors
- KabuSys 開発チーム（リポジトリ内モジュールに基づき推測して記載）

License
- ソース内に明示的なライセンス記載はありません。配布・運用の前にライセンスを確認してください。

<!-- EOF -->