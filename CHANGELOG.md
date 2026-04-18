CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のフォーマットに準拠しています。日付は YYYY-MM-DD 形式です。

Unreleased
----------

- （現在のコードベースに基づく未リリースの差分はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークのコア機能を追加。
- 実行用スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により実運用用ブローカー／モックブローカーを切り替え可能。
    - ExecutionEngine の起動前に stop フラグを確認し、スレッドでの実行と停止処理を実装。
    - エンジン稼働中は execution.pid を利用。
- 監視用スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関係なく本番用 sqlite_path を使用する旨の実装。
    - 停止フラグによる安全停止、例外キャッチして次回ポーリングまで継続。
- 設定管理
  - config.py: 環境変数読み込み・ラッパー Settings を実装。
    - 自動 .env 読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。.env と .env.local の優先度制御、OS 環境変数の保護（上書き不可）。
    - .env の行パーサは export プレフィックス・クォート・エスケープ・インラインコメントに対応する堅牢実装。
    - 各種設定プロパティ（DB パス、LINE トークン、監視閾値、環境種別チェック等）を提供。
- 設定関連 CLI
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを追加。
    - 秘匿項目のマスキング表示、選択肢／デフォルトサポート、保存確認、テンプレート書き出し。
    - .env に秘匿情報を残さない旨の注意文を出力。
  - validate_config.py: 起動前設定検証ツールを追加。
    - 必須 / 任意の環境変数チェック、KABUSYS_ENV 値チェック、DB パスと親ディレクトリの存在チェック、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）を root ロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度設定・CPU affinity ユーティリティを追加。
    - Windows と POSIX の差分を吸収（psutil の存在しない定数は getattr でフォールバック）。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(N) を提供。権限不足時は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: apply_sector_cap, calc_regime_multiplier を実装。
    - セクター集中上限ロジック（sell_codes を考慮、"unknown" セクターは除外しない）。
    - レジーム乗数（bull/neutral/bear）と未知レジームのフォールバック（警告）。
  - portfolio/position_sizing.py: calc_position_sizes を実装。
    - 複数の allocation_method（risk_based / equal / score）をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を用いた保守的コスト見積もり、残差処理による追加配分ロジックを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。paper_trading DB から各種指標（稼働率、fill/send 率、レイテンシ、リスク却下数等）を集計して人間向けレポートを出力。
    - P95 計算、期間フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
- DuckDB 統合
  - スクリプト類および research モジュールで DuckDB コネクション受け渡しをサポート（分析用データ格納に利用）。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- 設計／挙動に関する注意
  - 監視（run_monitoring）は環境変数 KABUSYS_ENV に依らず本番用 sqlite_path を使用する設計（監視データは環境混在を避けるため）。
  - run_execution は paper_trading 環境時に DB を明確に分離することで、ペーパートレードと本番のデータ隔離を明示的に実現。
- ログ設定
  - StreamHandler は stdout を使用（cron / scheduler から stdout/stderr を統一して扱えるようにする意図）。

Fixed
- .env 読み込みの堅牢化
  - export プレフィックス・引用符・バックスラッシュによるエスケープ・インラインコメントのパースに対応し、不正な行をスキップすることで自動読み込みの誤動作を軽減。

Deprecated
- なし

Removed
- なし

Security
- .env の取り扱いに関する注意を明示
  - config_setup にて .env を絶対に Git にコミットしない旨を出力。

Notes / Known limitations
- research/factor_research.py はモジュール構成と設計を含む実装が含まれるが、ファイル末尾で calc_momentum の実装が途中で切れており未完（今後の実装・テストが必要）。
- position_sizing の価格フォールバックは TODO コメントあり（価格欠損時の過少見積り問題に対処するための拡張が必要）。
- 一部の機能（ExecutionEngine や SystemMonitor 内部、BrokerClient 実装など）はこの差分での参照のみで、別ファイルに本体が存在する想定（初期リリースでは統合テストが必要）。
- YAML 検証は PyYAML がインストールされていない場合スキップされるため、CI 等で厳密にチェックする場合は依存を明示することを推奨。

Authors
- KabuSys 開発チーム（コードベースから推測して作成）

README やドキュメント（CONTRIBUTING.md 等）に設定手順、.env の作成、実行方法（run_execution/run_monitoring）、ログ配置や Paper Trading の流れを追記することを推奨します。