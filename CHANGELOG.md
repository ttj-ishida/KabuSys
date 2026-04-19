# Changelog

すべての変更は「Keep a Changelog」準拠の形式で記載しています。  
このファイルはコードベースの現状（ソースコードから推測可能な機能・振る舞い）に基づいて作成された初回のリリースノートです。

フォーマット:
- Unreleased: 今後の変更用
- 各バージョン: 追加/変更/修正/削除/セキュリティに分類して記載

## [Unreleased]
- なし（初回リリースに向けた状態）

## [0.1.0] - 2026-04-19

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数/設定読み込みモジュール `kabusys.config` を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env ファイル自動読み込み（`.env` → `.env.local`、OS環境変数を保護）。
    - .env のパースは export 記法、クォート、エスケープ、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスで各種設定取得メソッドを提供（DB パス、API トークン、ログレベル、環境判定、Paper Trading 関連など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）および is_live/is_paper/is_dev プロパティ。

- 設定作成ウィザード
  - `kabusys.config_setup`：対話式 .env 生成/更新ウィザードを提供。
    - デフォルト値・選択肢・シークレット入力対応。
    - `.env` の読み込み/書き込み機能（テンプレート付き）。
    - 保存確認・キャンセル機能。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前チェックツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリの存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければスキップして警告）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行/監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（`kabusys.utils.process_priority` を使用）。
    - 環境に応じて paper_trading 用の SQLite を使用（`PAPER_TRADING_SQLITE_PATH` / Settings.is_paper）。
    - ブローカークライアント生成（`BrokerClientFactory`）、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）検知で安全に停止。
    - エンジン実行は別スレッドで行いメインスレッドから監視・停止制御を行う。
    - 実行時の pid ファイル出力をサポート（`data/execution.pid` デフォルト）。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを永続化。
    - 起動時にプロセス優先度を "high" に設定。
    - stop flag による優雅な終了処理、KeyboardInterrupt での終了処理を実装。
    - sqlite3 / duckdb 両方のコネクション管理（起動時に monitoring テーブルの初期化を行う）。

- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`：
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30世代保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数による設定解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`：
    - cross-platform（Windows / POSIX）でプロセス優先度設定を提供（psutil を使用）。nice 値 / Windows 優先度クラスを抽象化。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を実装。
    - パーミッション不足や未対応 OS では警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates（スコア降順・タイブレークルール）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分へフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap（既存保有に基づくセクター集中制限、unknown セクターは制限対象外）、calc_regime_multiplier（bull/neutral/bear の乗数）。
    - 未知レジームは警告と共に 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes：allocation_method に応じた発注株数計算（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に対するスケールダウンと残差処理（残余キャッシュによる lot 単位の追加配分）を実装。
    - cost_buffer による手数料/スリッページ見積り考慮。
    - 一部将来的拡張（銘柄別 lot_size 等）について TODO を記載。

- リサーチモジュール（ファクター計算）
  - `kabusys.research.factor_research`：
    - モメンタム等の定量ファクター計算用モジュールの骨格を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する想定）。
    - 設定済みの計算窓（1M/3M/6M、MA200、ATR20、Volume 20日等）を定義。
    - 実装の一部（関数の途中まで）を含む（今後完成予定）。

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等。
    - Pass/Fail 判定閾値を定義（稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。
    - P95 計算、欠損データ時の N/A 表示を実装。

- パッケージ初期化
  - `kabusys.__init__` で基本的な __all__ エクスポート設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

## 既知の注意点 / TODO（コードから推測）
- 一部モジュール（factor_research）の実装が途中で終わっており、完全なファクター計算ロジックは未完。
- position_sizing 内で価格が欠損（0.0）だった場合のフォールバック処理は TODO コメントあり（前日終値等のフォールバック検討）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で動作しない場合がある（警告でスキップ）。
- logging_setup はログディレクトリ作成失敗時にファイルロギングを無効化するが、その旨は stderr/ログにしか出力されない。
- monitoring は常に Settings.sqlite_path（本番 DB）を使用するため、開発中は誤って本番 DB を破壊しないよう注意が必要。paper_trading の場合、Execution は専用の paper_sqlite_path を使用して本番 DB と分離する設計。

---

参考:
- 環境変数関連:
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
  - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB）
  - PAPER_FILL_MODE（paper_trading の約定モード）
  - KABUSYS_ENV / LOG_LEVEL / LOG_DIR / KILL_FLAG_CLEAR_ON_START
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読み込み停止）

（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴管理にはコミットログ・リリースタグを併用してください。）