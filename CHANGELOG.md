# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能とユーティリティを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として設定。

- 設定管理
  - 環境変数／.env 管理モジュール `src/kabusys/config.py` を追加。
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env/.env.local を自動読み込み（無効化用: `KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - 行パーサは `export KEY=val`、クォート、エスケープ、インラインコメントなどに対応。
    - 必須変数取得ヘルパー `_require()`、Settings クラスで各種設定（DBパス、APIトークン、環境種別、閾値等）をプロパティとして提供。
    - `is_live` / `is_paper` / `is_dev` の判定ユーティリティを提供。

- 環境設定ウィザード CLI
  - `.env` の初期作成・更新を対話式で支援する `src/kabusys/config_setup.py` を追加。
    - 対話プロンプト、既存値の読み込み、シークレットマスク表示、保存確認などの UX を提供。
    - デフォルト項目・説明つき。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml の不備を検出する `src/kabusys/validate_config.py` を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config YAML の存在とパース（PyYAML がない場合は警告）など。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行系（Execution）起動スクリプト
  - `src/kabusys/run_execution.py`
    - `ExecutionEngine` 用の起動スクリプト。プロセス優先度を最初に "high" に設定。
    - 環境に応じて DB を分離: `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドで ExecutionEngine を実行。停止フラグ（data/stop_requested.flag）検知で graceful shutdown。
    - pid ファイルパスの管理。

- 監視系（Monitoring）起動スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト。プロセス優先度を "high" に設定。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満等の不正値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用（監視 DB は常に本番 DB を参照する想定）。
    - 停止フラグ検知でループを終了し、例外はログに記録して次ポーリングへ復帰。

- 監視 DB 初期化ユーティリティ参照（init_monitoring_db）
  - Execution / Monitoring 起動時に監視テーブルの存在を保証する呼び出しを行う（冪等に初期化）。

- ロギングユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一的なログ設定関数 `setup_logging()` を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル・ログディレクトリの解決順を明確にし、既存ハンドラの二重設定を防止。

- プロセス優先度・CPU affinity ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - Windows（psutil の priority class）と POSIX（nice 値）を吸収して `set_process_priority()` を提供。失敗時は警告を出してスキップ。
    - `set_cpu_affinity()` により最初の N コアにプロセスを固定可能。

- ポートフォリオ構築関連（純関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を追加。スコアが全て 0 の場合は等重みにフォールバックして警告。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限の `apply_sector_cap()` と市場レジームに応じた乗数 `calc_regime_multiplier()` を追加。unknown セクターや価格欠損時の扱い、未定義レジームへのフォールバックを明記。Bear/Neutral/Bull のデフォルト乗数を定義。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数決定ロジック `calc_position_sizes()` を追加。allocation_method として "risk_based", "equal", "score" をサポート。lot_size、コストバッファ、aggregate cap のスケールダウン、残余配分ロジック（端数の再配分）を実装。価格欠損や上限に関する TODO コメントあり（将来的な拡張の指摘）。

- 研究・ファクタ計算（部分実装）
  - `src/kabusys/research/factor_research.py`
    - DuckDB（prices_daily / raw_financials）を用いたファクター計算モジュールを追加。Momentum / Value / Volatility / Liquidity の計算方針、リターン・MA200乖離率・ATR・出来高系指標を想定。関数インターフェースや定数を定義（計算ロジックはモジュール内で実装予定）。（注: ソース末尾で実装が途中で切れている箇所あり）

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から検証指標（稼働率、注文成功率、送信率、リスク却下数、P95レイテンシ等）を集計してレポート出力する CLI を追加。
    - P95 計算、日付フィルタ（--from/--to）、DB パス優先順位（--db > 環境変数 > デフォルト）に対応。
    - デフォルト閾値を定義（稼働率 99% / fill 90% / send 95% / P95 latency 200ms）し、Pass/Fail の判定を行う。

- パッケージエクスポート整理
  - `src/kabusys/portfolio/__init__.py` によるポートフォリオ関連 API のエクスポート整備。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Known issues / Notes
- research/factor_research.py の実装が途中で切れている箇所があります（ソース末尾に未完の行あり）。ファクター計算の完全実装は今後の作業予定です。
- position_sizing の価格欠損（price=0.0）時の取り扱いに関する TODO コメントあり（前日終値等のフォールバック検討）。
- Monitoring はソース上「監視は環境にかかわらず本番 sqlite_path を使用」と明記されています。運用時は DB 分離が必要でないか設計確認してください。
- `validate_config` は PyYAML が未インストールの場合、YAML ファイルの内容検証をスキップします（警告を出力）。YAML 検証を行うには PyYAML をインストールしてください。

### Security
- なし（初回リリース）

--------------------------------
今後の予定（例）
- factor_research の完全実装とテスト追加
- ユニットテストの整備（現状はコードのみ）
- ExecutionEngine / SystemMonitor の統合テスト、障害注入テスト
- 銘柄別 lot_size 対応（stocks マスタ参照）などの position_sizing 拡張

（以上）