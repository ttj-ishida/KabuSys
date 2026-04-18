# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
本プロジェクトはセマンティックバージョニングを採用しています。

なお、この CHANGELOG は提供されたコードベースの内容から機能追加や振る舞いを推測して作成しています。

## [Unreleased]

### Known issues
- research/factor_research モジュールの calc_momentum 関数定義が途中で切れており（ファイル末尾が不完全）、ファクター計算の一部が未実装 / 作業中になっています。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。
    - KABUSYS_ENV に応じて Paper Trading 用の DB を分離（paper_trading の場合は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory を用いて実運用/モックのブローカークライアントを注入。
    - ExecutionEngine をデーモンスレッドで実行・停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_monitoring.py: システム監視（SystemMonitor）ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用して監視データを記録する設計。
    - 停止フラグ（data/stop_requested.flag）検出で優雅にループを終了。
- 設定管理 / ユーティリティ
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出。.git または pyproject.toml を基準）。
    - 自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 複雑な .env パースロジック（export プレフィックス、シングル/ダブルクォート対応、エスケープ、コメント処理）を実装。
    - 各種設定項目（DB パス、J-Quants/kabuAPI 設定、Paper Trading 設定、監視しきい値など）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（有効値チェック）や KABUSYS_ENV/LOG_LEVEL の検証を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - デフォルト値表示、シークレット入力マスク、既存 .env 読み込み、保存機能を提供。
    - .env ファイルの書式をテンプレートとして生成。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテート、30世代保持）を統一的に設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を用いることでスケジューラや cron からのリダイレクト運用を考慮。
  - utils/process_priority.py:
    - Windows と POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する関数を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時に警告を出し安全にフォールバックする実装。
- ポートフォリオ構築関連（純粋関数群、DB を参照しない）
  - portfolio/portfolio_builder.py:
    - 銘柄候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を検査し、上限超過セクターの新規候補を除外するロジックを実装（unknown セクターは制約対象外）。
    - calc_regime_multiplier: market レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - 各配分方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した保守的見積り、端数処理を実装。
    - price が無効な場合のスキップやログ出力を考慮。
- 解析 / レポートツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率（fill/send）、リスクによる却下、レイテンシ（平均/最大/P95）を集計・評価。
    - 基準値（稼働率 99% など）を設定し、PASS/FAIL を判定して標準出力に整形レポートを出力。
    - DB パスは CLI --db オプション / PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
- データ分析基盤
  - DuckDB を分析用に採用（duckdb 接続を受ける設計）。実行・監視スクリプト双方で duckdb 接続を確立する実装。

### Changed
- なし（初回リリース相当のため具体的な「変更」はなし、実装された機能群を列挙）。

### Fixed
- なし（初回リリース相当のため修正履歴なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数のシークレットは config_setup の表示でマスクし、.env の Git コミット禁止をドキュメントに明記するなど運用上の注意喚起を追加。

---

開発・運用に関する補足:
- .env 自動ロードはプロジェクトルートの検出に依存しており、パッケージ配布後も CWD に依存せず動作するよう設計されています。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意しています（テスト用途など）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されますが、ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- run_monitoring は監視データの記録に本番用 SQLite（settings.sqlite_path）を使う点に注意してください（意図的な設計）。
- run_execution は paper_trading の場合、Paper 用 DB に完全に分離して記録する設計になっており、実運用データと混在しないようになっています。

もし CHANGELOG に追記・修正したい点（例えばリリース日、既知の不具合の扱い、細かな実装差分の強調など）があれば指示してください。