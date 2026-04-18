# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更点はカテゴリ別に記載しています。  
このファイルはプロジェクト初期リリースの変更履歴です。

全体方針:
- バージョン番号はパッケージの `__version__` (src/kabusys/__init__.py) に合わせています。
- 日付はこのリリース作成日です。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションとユーティリティ群を追加。
  - パッケージエントリとバージョン: src/kabusys/__init__.py (__version__ = "0.1.0")。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時に mock 用の専用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用するよう分離。
- 設定関連
  - src/kabusys/config.py: Settings クラスを導入。環境変数の自動読み込み（.env / .env.local、OS 環境優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。多数の設定プロパティ（DBパス、PID/kill フラグパス、監視閾値、PAPER_FILL_MODE 等のバリデーション）を実装。
  - src/kabusys/config_setup.py: .env の対話式ウィザードを追加（.env の生成・更新を支援）。シークレットのマスク表示、デフォルト/既存値の再利用をサポート。
  - src/kabusys/validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）、および本番時のガードチェックを実施。--strict オプションで警告を FAIL 扱いにできる。
- ログ関連ユーティリティ
  - src/kabusys/utils/logging_setup.py: 共通ログ設定ユーティリティを追加。stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（logs/<app_name>.log、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- プロセス優先度・CPU ピンニング
  - src/kabusys/utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差異を吸収し、権限エラー等は警告ログでスキップ。
- Portfolio 構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合は等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を追加。未知レジームは 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py: 株数決定ロジック (calc_position_sizes) を追加。allocation_method 支持（"risk_based" / "equal" / "score"）、リスクベースの計算、lot_size 単位での丸め、aggregate cap に基づくスケーリング（余剰キャッシュでの再配分ロジック）などを実装。
  - これらをまとめて公開するパッケージインターフェースを追加（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）からデータを集計し、稼働率・注文成功率・送信率・レイテンシ等を算出して PASS/FAIL 判定を出力。CLI オプション --from/--to/--db をサポート。P95 の計算や閾値はソース内で定義（稼働率 >= 99%、成立率 >= 90% 等）。
  - src/kabusys/tools/__init__.py を追加。
- 研究用モジュール
  - src/kabusys/research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等を計算する設計。DuckDB を利用する方針）。（注: ファイル末尾が途中で切れている可能性あり。）
- 監視 DB 初期化ヘルパー利用
  - run_execution/run_monitoring で共通の init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力の標準化
  - 既存起動スクリプトから logging_setup.setup_logging を呼び出すことで、全アプリで統一的なログ設定（stdout + 日次ファイルローテ）を適用。
- データベースの分離
  - ExecutionEngine は paper_trading 環境時に paper_sqlite_path を使用することで、本番の監視 DB とペーパートレード DB を明確に分離（誤発注リスク軽減）。
- 環境変数自動読み込みの挙動
  - .env の読み込み順序と上書きルールを明確化（OS 環境変数 > .env.local > .env、.env.local は上書き許可）。既存の OS 環境変数を保護するため protected セットを使用。

### Fixed
- 不正な環境変数値に対する堅牢性向上
  - MONITOR_POLL_INTERVAL や PAPER_FILL_MODE、LOG_LEVEL、KABUSYS_ENV などのバリデーションとデフォルトフォールバックを追加。MONITOR_POLL_INTERVAL が 0 以下や整数以外の値の場合でも安全にデフォルトにフォールバックするよう修正。
- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリの作成に失敗してもコンソールログは維持するように改善（ファイルハンドラ生成をスキップして継続）。

### Notes / Known limitations
- factor_research.py は設計方針と主要ロジックを含みますが、ファイル末尾が途中で切れているため完全実装や追加ユニットテストが必要な可能性があります。
- position_sizing の価格フォールバックに関する TODO が残っています（price が欠損した場合の前日終値等のフォールバック未実装）。
- process_priority/set_cpu_affinity は権限や OS に依存するため、権限不足では警告ログを出し設定をスキップします。
- validate_config の YAML パース検証は PyYAML に依存。インストールされていない環境では内容検証がスキップされる点に注意してください。
- .env ファイルは明示的に Git にコミットしないことを README 等で運用ルールとして周知してください（config_setup.py のヘッダにも注記）。

---

将来的なリリースでは、テストカバレッジの追加、factor_research の完成、銘柄ごとの lot_size 対応、さらに詳細な運用手順（デプロイ手順・監視アラート設定例）を追加する予定です。