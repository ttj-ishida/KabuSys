# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-25
初回リリース。自動売買システム「KabuSys」の基幹機能群を導入しました。

### Added
- コアランタイム / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、高優先度での実行、停止フラグ検出、スレッドでのエンジン実行管理、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用する振る舞いを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。監視用 DB 初期化を行い停止フラグでループを終了。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出）、堅牢な .env パーサ、Settings クラスを実装。多くの設定値（DB パス、API トークン、Paper Trading 設定、しきい値、PID/Kill フラグパスなど）を環境変数から取得・検証するプロパティを提供。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。デフォルト値・選択肢・シークレット入力をサポートし、.env ファイルへの書き込みを行う。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML があればパース検証）・本番環境向けガードなどをチェック。--strict オプションで警告をエラー扱いにできる。
- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をフォールバック。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX 系）でのプロセス優先度設定と CPU affinity 設定機能を追加。psutil を利用し、アクセス権限エラー時は安全に警告を出してスキップする。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 銘柄候補選定（スコア降順で上位 N）、等金額配分、スコア正規化配分（スコア全ゼロ時は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームによる乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0 を返し警告を出す。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、コストバッファ考慮、および残余キャッシュに応じた追加配分ロジックを実装。
  - portfolio/__init__.py: 上記機能を公開するパッケージ初期化。
- 解析・検証ツール
  - tools/paper_verification_report.py: ペーパートレーディングの検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し、閾値に基づいて PASS/FAIL を判定。P95 計算、期間フィルタ、DB パスの CLI 引数/環境変数指定に対応。
- データ分析（リサーチ）基盤
  - research/factor_research.py: ファクター計算モジュールのスケルトンを追加（モメンタム、MA、ATR、流動性、Value ファクター等を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針と定数を実装（calc_momentum の実装開始）。
- パッケージメタ
  - __init__.py: パッケージ名・初期バージョン（0.1.0）を設定。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- .env パーサの改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメント処理の強化。これにより実運用で一般的な .env フォーマットに耐性を向上。

### Notes / Limitations
- apply_sector_cap の価格欠損時の挙動に関する TODO コメントあり（価格が 0.0 の場合にエクスポージャが過小見積りされる可能性）。将来的に前日終値等のフォールバックを検討。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map を導入する設計拡張を計画。
- research/factor_research.py はファクター計算のフル実装を目指す設計だが、一部実装が途中（ファイル末尾で切れている）。今後の実装課題あり。
- run_monitoring は Monitoring 用 DB 接続に Settings.sqlite_path を常に使用する設計（監視は環境に依存せず本番 DB を見る方針）。運用上の分離が必要な場合は設定検討を推奨。

### Security
- .env ファイル生成時は「.env を絶対に Git にコミットしないこと」と明示。シークレット項目はウィザードでマスク表示。

----

今後の予定（参考）
- factor_research の各ファクター計算の完全実装とテスト
- ExecutionEngine / SystemMonitor の結合テストとエンドツーエンド検証
- 銘柄別 lot_size 管理、手数料/スリッページモデルの強化
- モニタリング・アラート（LINE 通知）の本番向け整備

(リリースノートはコード内容から推測して作成しています。実際のリリース履歴や変更意図と差異がある場合があります)