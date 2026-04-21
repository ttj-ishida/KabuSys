# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお本 CHANGELOG は、提供されたソースコードの内容から機能追加・修正点を推測して作成したものです。

## [Unreleased]

- ドキュメント化や小規模な内部改善など、リリースに含めるか検討中の変更や小さな修正を集約する予定です。

---

## [0.1.0] - 2026-04-21

最初の公開リリース。主要コンポーネントの初期実装を含みます。

### 追加 (Added)

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 DB を使用し、MockBrokerClient の利用を想定。停止フラグ、PID ファイル管理、バックグラウンドスレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB 初期化処理を行い、停止フラグでループを終了。

- 設定管理
  - config.py: 環境変数/`.env` ファイルからの設定読み込みと Settings クラスを実装。J-Quants / kabuステーション / LINE / DB /監視閾値など多くの設定プロパティを提供。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を自動読み込み（OS 環境変数は保護）。

- 設定ツール
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新する CLI を追加。
  - validate_config.py: 起動前に環境変数・config/*.yaml の基本的な検証を行う CLI を追加。`--strict` オプションで警告をエラー扱いにできる。PyYAML 未インストール時のフォールバックや本番環境向けガードも実装。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定・StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を提供。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py: Windows/Linux/Mac に対応したプロセス優先度設定と CPU affinity 設定のユーティリティを追加（psutil を利用）。プラットフォーム差分を吸収。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコア順）、等配分・スコア加重配分の実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score 対応）、単元株丸め、全体キャップに基づくスケーリング、コストバッファを考慮した実装。

- 研究・分析
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの実装（モメンタム / MA200 / ATR / 流動性等の算出、設計方針と定数を含む）。（実装は途中まで提供）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ等を集計して検証レポートを出力するスクリプトを追加。閾値と PASS/FAIL 判定ロジックを実装。コマンドライン引数で期間・DB パスを指定可能。

- パッケージ情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更 (Changed)

- DB 周りの設計
  - run_monitoring は環境に依らず本番用の sqlite_path を参照する方針とし、monitoring 用テーブルを初期化する init_monitoring_db を必ず呼び出すようにした（冪等処理）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離する動作を追加。

- env ファイルパーサ
  - _parse_env_line が export プレフィックスやクォート・バックスラッシュエスケープ、インラインコメントの扱いに対応するよう拡張され、現実の .env フォーマットへの互換性を向上。

- ログ仕様
  - logging_setup の既存ハンドラクリアやログレベル解決の挙動を明確化。コンソールには stdout を使う設計に変更（cron 等で stdout/stderr を一元化しやすくするため）。

### 修正 (Fixed)

- 環境変数の上書き制御
  - .env 自動読み込み時に OS 環境変数を保護するロジックを導入。`.env.local` の override は可能だが既存の OS 環境変数は上書きされないようになった。

- ポジションサイズ計算の丸め・制限
  - calc_position_sizes において単元株（lot_size）での丸め処理、1 銘柄上限（max_position_pct）や aggregate cap によるスケールダウン処理、コストバッファ考慮を明示的に実装。端数配分は残差に基づいて安定的に行う実装を追加。

- run_execution / run_monitoring のリソースクリーンアップ
  - 両スクリプトとも finally ブロックで sqlite/duckdb 接続を確実にクローズするようにした。

### その他 (Misc)

- validate_config による config/*.yaml の構文チェック（PyYAML が存在する場合）や KABUSYS_ENV=live に対する安全ガード（LINE 通知設定や Kill フラグの自動クリア設定）を追加。
- paper_verification_report のレポートは P95 レイテンシ算出、各種指標の N/A 処理、閾値定義（稼働率・成功率・送信率・P95）を備える。

---

注記:
- 上記はコードベースの内容から推測してまとめた変更点です。実際のコミット履歴や既存のリリースノートとは差異がある可能性があります。正確な履歴を作成するには Git のコミットログや開発者の変更記録を参照してください。