# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
主要なリリースや機能追加・修正をコードベースから推測してまとめています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-22

初回公開リリース。自動売買システム KabuSys のコア機能群を実装しています。以下はコードベースから推測してまとめた主な追加点・実装内容です。

### Added
- 全体
  - パッケージ初期版として各モジュールを実装・公開。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数/`.env` を取り扱う設定モジュール `kabusys.config` を実装。
    - プロジェクトルートを `.git` または `pyproject.toml` から自動で検出して `.env` / `.env.local` を読み込む機能。
    - クォートやエスケープを考慮した `.env` 行パーサーを実装（`export KEY=...` 形式にも対応）。
    - 必須環境変数の取得ヘルパー `_require()` と `Settings` クラスを提供（J-Quants / kabu API 等の設定をプロパティで公開）。
    - 環境判定（development / paper_trading / live）、各種パス（DuckDB/SQLite 等）、Paper Trading の動作モード等のプロパティを実装。

- 設定ユーティリティ / CLI
  - 対話式ウィザード `kabusys.config_setup` を実装。
    - `.env` の初期作成・更新を支援する対話ループ、既存値の読み込み、マスク表示（シークレット）をサポート。
    - `.env` 書き出しテンプレートを実装（コメント付き、Git にコミットしない旨の注意書き）。
  - 設定検証 CLI `kabusys.validate_config` を実装。
    - 必須環境変数の検査、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース検査（PyYAML がある場合）等。
    - `--strict` オプションで警告を失敗扱いにする機能。

- 実行 / 監視ランチャー
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（`data/paper_trading.db`、環境変数で上書き可）を使用して本番 DB と分離する設計。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動処理を実装。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御。
    - エンジンは別スレッドで起動し、停止フラグ検知で安全に停止する仕組み。
  - システム監視ループ起動スクリプト `kabusys.run_monitoring` を追加。
    - 環境にかかわらず監視は本番用の sqlite_path を使用して監視 DB を初期化。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトを使用。
    - 停止フラグ検知でループを終了、例外発生時にもログ出力して次のポーリングに継続する堅牢なループ。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup` を実装。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）をルートロガーへセットアップ。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリ解決順を明確化（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU アフィニティ設定ユーティリティ `kabusys.utils.process_priority` を実装。
    - Windows と POSIX（Linux/Mac 等）での差を吸収してプロセス優先度を設定。
    - CPU affinity 固定機能を提供。権限不足や未対応 OS の場合は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルの候補選定（スコア降順、タイブレークで signal_rank を利用）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額へフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限の適用（既存保有を考慮して特定セクターの新規候補を除外）、レジーム（bull/neutral/bear）に基づく投下資金乗数計算（フォールバックと警告あり）を実装。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算を実装。
    - 単元株（lot_size）、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料/スリッページの保守見積り）を考慮した丸めロジックを実装。
    - スケーリング時の端数処理（lot 単位での再配分）や上限超過回避を考慮。

- リサーチ / ファクター
  - `kabusys.research.factor_research` の骨組み（モメンタム等のファクター計算方針・定数）を実装。DuckDB の prices_daily / raw_financials を参照してファクターを計算する設計。

- ツール
  - Paper Trading の検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を実装。
    - 稼働率（uptime）、注文成功率 / 送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を SQLite の paper_trading DB から集計してレポート出力。
    - PASS/FAIL 判定の閾値（uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）を定義し、判定結果と失敗理由を表示可能。
    - CLI で期間指定（--from/--to）や DB パス指定（--db）に対応。

### Changed
- n/a（初回リリースのため、変更履歴はなし）

### Fixed / Notes
- .env パーサーでクォート内のバックスラッシュエスケープやインラインコメント処理に対応しており、複雑な環境変数値も正しく読み込めるようになっている点を改善済み（コード実装に基づく記載）。
- ログディレクトリ作成・ファイルハンドラ作成失敗時の安全なフォールバック（コンソールのみで継続）を実装しており、起動環境による崩壊を防止。
- プロセス優先度設定は権限不足や未対応 OS の場合に警告してスキップする堅牢な実装。
- 実行/監視プロセスは stop flag（data/stop_requested.flag）と PID ファイルを用いて起動停止制御を行い、運用時の手動停止に対応。

## 既知の制限（コードから推測）
- position_sizing の price のフォールバックが未実装（price が 0 の場合、エクスポージャーが過少評価される可能性）。コード内に TODO コメントあり。
- factor_research の実装はモジュールの骨組み・方針が記載されているが、関数群の完全実装（全ファクターの計算処理）が進行中である可能性あり（抜粋の末尾で未完の記述が確認される）。
- `config/*.yaml` の内容検証は PyYAML がインストールされていない場合はスキップされる点に注意。

---

変更点の記載は、提供されたソースコードの内容・コメント・ドキュメンテーション文字列から推測して作成しています。追加のコミット履歴や実際のリリースノートがある場合はそれを反映して更新してください。