# Changelog

すべての注記は Keep a Changelog のガイドラインに準拠します。  
このファイルは主にコードベースの現状から推測した変更・追加点を記載しています。

- Unreleased
  - なし

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションパッケージ KabuSys を追加
  - バージョン定義: `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。

- 環境設定関連
  - Settings クラス（`src/kabusys/config.py`）
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env/.env.local の読み込み順序と OS 環境変数の保護機能を実装。
    - 多数のプロパティ（J-Quants, kabuAPI, DB パス, paper trading 設定, 監視しきい値等）を提供し、値検査（有効値チェック・型変換）を行う。
  - 環境変数パーサの強化
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応した .env パーサを実装。

- 設定ユーティリティ CLI
  - 環境設定ウィザード（`src/kabusys/config_setup.py`）
    - 対話式で .env を生成・更新するウィザードを提供。
    - 保存プレビュー、シークレットマスク表示、デフォルト値・選択肢のサポートを実装。
  - 設定検証ツール（`src/kabusys/validate_config.py`）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML インストール有無に応じて）を行う CLI。
    - `--strict` フラグで警告も失敗扱いにできる。

- 実行用スクリプト
  - 監視ループ起動スクリプト（`src/kabusys/run_monitoring.py`）
    - SystemMonitor を定期ポーリングで実行するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境に関係なく本番用 sqlite_path を使用する仕様（冪等に監視 DB を初期化）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止を実装。
  - ExecutionEngine 起動スクリプト（`src/kabusys/run_execution.py`）
    - 実際の発注実行を行う ExecutionEngine を起動するエントリポイント。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して paper_trading 用 DB（デフォルト: data/paper_trading.db）に完全分離して記録。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグと PID ファイルによるプロセス管理、daemon スレッドでの実行と安全停止の実装。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入（utils を利用）。

- 監視 DB 初期化
  - `src/kabusys/monitoring/monitoring_db.py` 経由で監視テーブルを冪等に作成する初期化処理を呼び出す（run_monitoring / run_execution を通じて利用）。

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポートを SQLite DB から生成する CLI。
    - 稼働率、注文成功率（Fill rate）、送信率（Send rate）、リスク却下数、API レイテンシ（平均/最大/P95）などの集計と PASS/FAIL 判定を実装。
    - P95 算出、日付フィルタ（--from / --to）、DB パスの引数/環境変数対応、閾値定義を含む。

- ポートフォリオ構築ライブラリ（純関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレークルール）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限適用 apply_sector_cap（売却予定銘柄除外、unknown セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - position sizing ロジック（risk_based / equal / score の配分方式）。
    - 単元株（lot_size）丸め、per-stock 上限と aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料/スリッページ見積）を考慮したスケーリング＆端数配分アルゴリズムを実装。

- リサーチ / ファクター計算
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して Momentum / Volatility / Liquidity / Value 系ファクターを計算する設計（calc_momentum, calc_volatility 等）。
    - MOMENTUM（1M/3M/6M/MA200乖離）、ATR（20 日）、20 日平均出来高などを SQL+Python で算出する実装。
    - データ不足時は None を返す扱い（安全な欠損処理）。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（`src/kabusys/utils/process_priority.py`）
    - set_process_priority(level) — Windows / POSIX（Linux, macOS, FreeBSD）に対応し、psutil を用いて優先度を設定。権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数で CPU affinity を固定。不正値チェックと例外ハンドリングを実装。

### Changed
- （初期リリースのため主に追加。既知のデフォルト設定を明示化）
  - 監視・実行スクリプトは起動直後にプロセス優先度を "high" に設定するように統一。
  - 監視では MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を柔軟に変更可能（不正値は警告してデフォルト 60 秒にフォールバック）。
  - run_execution の RiskManager 初期設定（デフォルトパラメータ）をコード内に明記（max_position_pct, max_utilization, rate_limit_per_sec 等）。

### Fixed
- N/A（初期リリース。実装段階で想定されうる例外処理やフォールバックを明示的に実装）
  - .env 読み込み失敗時に警告を出すようにしてプロセスが停止しない挙動を確保。
  - psutil による優先度設定で権限不足や未実装メソッドに対して警告を出すよう例外ハンドリングを追加。

### Removed
- N/A

### Security
- 環境変数に秘密情報を含むフィールド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は Settings/API 層で直接取得する設計。config_setup では .env に書き込む際に注意喚起コメントを追加（.env を絶対に Git にコミットしない旨）。

---

注記:
- ここに記載した項目は現行コードの構成・ドキュメント文字列・実装（関数名・引数・デフォルト値）から推測してまとめたものです。テストや外部モジュール（monitoring.system_monitor 等）の実際の実装詳細は別途参照してください。
- 今後のリリースではテスト状況、互換性（BREAKING CHANGES）、追加された CLI オプションやパラメータの変更などを明示してください。