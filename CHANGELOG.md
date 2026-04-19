# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。重要な変更点は日本語でまとめています。

※この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。

## [Unreleased]

- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用し本番 DB と分離して動作。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を開始。
    - 停止は data/stop_requested.flag により検知し、エンジン停止処理を行う。PID ファイルの管理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境に関係なく production の sqlite_path を使用する実装（本番 DB を参照する挙動に注意）。
    - 停止は data/stop_requested.flag により検知。

- 設定・環境周りのユーティリティ追加
  - config.py
    - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local 読み込みの優先度制御および OS 環境変数保護（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化が可能）。
    - .env 行のパースを堅牢化（export プレフィックス、クォート内エスケープ、インラインコメント等に対応）。
    - Settings クラスを提供し、各種環境変数（J-Quants、kabu API、DB パス、紙取引関連設定、監視閾値、ログレベルなど）をプロパティで取得。値検証（例：KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - シークレット項目は入力時マスク、既存 .env 読み込み、保存前の確認をサポート。
  - validate_config.py
    - 起動前に設定不備を検出する CLI。
    - 必須環境変数の未設定チェック、プレースホルダ値チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML が無ければパース検証をスキップ）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- 監視/検証ツール追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を集計して検証レポートを出力する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数など。
    - 基準値（閾値）定義を含み、PASS/FAIL 判定を行う。日付フィルタ（--from/--to）対応。

- ポートフォリオ構築関連モジュール追加
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - Unknown セクターの扱い、レジームが未知の場合のフォールバック挙動（1.0）などを定義。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジック（risk_based / equal / score）を実装。
    - lot_size（単元）丸め、1銘柄上限・合計投下上限（aggregate cap）対応、cost_buffer を用いた保守的見積り、スケーリングと端数配分ロジックを導入。

- ユーティリティ追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定で 30 日保持）を設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR 環境変数、引数からの上書きに対応。ログディレクトリ作成失敗時は安全にフォールバックしてコンソール出力のみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を提供。
    - psutil を利用し、権限不足や未サポート OS の場合は警告を出してスキップ。

- 研究用モジュール（初期実装）
  - research/factor_research.py
    - ファクター計算モジュールのスキャフォールド（モメンタム等の定義、定数、calc_momentum の骨組み）。DuckDB 経由で prices_daily / raw_financials を参照してファクターを算出する設計。

- パッケージメタ情報
  - __init__.py にてバージョンを 0.1.0 に設定し、主要サブパッケージを __all__ に追加。

### Changed
- 監視 DB 初期化
  - 起動スクリプト（run_monitoring, run_execution）ともに monitoring 用テーブルが存在することを保証するため init_monitoring_db を呼び出すように（冪等的な初期化）。
- ロギング動作の統一
  - すべての起動スクリプトで setup_logging を呼び出し、ログ出力方法を統一。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてクォート内部のバックスラッシュエスケープやインラインコメントの扱いを改善。export プレフィックス対応など、.env の柔軟な記述に耐えるよう改善。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

補足・注意点（コードから推測）
- Monitoring は run_monitoring のコメントにもある通り「KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」実装になっているため、開発環境で実行する際は監視対象 DB の確認に注意してください。
- run_execution は paper_trading モードで paper_sqlite_path を用いるため、ペーパートレードと本番 DB は分離されます。デフォルトパスは data/paper_trading.db（環境変数で上書き可）。
- process_priority / set_cpu_affinity は psutil に依存し、権限不足時に例外を投げずログ警告でスキップする設計です。
- config_setup により生成される .env ファイルは機密情報を含むため、リポジトリへコミットしないよう注意喚起が明示されています。

以上。追加で差分ごとの詳細なコミットメッセージや影響範囲を推測して追記することも可能です。必要であれば特定モジュールごとの変更点をより詳細に分解して記載します。