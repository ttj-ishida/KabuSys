CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリースとして KabuSys の基本機能を追加。
  - パッケージ情報
    - バージョン: v0.1.0（src/kabusys/__init__.py）
  - 環境設定・管理
    - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）を追加。OS 環境変数を保護して .env/.env.local を読み込む実装（src/kabusys/config.py）。
    - .env の行パーサーは export 形式、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントを適切に扱う（src/kabusys/config.py）。
    - 対話式の環境設定ウィザードを追加（.env の初期作成 / 更新に使用、src/kabusys/config_setup.py）。
    - 設定検証 CLI を追加（必須環境変数の確認、KABUSYS_ENV やログ・DB パス等の検証、YAML ファイルの存在／パース確認を実施; src/kabusys/validate_config.py）。
  - 実行／監視ランチャー
    - ExecutionEngine 起動スクリプトを追加（プロセス優先度設定、Paper Trading 時は専用 DB に分離して Mock ブローカーを使用、停止フラグ監視、PID ファイル管理、src/kabusys/run_execution.py）。
    - SystemMonitor 用のポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL でポーリング間隔上書き可能、停止フラグ検知、monitoring 用 DB 初期化、src/kabusys/run_monitoring.py）。
  - ロギング / プロセス制御ユーティリティ
    - 統一的なロギング設定ユーティリティを追加（コンソール stdout 出力 + 日次ローテートファイル出力、ログディレクトリ自動作成・失敗時はコンソールのみで継続、src/kabusys/utils/logging_setup.py）。
    - プロセス優先度（Windows / POSIX 差分を吸収）および CPU affinity 設定ユーティリティを追加（権限不足や未対応プラットフォーム時は警告を出してスキップ、src/kabusys/utils/process_priority.py）。
  - ポートフォリオ構築
    - 候補選定 / 重み計算機能（スコア降順ソート、等金額配分、スコア加重配分、フォールバック処理）を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - セクター集中制限（apply_sector_cap）とレジームに応じた投下資金乗数（calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - 発注株数決定・リスク制限・単元丸めロジックを追加（risk_based / equal / score の allocation_method をサポート、アグリゲートキャップによるスケーリング、lot_size 単位での丸め、手数料スリッページ用 cost_buffer を考慮、src/kabusys/portfolio/position_sizing.py）。
    - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。
  - リサーチ / ユーティリティ
    - Paper Trading の検証レポート生成スクリプトを追加（稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL を判定、コマンドライン引数で期間指定可能、src/kabusys/tools/paper_verification_report.py）。
    - DuckDB 接続を使ったファクター計算モジュールの骨格を追加（momentum 等の計算を行う設計、src/kabusys/research/factor_research.py。※ファイルは部分実装）。
  - DB 初期化補助
    - 監視テーブルなどの初期化を保証する init_monitoring_db の呼び出しをランチャーに組み込み（monitoring/実行双方で冪等的に初期化）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env 読み込みエラー時に警告を出し続行する安全策を実装（ファイル読み込み失敗時の警告表示、src/kabusys/config.py）。
- ログディレクトリ作成失敗時はファイルハンドラの作成をスキップしてコンソール出力を維持するフォールバックを追加（src/kabusys/utils/logging_setup.py）。
- psutil による優先度設定や CPU affinity 設定は権限エラー等をキャッチして警告を出すようにして、プロセスがクラッシュしないように改善（src/kabusys/utils/process_priority.py）。
- モニタリングのポーリング間隔設定で不正な値が渡された際にデフォルトへフォールバックする処理を追加（MONITOR_POLL_INTERVAL の検証、src/kabusys/run_monitoring.py）。
- Execution エンジンの Paper Trading モードでは本番 DB と完全に分離して専用 SQLite を使用するようにした（src/kabusys/run_execution.py）。

Security
- 機密値（J-Quants トークン、kabu API パスワード等）は .env に保存する前提でウィザード中はマスク表示するなど取り扱いに配慮（src/kabusys/config_setup.py）。必須の機密環境変数未設定時は検証ツールでエラー扱いにする（src/kabusys/validate_config.py）。

その他 / Notes / Known issues
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO コメントあり（src/kabusys/portfolio/risk_adjustment.py）。
- position_sizing: 銘柄ごとの単元（lot_size）は現状グローバル共通。将来的には銘柄別 lot_map を受け取る設計に拡張する TODO がある（src/kabusys/portfolio/position_sizing.py）。
- research.factor_research モジュールは設計・骨格が含まれているが実装が途中（ファイル末尾が途切れている状態）。DuckDB ベースのファクター計算を意図。
- run_monitoring は Monitoring 用 DB として常に settings.sqlite_path を使用（環境に依存せず本番用パスを参照）。必要なら設定変更を検討。
- validate_config の YAML 検証は PyYAML が未インストールの場合スキップされる（警告表示）。

参考（主な環境変数）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: データベースパス
- LOG_LEVEL, LOG_DIR: ログ制御
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時の Kill Flag 自動クリア制御（ production では注意）

署名
----
この CHANGELOG は、リポジトリ内のソースコード（コメントや実装）から推測して作成した初期リリース向けの変更履歴です。実際のリリースノート作成時にはリリース日や変更対象を開発履歴に合わせて調整してください。