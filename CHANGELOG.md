# CHANGELOG

すべての注目すべき変更を記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアントの生成、OrderManager/RiskManager/Reconciler 組み立て、スレッドでのセッション実行および停止フラグによる安全停止を実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループを終了、例外発生時はログ出力のうえ次サイクルへ継続。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定・環境管理
  - config.py: .env 自動読み込み機能を導入（プロジェクトルートの探索に .git または pyproject.toml を使用）。.env/.env.local の読み込み順・保護キー概念（OS 環境変数を上書きしない）を実装。.env の各行のパースを堅牢化（export プレフィックス、クォートやエスケープ、インラインコメント処理等）。Settings クラスで各種設定プロパティを提供（J-Quants / kabu API / DB パス / paper_trading 関連 / 監視閾値 / 環境判定等）。PAPER_FILL_MODE のバリデーションを実装。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加。デフォルトや既存値の再利用、シークレットのマスク表示、確認後の書き込みをサポート。
  - validate_config.py: 起動前検証用 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境用のガードチェックなどを実行。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続する、安全なハンドラ再設定処理を実装。
  - utils/process_priority.py: psutil を用いてプラットフォーム差異を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定を追加。Windows/Linux/macOS を考慮し、権限不足や未対応環境では警告出力でフォールバックする。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク）、等重配分、スコア加重配分（全スコア 0 の場合は等重へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（既存ポジションのセクター露出を計算して候補を除外）と市場レジームに応じた資金乗数（bull/neutral/bear）を実装。未知レジーム時のフォールバックとログ警告あり。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づき発注株数を計算する実装を追加。単元株丸め、1 銘柄上限・全体投下上限（aggregate cap）、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリング、余剰キャッシュを用いた端数分配ロジックなどを実装。

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite データベースから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定（閾値はソース内定義）。日付フィルタ、DB パス指定や環境変数経由の DB 指定をサポート。

- その他
  - research/factor_research.py（着手）: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタムや MA/ATR 等の定義、設計方針記載）。処理の一部は実装途中。

### Changed
- アプリケーション初期設計の整理とドキュメント化
  - 各モジュールに詳細な docstring と使用上の注意（例: ファイル入出力失敗時のフォールバック、空データ時の挙動）を追記。将来的な拡張点（銘柄別 lot_size の導入や価格フォールバック）について注記。

### Fixed
- 起動スクリプトやユーティリティでの安全なリソースクローズ処理を強化（DB 接続やハンドラの flush/close を適切に行うように修正）。

### Security
- .env を自動生成する際の注意喚起を .env テンプレートに明記（.env を Git にコミットしない旨）。

---

初回リリース（0.1.0）では、実運用を想定した監視・実行基盤、設定管理、ロギング、プロセス制御、ポートフォリオ構築と発注量算出ロジック、及びペーパートレードの検証ツールを揃えています。今後は research モジュールの完成、各コンポーネントの単体テスト強化、設定/運用の自動化（CI/CD）などを予定しています。