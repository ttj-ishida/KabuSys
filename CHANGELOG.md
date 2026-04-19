# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
（注: この CHANGELOG は提供されたコード内容から機能追加・振る舞い・注記を推測して作成しています。）

## [Unreleased]

### Added
- 全体
  - パッケージ初期構成（モジュール群の追加）。
  - バージョン文字列をパッケージルートに付与（kabusys.__version__ = "0.1.0"）。
- 設定・起動関連
  - Settings クラスによる環境変数ラッパーを実装。各種設定（J-Quants, kabuAPI, DB パス, ログ設定, 環境判定フラグ等）をプロパティとして提供。
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。.env と .env.local の読み込み順制御および OS 環境変数の保護実装。
  - config_setup CLI: 対話式ウィザードで .env を生成・更新するユーティリティを追加（シークレット項目のマスク表示、既存値の再利用、書き込み機能）。
  - validate_config CLI: .env や config/*.yaml の設定不足や注意点を起動前に検出する検証ツールを追加（--strict モード対応）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。プロセス優先度を "high" に設定、paper_trading 環境では専用の paper DB を使用して本番 DB と分離、ブローカーファクトリから BrokerClient を生成しコンポーネントを組み立てて ExecutionEngine をスレッドで起動、停止フラグ / PID 管理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグ / DB 初期化 / duckdb 接続の管理。
- ロギング・プロセス管理
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保管）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。権限不足時は警告を出してスキップ。
- モニタリング / 実行用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築
  - portfolio.portfolio_builder: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。スコアがすべて 0 の場合は等金額配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックしてログ警告を出す。
  - portfolio.position_sizing: allocation_method（"risk_based", "equal", "score"）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、per-position と aggregate のキャップ、スケールダウンロジック、手数料等を見積もる cost_buffer を考慮した安全な資金配分をサポート。
  - portfolio パッケージの __all__ を設定し各関数を公開。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポートジェネレータを追加。稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。日付フィルタ、P95 計算、欠損テーブルに対する頑強なハンドリングを実装。
- リサーチ（スケルトン）
  - research.factor_research: DuckDB を用いたファクター計算モジュールのスケルトンを追加（モメンタム、MA、ATR 等を想定）。関数 calc_momentum の実装が開始されている（途中までのコードあり）。

### Changed
- ロギング
  - StreamHandler を stdout に向けることで cron / TaskScheduler 等で stdout/stderr を一元化してリダイレクトしやすくした。
  - 既存ハンドラが存在する場合はクリアしてから再設定する仕様に変更（二重設定回避）。
- 環境変数ロード
  - .env の読み込みロジックを強化（export KEY= 形式、クォート中のバックスラッシュエスケープ、インラインコメント処理の細かな挙動を実装）。
  - .env.local を上書きモードで読み込めるようにし、OS 環境変数を protected として上書き防止。
- 起動時優先度
  - run_execution/run_monitoring の起動時に最初にプロセス優先度を "high" に設定するように変更（重要処理の優先度確保）。
- DB パスの取り扱い
  - run_execution: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と完全に分離。
  - run_monitoring: 監視は環境に関係なく本番 sqlite_path を使用する仕様を明確化。
- 停止・PID 管理
  - 停止フラグ（data/stop_requested.flag）検知により各スクリプトが優雅に終了するロジックを追加。ExecutionEngine は別スレッドで実行し、フラグ検知で engine.stop() を呼び出す。
- validate_config
  - config/*.yaml の存在確認および PyYAML が無い場合は検証をスキップして警告を出すようにした。--strict で警告を失敗扱いにできる。

### Fixed
- 環境ファイルパーサの不具合対策
  - クォート内のエスケープやコメント扱いに起因する .env の誤パースを改善。
- paper_verification_report の堅牢化
  - テーブルが存在しない場合や OperationalError が発生した場合にデフォルト値を返すことでクラッシュを回避。P95 計算で空リストを扱う安全性を確保。
- portfolio ロジック
  - スコアが全て 0 の場合に calc_score_weights が等金額配分にフォールバックするようにしてゼロ除算や不正な配分を回避。
  - price が欠損・0 の場合は該当銘柄をスキップし、デバッグログを出すようにして例外発生を防止。
- process_priority / cpu_affinity
  - サポートされないプラットフォームや権限不足の場合に警告を出してスキップするようにして起動失敗を避ける。

### Security
- config_setup の対話表示でシークレット（API トークン等）はマスク表示（****）して画面に直接表示されることを抑止。

### Removed
- 特になし（初期リリース相当のため多数の機能追加が中心）。

### Known issues / TODO
- research.factor_research の calc_momentum 実装が途中で終わっている（ファイル末尾で途切れ）。ファクター計算モジュールは引き続き実装が必要。
- position_sizing の将来的拡張として各銘柄の単元株（lot_size）を銘柄マスタから取得する設計（TODO コメントあり）。
- apply_sector_cap では price が欠損した場合にエクスポージャーが過少見積りされる旨の注記があり、フォールバック価格取得の拡張が望ましい。
- run_monitoring が常に本番 sqlite を参照する点は設計意図だが、テスト環境での分離が必要な場合は注意。

---

## [0.1.0] - 2026-04-19

初回公開相当のマイルストーン。上記 Unreleased の内容を反映した最初の安定化リリース。
- パッケージ基本機能（設定管理、起動スクリプト、ロギング、プロセス制御、ポートフォリオ構築、ポジションサイズ、リスク調整、Paper 検証ツール、設定ウィザード & 検証ツール）を収録。
- 開発者向け CLI（python -m kabusys.config_setup, python -m kabusys.validate_config）を提供。
- Paper Trading と Live を分離するための DB パスと Mock ブローカーファクトリへの対応を実装。

---

（注）この CHANGELOG は提供されたソースコードの構造・コメント・実装から推測して作成しています。実際のコミット履歴や変更差分がある場合は、その履歴に基づく正式な変更履歴の追記・修正を推奨します。