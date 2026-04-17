# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルは、リポジトリ内のソースコードの実装内容から推測して作成したリリースノートです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回公開リリース。システム全体のコア機能、CLI ツール、ポートフォリオ構築ロジック、検証ユーティリティ等を含みます。

### Added
- 核心ランタイム/デーモン
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境に応じて paper_trading 用のモックブローカーを使用し、専用 SQLite（data/paper_trading.db など）に記録するよう実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止はリポジトリ直下の data/stop_requested.flag により制御。
- 設定関連
  - config.py: 環境変数・.env 自動読み込み機能を実装（.env と .env.local の優先度処理、プロジェクトルート探索を含む）。API トークンや各種パスをプロパティとして提供する Settings クラスを追加。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（シークレットマスク、選択肢・デフォルト表示、保存機能）。生成される .env ファイルのテンプレート出力を実装。
  - validate_config.py: 起動前の設定検証ツールを追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パス検査、config/*.yaml 存在＋パースチェック、--strict モード対応）。
- ポートフォリオ構築ライブラリ（純関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア/ランクベース）、等金額／スコア加重の重み計算。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウンと再配分ロジック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有を考慮して候補を除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/__init__.py: 上記関数群を公開 API としてまとめてエクスポート。
- リサーチ/分析
  - research/factor_research.py: DuckDB を用いた定量ファクター計算（モメンタム、ボラティリティ、流動性等）。prices_daily / raw_financials を参照して日付基準でファクターを返す設計。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows の優先度クラス、POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。プラットフォーム差分を吸収する実装と例外ハンドリングを含む。
- モニタリング/レポート
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db の利用）を各起動スクリプトに追加。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出・判定（合格基準値を定義）し、期間指定や DB パス指定を CLI オプションで受け付ける。
- パッケージ情報
  - __init__.py にバージョン情報 (__version__ = "0.1.0") と主要サブパッケージを追加。

### Changed
- DB の扱い
  - run_monitoring: Monitoring は KABUSYS_ENV に依存せず「本番 sqlite_path」を使用する仕様（監視データは本番 DB に格納）。
  - run_execution: paper_trading 環境では paper_sqlite_path を優先して接続し、本番 DB と分離される仕様。
- 設定の読み込み優先度
  - OS 環境変数 > .env.local > .env の順で .env を読み込む挙動を実装（既存の OS 環境を保護する protected キーセットを導入）。
- エラーハンドリング／堅牢化
  - .env パース (_parse_env_line): export プレフィックス、クォート内のエスケープ処理、インラインコメントの扱いなどを考慮した堅牢な実装に。
  - process_priority: 利用可能な定数がない環境でもモジュールロードできるよう getattr フォールバックを採用。アクセス拒否や未実装例外は警告ログで無視する動作に変更。
  - run_monitoring/run_execution: 停止フラグ（stop_requested.flag）検出による安全停止処理を追加。起動時にプロセス優先度を高く設定する処理を最初に実行。
- CLI 出力/ユーザー体験
  - config_setup: シークレット入力のマスク表示、既存値の再利用、確認プロンプトを追加。保存テンプレートに注意書き（.env を Git にコミットしない旨）を挿入。

### Fixed
- 環境値検証
  - Settings.paper_fill_mode: 無効な値に対して明示的な ValueError を返し、許容値の説明を行うように改善。
  - Settings.env / log_level: 無効な値で ValueError を投げる設計にして、早期検出を強化。
- レポートおよび統計算出
  - paper_verification_report: P95 計算関数と各種クエリで NULL / データ不足時に安全に N/A を返すようにハンドリングを追加。DB が存在しない場合のエラーメッセージを改善。
- 設定検証ツール
  - validate_config: PyYAML 未インストール時には YAML 検証をスキップし警告を出すように。config/*.yaml が存在しない場合に警告メッセージを表示して生成スクリプトへの導線を案内。

### Security
- .env の取り扱いに関する注意書きを config_setup の出力テンプレートに明記（.env を Git に含めないことを推奨）。

### Notes / Known limitations
- portfolio.position_sizing: 価格データが欠損（0 や None）の場合、現状はスキップしてしまうためエクスポージャーが過少評価される可能性あり。将来的には前日終値などのフォールバック価格導入を検討。
- process_priority.set_cpu_affinity: 一部 OS / 権限下では失敗する（警告ログでフォールバック）。
- monitoring / execution の一部コンポーネント（SystemMonitor、ExecutionEngine、BrokerClientFactory 等）は本変更ログの範囲で呼び出し・組み立てを行うが、実装の詳細（内部ロジック）は別モジュールに依存するため、その動作確認は運用環境に依存。

---

開発・運用に関する問い合わせや追記したい点があればお知らせください。必要に応じてリリース日やカテゴリ分けの修正、個別コミットに基づく詳細な変更説明を追記します。