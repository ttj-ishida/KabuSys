# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。日付はコードベースから推測したリリース日です。

## [未リリース]

(なし)

## [0.1.0] - 2026-04-19

Added
- 実行用 / 運用用の起動スクリプトを追加
  - run_execution: ExecutionEngine を起動するエントリポイント。プロセス優先度を高めに設定し、スレッドでエンジンを実行、停止フラグ（data/stop_requested.flag）で安全に停止可能。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード DB（data/paper_trading.db）を使用し、本番 DB と分離する動作をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループを終了。Monitoring は環境にかかわらず本番 sqlite_path を使用する実装。

- 環境設定・検証用 CLI を追加
  - config_setup: 対話式ウィザードで .env を生成/更新するツールを提供。シークレット項目はマスク表示、保存前に確認ダイアログを表示。
  - validate_config: .env と config/*.yaml の基本的な整合性チェックを行う CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証を行う。--strict オプションで警告を失敗扱いにできる。

- 設定管理機能（kabusys.config）
  - プロジェクトルート検出ルーチンを実装（.git または pyproject.toml を探索）。これによりカレントワーキングディレクトリに依存せず .env を自動ロード。
  - .env 読み込みロジックを強化（export プレフィクス対応、クォート内のエスケープ処理、インラインコメントの扱い等）。
  - Settings クラスを実装し、各種環境変数（J-Quants、kabuAPI、DB パス、Paper Trading 関連、監視閾値など）をプロパティとして提供。PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の有効値チェックを実施。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights、全スコアが 0 の場合は等配分にフォールバックして警告）を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier、未知レジームはフォールバック）を実装。セクター不明 ("unknown") の扱いや既存保有からのエクスポージャー計算の挙動を明記。
  - position_sizing: 各配分方式（risk_based / equal / score）に基づく発注株数算出を実装。単元株（lot_size）での丸め、ポートフォリオと利用可能現金に基づく aggregate cap のスケーリング、手数料やスリッページを想定した cost_buffer の考慮、端数配分のための残差処理などのロジックを搭載。

- 監視・レポート系ツール
  - monitoring_db 初期化呼び出しを各起動スクリプトに組み込み、監視用テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report: ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して検証レポートを生成するスクリプトを追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。日付フィルタ（--from / --to）と DB パス指定（--db）に対応。

- ユーティリティ
  - utils/logging_setup: 統一的なログ設定ユーティリティを追加。StreamHandler を stdout に設定（cron 等で stdout/stderr を一本化する運用を想定）、TimedRotatingFileHandler による日次ローテーション（30 日保持）をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして動作継続する。
  - utils/process_priority: Windows/Linux/Mac の差分を吸収したプロセス優先度設定と CPU affinity 設定を提供。起動スクリプトで初動に優先度を "high" に設定する呼び出しを行う。権限不足などで設定できない場合は警告を出してスキップ。

- 研究用モジュール（partial）
  - research/factor_research: Momentum 等のファクタ計算を行う設計を追加（DuckDB 経由で prices_daily / raw_financials を参照）。モジュール冒頭に定数や設計方針を定義。実装途中（ソース末尾で途切れ）だが、関数のインターフェースや利用想定は明記。

Changed
- .env 自動ロード順序を明確化：OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- ロギング初期化の振る舞い：既にハンドラが存在する場合は一度クリーンアップしてから再設定することで二重出力を防止。

Fixed
- ログディレクトリ作成やファイルハンドラ初期化に失敗した場合でもコンソールログで継続できるようフォールバック処理を追加（エラー時は警告出力）。

Security
- シークレット系（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）を .env ウィザードでマスク表示するなど、設定ファイル取り扱いでの注意喚起を追加。README 等の明示的注意（.env を Git に含めない）を .env の自動生成ヘッダに記載。

Notes / その他
- run_monitoring の実装では monitoring が常に production の sqlite_path を使う点や、run_execution が paper_trading 用 DB を分離して使用する点など、運用上の重要な差分がコード内コメントに明示されています。運用時は KABUSYS_ENV の設定や各種パスに注意してください。
- research/factor_research は実装途中の箇所があるため、ファクタ計算の呼び出し前に実装完了が必要です。

---
開発にあたっての補足やリリースノートの補強（たとえば各 CLI の使用例や既知の制約）は必要に応じて別途追記できます。必要なら、各項目ごとに詳細な使用手順や設定例も作成します。