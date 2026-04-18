CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
主にコードベースから推測できる追加機能・改善点・修正・挙動についてまとめています。

Unreleased
----------

### Added
- 全体
  - 初期バージョンのアプリケーション基盤を追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution: 実行エンジンの起動スクリプトを追加。ExecutionEngine を起動し、BrokerClientFactory 経由でブローカークライアントを構築。Paper Trading 環境では専用の SQLite DB（data/paper_trading.db、環境変数で変更可）を使用して本番 DB と完全分離。
  - run_monitoring: SystemMonitor をポーリングで定期実行する監視スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。停止はプロジェクト直下のデータフォルダに置かれる `stop_requested.flag` ファイルで制御。

- 設定・検証ツール
  - config_setup: インタラクティブな .env 作成/更新ウィザードを追加。主要な環境変数（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）の入力支援を行い、.env を生成。
  - validate_config: 起動前設定検証 CLI を追加。必須環境変数や config/*.yaml の存在・パース確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、production 向けの注意喚起等を行う。`--strict` オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config: 自動 .env ロード機構を実装（プロジェクトルートが検出できる場合に `.env` → `.env.local` の順で読み込み）。`.env` のパースは引用符・エスケープ・コメントを考慮した堅牢な実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - Settings クラスを追加し、環境変数の取得・検証・デフォルト解決を一元管理（J-Quants、kabu API、DB パス、監視閾値、環境判定メソッド等を提供）。一部プロパティで不正値時に明示的な例外を投げる。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。コンソール出力（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を追加。権限不足や未対応 OS の場合は安全にスキップして警告ログを出力。

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定（スコア降順ソート）、等金額配分、スコア加重配分の純粋関数を追加。スコア全0 の場合は等配分にフォールバック（警告）。
  - portfolio.risk_adjustment: セクター集中制限を適用する関数（apply_sector_cap）と市場レジームに応じた投下資金乗数計算（calc_regime_multiplier）を追加。未知レジーム時はフォールバック挙動を定義。
  - portfolio.position_sizing: ポジションサイズ算出ロジックを追加。allocation_method に応じた株数計算（risk_based / equal / score）、単元株丸め、最大ポジション比率・投下資金制限・スケーリング（available_cash を超える場合の縮小ロジックと残差分配）などを実装。

- 研究・分析ツール
  - research.factor_research: DuckDB 接続を使用したファクター計算モジュールの骨子を追加（モメンタム、MA200乖離、ATR、出来高系などの計算方針を定義、関数 calc_momentum の実装開始）。
  - tools.paper_verification_report: ペーパートレーディング検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し、しきい値に基づく PASS/FAIL 判定を行う。コマンドラインオプションで期間指定（--from/--to）および DB パス指定（--db）に対応。

### Changed
- ログ関連
  - ログ出力は stdout を優先して利用するように仕様決定（cron 等で stdout/stderr を統一してリダイレクトする運用を想定）。
  - setup_logging は既存ハンドラをクリーンアップしてから再設定するようにして二重登録を防止。

- DB の取り扱い
  - 監視（run_monitoring）は KABUSYS_ENV に依らず本番用 sqlite_path を使用する仕様とした（監視データは環境に依存しない想定）。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と分離。

### Fixed
- 設定パーサ
  - .env パーサの実装で引用符付き値のエスケープや行末コメント処理を考慮することで、実際の .env でよくあるパターンへの耐性を向上。

- 起動スクリプトの終了処理
  - run_execution / run_monitoring において、停止フラグ（stop_requested.flag）検知時に安全に停止する制御を実装。例外や KeyboardInterrupt に対しても DB 接続をクローズする finally を追加。

### Security
- 環境変数管理
  - config_setup で生成される .env に対して「.env を絶対に Git にコミットしないこと」という明示的な注意を出力するテンプレートを採用。
  - Settings の必須環境変数チェックで未設定時に例外を発生させ、起動前に明確に失敗させる設計。

Notes / 補足
- 多くのモジュールはドキュメント文字列（docstring）で意図・設計方針が明確に説明されており、将来的な拡張（銘柄別 lot_size の導入、フォールバック価格の採用、より詳細なファクター計算等）を見越した作りになっています。
- research.factor_research の calc_momentum はファイル末尾で途中で切れている（実装継続の余地あり）。実運用に向けて DuckDB SQL 周りの最終実装や追加のファクター実装が残っている可能性があります。
- 実際のブローカー統合や ExecutionEngine の詳細実装（エラーハンドリング、レート制限対応、order repository の永続化詳細等）はコードベースの他モジュールに依存しており、本 changelog は表層的な追加点・仕様から推測してまとめています。

今後のリリース案（提案）
- research モジュールのファクター計算完成とテスト追加
- ポートフォリオ最適化のユニットテスト拡充（edge case: 価格欠損、lot_size の異常値）
- 起動・監視スクリプトの統合テスト（stop flag / pid file / kill flag の挙動確認）
- ドキュメント（README / 操作手順）と運用手順（デプロイ手順、ログローテーション/監視）を補強

--- 
（この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）