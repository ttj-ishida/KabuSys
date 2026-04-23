# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の SQLite（data/paper_trading.db 等）を使用する分離設計、BrokerClientFactory 経由のブローカークライアント生成、Engine のデーモンスレッド起動と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を参照する仕様。
- 設定管理
  - config.py: .env 自動ロード（プロジェクトルート判定による）、複数の設定プロパティ（DB パス、API トークン、環境判定、しきい値など）を提供する Settings クラスを追加。PAPER_FILL_MODE のバリデーション等を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。複数の設定項目を対話的に入力し .env を生成・更新可能。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML が利用可能な場合）等を検証。--strict オプションをサポート。
- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール(stdout) と 日次ローテートファイルログ(TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX(nice) に対応。アクセス権や未サポート環境では警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中排除ルール（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出（risk_based / equal / score）を実装。単元株（lot_size）で丸め、aggregate cap（available_cash）超過時はスケールダウンと残差処理を行う。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- 監視・検証ツール
  - monitoring DB 初期化フック（init_monitoring_db）呼び出しを各起動スクリプトに追加（監視テーブルが存在することを保証）。
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力するツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を行う。期間フィルタと DB パス指定オプションをサポート。
- 研究用モジュール（初期実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム / MA / ATR / ボラティリティ / 流動性等の計算方針を定義）。（一部実装が途中のファイルあり）

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Known issues
- factor_research.py の実装が途中で終端（ファイルが途中で切れている）。今後、SQL クエリや計算ロジックの完成が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされて除外が漏れる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討。
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size（単元）をサポートする設計拡張の TODO コメントあり。
- run_execution.py / run_monitoring.py:
  - 停止制御は data/stop_requested.flag を用いる。運用時はフラグ管理と PID ファイルの整合に注意。
- .env 自動ロード:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする仕組み。テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- PAPER_FILL_MODE 等、環境変数の値検証は厳密（無効値は例外を発生させる）。本番環境では .env の設定を validate_config で事前検証することを推奨。

### Security
- 環境変数取り扱い:
  - config_setup.py は .env を生成するが、.env を絶対にリポジトリにコミットしないようヘッダコメントで注意喚起。
  - 機密値入力項目はマスク表示（対話ウィザード）されるが、保存される .env は平文であるため運用上の管理を厳密に行うこと。

---

今後の改善予定（例）
- research/factor_research の完成とユニットテスト整備
- broker クライアントに対するモックやテスト用フックの強化
- エラーメトリクス収集と自動アラート連携（LINE 通知の整備）
- 銘柄別単元（lot_size）や価格フォールバック戦略の導入

もし CHANGELOG に追加してほしい細かな差分（例: 特定ファイルでの注目コミット、あるいは日付やリリース名の変更）があればお知らせください。