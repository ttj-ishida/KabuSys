# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（初期リリース）から推測して作成されています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を追加。
- 環境・設定管理
  - `kabusys.config`:
    - .env ファイル自動ロード（プロジェクトルート判定: .git / pyproject.toml）。
    - 緩やかな .env パーサ（export 形式、クォート内のエスケープ、インラインコメント処理対応）。
    - 環境変数取得ラッパ（必須値チェック `_require`）、Settings クラス（各種パス・フラグ・閾値などのプロパティ）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `kabusys.config_setup`:
    - 対話式の .env 作成/更新ウィザード（`python -m kabusys.config_setup`）。
    - 各設定項目の説明・デフォルト・シークレットマスク表示、.env 書き込み機能。
- 設定検証 CLI
  - `kabusys.validate_config`:
    - .env および config/*.yaml の基本的な存在・整合性チェック。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、パスの親ディレクトリ確認、PyYAML 有無による YAML 検証スキップ、KABUSYS_ENV=live 時の追加ガード。
    - `--strict` オプションで警告を失敗扱いにする機能。
- 起動スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（`data/paper_trading.db`）を利用し、実口座と分離。
    - BrokerClientFactory を使ったブローカー抽象化。Engine の構成（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて別スレッドで実行。
    - 停止用フラグファイル（data/stop_requested.flag）検知により安全に停止可能。PID ファイル出力サポート。
  - `run_monitoring.py`:
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境に関わらず監視は本番用 `sqlite_path` を参照（監視データは単独 DB 想定）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）。不正値（0 以下や非数）は警告してデフォルトにフォールバック。
    - 停止フラグファイル検知によるループ終了。KeyboardInterrupt ハンドリングと DB クローズ処理。
- ログ・プロセス運用ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガー設定ユーティリティ。stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（既定ログディレクトリ: logs/、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定（high/normal/low）と CPU affinity 設定機能。
    - 権限不足や非対応環境では警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - シグナル選定 (`select_candidates`)、等重配分 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) の実装。スコア合計がゼロの場合は等金額配分へフォールバック。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中上限適用 (`apply_sector_cap`)。既存保有・価格情報を基にセクター超過を検出して候補を除外。
    - レジームに応じた投下資金乗数 (`calc_regime_multiplier`)（bull/neutral/bear マッピング、未知レジームは警告して 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 株数決定ロジック (`calc_position_sizes`)。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap とコストバッファを考慮したスケーリング、端数処理ロジックを実装。
- モニタリング・DB 初期化
  - `init_monitoring_db` 呼び出し箇所を run スクリプトで保証（監視テーブルの冪等初期化）。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite の履歴から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポートを出力。
    - 判定基準（閾値）を定義し PASS/FAIL を判定する CLI（`--from` / `--to` / `--db` オプション）。
- 研究用ファクター計算（部分実装）
  - `kabusys.research.factor_research`:
    - Momentum/Value/Volatility/Liquidity 等の計算方針と定数を定義。DuckDB 接続で prices_daily / raw_financials を参照する設計。モメンタム計算関数等を配置（本リリースでは一部実装途中の箇所あり）。

### Changed
- なし（初期リリースにつき履歴は新規追加のみ）。

### Fixed
- 環境変数パースの堅牢化:
  - `_parse_env_line` にて export プレフィックス、クォート内エスケープ、インラインコメントの取り扱いを強化。
- `MONITOR_POLL_INTERVAL` の不正値（非数・0 以下）に対して警告を出しデフォルト（60 秒）にフォールバックする挙動を実装。

### Deprecated
- なし

### Removed
- なし

### Security
- .env ファイルを生成する際に「.env は絶対に Git にコミットしないこと」を明記。
- 必須トークン等は Settings で必須チェックを行い、未設定時は明確なエラーを投げる実装。

### Known issues / Notes
- research/factor_research.py の一部関数が実装途中の痕跡（ファイル末尾付近に不完全な行）が見られます。実データでの使用前に実装の完成・テストが必要です。
- position_sizing の価格欠損時の扱い（price == 0.0 の場合）は TODO コメントあり。将来的にフォールバック価格（前日終値など）を導入する予定。
- process priority / cpu affinity の設定は OS や権限に依存し、失敗時は警告を出して処理を継続する設計です（完全な保証は行いません）。
- monitoring は環境にかかわらず本番用 sqlite_path を使用する設計上、本番 DB へのアクセスについて運用上の注意が必要です（paper_trading とは分離している箇所に注意）。

---

作成者注: 本 CHANGELOG は与えられたコードベースから推測して作成した初期リリース用の変更履歴です。実際のコミット履歴・バージョニング方針に応じて適宜更新してください。