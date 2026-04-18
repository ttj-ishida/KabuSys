Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md
=============

すべての注記はソースコードから推測して記載しています。

Unreleased
----------

なし

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - パッケージ初期リリース。バージョンは __version__ = "0.1.0"。
  - CLI/ユーティリティ、ポートフォリオ構築、実行エンジン起動、監視、調査ツール等の基礎機能を実装。

- 設定管理
  - 環境変数自動読み込み実装（.env / .env.local）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの実装（export プレフィックス対応、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等）。
  - Settings クラスを実装し、アプリで使用する各種設定をプロパティ経由で取得可能にした。
    - J-Quants / kabu API 用トークン/パスワード、DB パス（DuckDB / SQLite）等。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証とデフォルト（"instant"）。
    - PAPER_TRADING 用 SQLite のデフォルトパス: data/paper_trading.db。
    - 監視用 PID / Kill Flag 関連設定、CPU/Memory/Disk のデフォルトしきい値（コード内デフォルト値あり）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値チェック）。
  - settings インスタンスの提供。

- 設定ユーティリティ
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 秘匿入力のマスク、選択肢サポート、既存 .env の読み込み／再利用機能。
    - --env-file で保存先指定可能。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML 未インストール時はスキップ警告）。
    - KABUSYS_ENV=live の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の注意表示）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行 / 監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離（MockBrokerClient を使用する想定）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）を検知して安全に停止。PID ファイル出力サポート。
    - RiskManager のデフォルト設定（max_position_pct=0.20 等）を実装し、初期ポートフォリオ値は broker.get_available_cash() を参照。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（monitoring DB 初期化を保証）。
    - duckdb への接続確立、SystemMonitor.check_once() を定期実行。例外はログ出力して次回ポーリングまで継続。
    - 停止フラグ検出でループを終了、KeyboardInterrupt もハンドリング。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 関数引数に基づき解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py を追加。
    - set_process_priority(level) で Windows / POSIX を吸収した優先度設定を実装（psutil ベース）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を設定（存在しない場合や権限不足時は警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）に基づいて候補を除外。sell_codes により当日売却予定を除外可能。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0/neutral=0.7/bear=0.3）。未知レジームは 1.0 へフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）適用時のスケーリングと余りの配分ロジックを含む。
    - cost_buffer による手数料・スリッページの保守的見積り、価格欠損時のスキップ、各種パラメータは引数で調整可能。
  - portfolio/__init__.py で主要 API をエクスポート。

- 調査 / レポート
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を読み、稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - P95 計算、日付フィルタ（--from / --to）、DB の存在チェックとエラーメッセージを実装。
    - 基準値（稼働率 99%, 成功率 90% など）に基づいて PASS/FAIL 判定を出力。

- リサーチ（未完）
  - research/factor_research.py を追加（モメンタム等のファクター計算基盤を開始）。
    - 各種定数（モメンタム窓、MA200、ATR 等）と calc_momentum の実装を着手（ソースは途中で切れているため、完全実装は今後）。

Changed
- 初回リリースにつき該当なし（初期追加のみ）。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意点（コードから推測）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しない。ルートが特定できない場合は自動ロードをスキップする。
- .env の自動ロードは OS 環境変数を保護（.env.local の override でも OS 環境変数は上書きされない）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出して 60 秒にフォールバックする（time.sleep に負の値を渡さないため）。
- ログ出力は標準出力（stdout）に出す設計のため、cron 等で stdout/stderr を一本化してリダイレクトした運用に向く。
- process_priority / cpu_affinity は権限不足や未対応 OS で例外を投げずに警告を出して処理をスキップする実装になっている。
- research/factor_research.py は calc_momentum の実装が途中で終わっているため、完全なファクター計算はまだ作業中。

今後の追加候補（推測）
- research/factor_research.py の完了（DuckDB を使ったファクター計算全実装）。
- SystemMonitor / ExecutionEngine 周りの単体テストとエンドツーエンドテスト補強。
- strategy / data パッケージの追加実装（現状は純粋関数群が中心）。
- ロギングやメトリクスの強化（構造化ログ、外部監視連携等）。

以上。必要であれば各項目の英語版や、より細かいファイル毎の変更履歴（コミット単位での想定）も作成します。