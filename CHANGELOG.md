# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（実装内容に基づく要約）。  

なお、リリース日はコードベース作成時点（本ファイル作成時）を使用しています。

## [0.1.0] - 2026-04-19

### Added
- アプリケーション骨格を初期実装
  - パッケージ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` を追加。
- 実行用スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用する旨をサポート。
    - プロセス優先度を起動直後に "high" に設定。
    - 停止フラグファイル（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）を用いた起動/停止制御を実装。
    - BrokerClientFactory を通じたブローカークライアントの抽象化、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager に渡すデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor 用ポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時は警告を出してデフォルトにフォールバック。
    - 監視は環境に依らず本番の `sqlite_path` を使用する旨を明記（監視データは一貫した DB に保存）。
    - 停止フラグ検知でループを終了する制御を実装。
- 設定管理
  - `src/kabusys/config.py`
    - Settings クラスを実装し、環境変数から各種設定を取得する API を提供（J-Quants / kabuAPI / DB パス / モード判定 /閾値など）。
    - `.env` 自動読み込み機能を提供（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。優先順位: OS環境 > .env.local > .env。
    - `.env` 自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
    - `.env` 値の厳密チェック（`PAPER_FILL_MODE` の有効値チェック、`KABUSYS_ENV`/`LOG_LEVEL` の検証）を実装。
- 設定ユーティリティ / ウィザード / 検証
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を生成・更新する CLI を実装。
    - シークレット値は表示をマスクして確認可能。`.env` のテンプレート的出力機能を持つ。
  - `src/kabusys/validate_config.py`
    - 起動前に `.env` と `config/*.yaml` を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML 利用可時）などを実施。`--strict` で警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定する共通ユーティリティを実装。
    - LOG_DIR が作成できない場合はファイル出力をスキップしてコンソール出力のみ継続する堅牢性を実装。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を明示。
  - `src/kabusys/utils/process_priority.py`
    - Windows と POSIX を吸収するプロセス優先度設定ユーティリティを実装（`set_process_priority`）。
    - CPU アフィニティ固定用 `set_cpu_affinity` も実装（存在しない場合はスキップ）。
    - 権限不足や未対応プラットフォームでの失敗を警告として処理（例外を破壊的に投げない）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレーク: signal_rank）と重み付け（等金額・スコア加重）関数を実装。
    - スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限を適用する `apply_sector_cap` 実装。既存保有のセクター別時価をもとに上限を超えるセクターの新規候補を除外。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバックして警告を出力。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリングと端数処理）、cost_buffer による保守的見積りをサポート。
    - 価格未取得銘柄のスキップやログ出力によるデバッグ情報を提供。
  - `src/kabusys/portfolio/__init__.py` で上記関数群を公開。
- 解析 / 研究モジュール（初期実装）
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受けて定量ファクター（Momentum / Value / Volatility / Liquidity）を計算する方針を実装（関数や定義、定数類を追加）。モジュールは prices_daily / raw_financials を想定している。
    - PSEUDO 実装の一部（定数や calc_momentum のインターフェースなど）を追加（実装続行の痕跡あり）。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、P95 等の指標を計算して PASS/FAIL を判定する。
    - 基準値（稼働率 99%、成功率 90% 等）を定義しレポート出力を行う。
- その他ユーティリティ/初期化
  - `.env` 解析機能（`src/kabusys/config.py` 内）
    - export プレフィックス、クォート（シングル/ダブル）やバックスラッシュエスケープ、行内コメントルール等に対応した堅牢なパーサを実装。
    - .env ファイルの読み込みオプション（override/protected）を提供して OS 環境変数の保護を実現。
  - `src/kabusys/tools/__init__.py`, `src/kabusys/utils/__init__.py` 等のパッケージ初期化ファイルを追加。

### Changed
- ログ出力の設計
  - コンソール出力を stdout に統一（cron 等でリダイレクトしやすくするため）し、ファイルハンドラは日次ローテーションで 30 日分を保持する実装に統一。
- DB パスと監視の扱い
  - 監視用プロセスは環境にかかわらず `Settings.sqlite_path`（本番監視 DB）を使用する挙動を明記（`run_monitoring`）。一方、実行エンジンは paper_trading の場合に専用 DB を使用する。
- プロセス起動フロー
  - すべての起動スクリプトで最初にプロセス優先度を設定するように統一（`set_process_priority("high")` を呼び出す）。
- 設定検証の強化
  - `validate_config.py` により起動前の主要環境変数・ファイル・YAML の存在/パースチェックを提供。`--strict` オプションで警告を FAIL 扱いにできる。

### Fixed
- ロバスト性の向上
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にプロセスが落ちないように修正（警告を出してコンソール出力のみ継続）。
  - `.env` 読み込み失敗時に警告を出すだけで起動を継続するように調整（tests/CI での柔軟性を確保）。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）で ValueError を投げずにデフォルトへフォールバックする処理を追加。
  - `set_process_priority` / `set_cpu_affinity` で権限不足や未サポート環境の例外が発生した場合に警告に置き換えるように改善。

### Security
- `.env` ウィザードの表示改善
  - `config_setup.py` の確認画面でシークレット項目はマスク表示（`****`）して画面に出力、誤ってコンソールに平文で残すリスクを軽減。

### Documentation / UX
- CLI ヘルプ・使用例を各スクリプトのドキュメンテーション文字列に追加（run_monitoring, run_execution, config_setup, validate_config, paper_verification_report など）。
- config_setup による `.env` テンプレートの生成と次のステップ（validate_config 実行）案内を追加。

## Unreleased
- なし（現時点でのコードベースはバージョン 0.1.0 相当の機能群を含むと判断）

---

注記:
- 本 CHANGELOG は提供されたソースコードの内容から実装機能・挙動を推測して作成しています。実際のコミット履歴や変更履歴が存在する場合はそれに合わせて差し替えてください。