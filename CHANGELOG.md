# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

すべての非互換性のある変更はメジャーのリリースノートに明記します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買システム KabuSys の基本機能群を提供します。

### Added（追加）
- 基本構成・設定
  - Settings クラスを提供（src/kabusys/config.py）。環境変数経由で設定を取得し、各種プロパティ（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）を公開。
  - 自動 .env ロード機能を追加（プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パース実装を強化。クォート／エスケープ、export プレフィックス、行内コメントの扱いに対応。

- 設定支援ツール
  - 対話式設定ウィザード (kabusys.config_setup) を追加。.env の作成・更新を支援し、デフォルト値・選択肢・シークレット入力をサポート。
  - 設定検証 CLI (kabusys.validate_config) を追加。必須環境変数やパス、config/*.yaml の存在・パースをチェック。--strict モードで警告を失敗扱いにできる。
  - config/*.yaml のパースは PyYAML があれば実施し、未インストール時は警告してスキップ。

- 実行/監視プロセス起動スクリプト
  - execution エンジン起動スクリプト (src/kabusys/run_execution.py) を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を適用する設計）。
    - ブローカー生成は BrokerClientFactory 経由。
    - ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag の存在で安全に停止する仕組みを実装。起動時にプロセス優先度を high に設定。
    - PID ファイル（data/execution.pid）を扱う。
  - monitoring 起動スクリプト (src/kabusys/run_monitoring.py) を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。例外発生時はログに出力して次のポーリングへ継続。
    - 起動時にプロセス優先度を high に設定。

- 監視・モニタリング関連
  - init_monitoring_db を実行して監視テーブルを冪等に初期化（両スクリプトから呼び出し）。

- ロギング・プロセスユーティリティ
  - 統一ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py) を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py) を追加。
    - Windows / POSIX を吸収してプロセス優先度を設定。psutil を用い、アクセス拒否や未実装は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。

- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定 / 重み計算 (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順 + tie-breaker で候補を選択。
    - calc_equal_weights、calc_score_weights: スコア正規化、全スコアが 0 の場合は等配分へフォールバック。
  - セクター制限・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: セクター集中上限を超える銘柄を候補から除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す。未知レジームは警告して 1.0 をフォールバック。
  - 株数決定・リスク制限 (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method に応じて発注数量を計算（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）での丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守見積り、残差処理による追加配分ロジックを実装。
  - ポートフォリオ関連関数をパッケージエクスポート（src/kabusys/portfolio/__init__.py）。

- Research（解析）関連（基盤）
  - factor_research モジュール (src/kabusys/research/factor_research.py) の骨組みを追加（モメンタム/ATR/流動性等の計算方針と定数を定義、DuckDB 経由での計算を想定）。（モジュール途中まで実装あり）

- ツール
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py) を追加。
    - 指定期間（--from / --to）または DB 全期間で検証レポートを出力。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数などを計算し、閾値に基づいて PASS/FAIL 判定を行う。
    - DB のテーブル欠落や OperationalError は捕捉して部分的にデータ欠落として処理。

### Changed（変更）
- パッケージ初期化でバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 各起動スクリプトで起動時にプロセス優先度を設定するよう統一。

### Fixed（修正）
- （初版のため既知のバグ修正履歴はなし。実装上の補足や TODO はソース内コメントに記載。）

### Notes / Behaviors（備考）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 SQLite を上書きせず、PAPER_TRADING_SQLITE_PATH（環境変数）またはデフォルト data/paper_trading.db を利用して、本番データと完全分離する設計。
- .env の自動ロードは OS 環境変数を保護（.env.local は override=True だが既存の OS 環境変数は上書きしない）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。不正値や 0 以下はデフォルト 60 秒にフォールバックして警告を出力。
- ロギングは stdout に出力する設計のため、cron/task scheduler でのリダイレクト運用を想定。
- process_priority の設定は権限やプラットフォームによって失敗する可能性があり、その場合は警告を出して処理を継続する。

---

今後の予定（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の具体的算出と正常系テスト）
- execution / broker 周りの統合テストと本番リスクガードの強化
- 単体テスト・CI の整備、ドキュメント拡充

-----------
参考: この CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）から実装内容を推測して作成しています。