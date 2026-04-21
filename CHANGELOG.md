# CHANGELOG

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の慣例に準拠しています。  

※ リリース日付はソースコードから推測して設定しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 実行/監視用エントリポイントを追加。
  - run_execution: ExecutionEngine を起動する CLI ライクなスクリプトを追加。
    - プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite（デフォルト: `data/paper_trading.db`）を使用する設計（MockBrokerClient の利用を想定）。
    - 実行中は PID ファイル（`data/execution.pid`）を管理し、停止フラグファイルでグレースフルに停止可能。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションを実行。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を明記。
    - 停止フラグファイルでループを終了、例外発生時はログに残して次回ポーリングまで待機。
- 環境設定 / 設定読み込み
  - `kabusys.config.Settings` を導入。環境変数をラップして各種設定値（J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV、LOG_LEVEL、各種しきい値など）をプロパティとして提供。
  - .env 自動読み込み機能を実装。
    - プロジェクトルート（`.git` または `pyproject.toml`）を基準に `.env` / `.env.local` を自動ロード。
    - OS 環境変数は保護（既存キーを保護）して `.env.local` 等で上書きする挙動を採用。
    - 環境変数自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` パーサーを実装。
    - `export KEY=val` 形式、クォート（'"/）とバックスラッシュエスケープ、インラインコメントの扱い等に対応する堅牢なパーサー。
- 設定ウィザード / 検証ツール
  - `config_setup.py`: 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - 秘匿入力表示（保存時はマスク表示）、デフォルト値、選択肢、説明文を備えた項目定義。
    - .env に書き込む際にヘッダで注意書きを追加（.env を Git にコミットしない旨）。
  - `validate_config.py`: 起動前に環境変数と `config/*.yaml` の存在・妥当性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML が未インストールの場合は警告）など。
    - `--strict` オプションで警告を失敗（exit code 1）扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - `utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログディレクトリ/レベルの解決順（引数 > 環境変数 > デフォルト）を実装。ディレクトリ作成失敗時はファイル出力をスキップして継続。
    - 起動スクリプト間での一貫したログ管理を目的とする。
  - `utils.process_priority` を追加。
    - Windows / POSIX（Linux, macOS 等）差を吸収してプロセス優先度（nice / Windows priority class）を設定可能。
    - CPU affinity を設定する関数 `set_cpu_affinity` を提供。
    - psutil 標準の例外（アクセス権限等）を安全にハンドリングしてフォールバックする。
- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバック）。
  - `portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター別エクスポージャーを計算し上限を超えるセクターの新規候補を除外）。
    - レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear マップ、未知は警告と 1.0 フォールバック）。
  - `portfolio.position_sizing`:
    - `calc_position_sizes` を実装。allocation_method に応じた株数計算（"risk_based" / "equal" / "score"）を提供。
    - 単元（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを実装。残差再配分アルゴリズムも実装。
- リサーチ / ファクター計算
  - `research.factor_research` にファクター計算基盤を追加（モメンタム・ボラティリティ等の定数と calc_momentum 関数の骨子）。
    - DuckDB 接続を受け取り prices_daily / raw_financials に基づく計算を行う設計（SQL + Python）。
- ツール
  - `tools.paper_verification_report`:
    - Paper Trading 用 SQLite を参照して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均 / 最大 / P95）等を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェックなどを実装。

### Changed
- なし（初回公開）

### Fixed
- 監視ループ / 実行ループの堅牢性を向上。
  - run_monitoring: monitor.check_once() で例外が発生してもループを継続し、例外をログに残すようにした。
  - run_execution: 停止フラグ検知時に ExecutionEngine.stop() を呼び出してグレースフルに終了できるよう実装。

### Security
- `.env` 生成時に「.env を絶対に Git にコミットしないこと」を明示するヘッダを出力するようにした。

### Notes / Implementation details
- 環境変数の妥当性チェックや値のパース（数値や列挙値の検証）は Settings クラスと validate_config で重複チェック可能。
- ロギング設定は既存ハンドラを一度クローズしてから再設定するため、複数回呼び出してもハンドラ二重設定を避ける。
- process_priority / cpu_affinity は権限不足や未対応 OS の場合は警告ログを出しスキップする実装。
- Paper Trading と本番 DB の分離を意識した設計（paper_sqlite_path の導入、Broker の Mock 切替を想定）。

---

（将来的にリリース履歴を継続する場合は、ここに Unreleased セクションを用意し、次バージョンの変更点を記録してください。）