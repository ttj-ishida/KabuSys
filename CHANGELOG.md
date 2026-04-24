# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを意識して記載しています。

注: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。

## Unreleased
- なし（今後の変更予定をここに記載してください）

## [0.1.0] - 2026-04-24
初回リリース。

### Added
- 基本ライブラリとアプリケーション構成
  - Settings クラスを提供する `kabusys.config` を実装。
    - .env 自動読み込み機能（.env / .env.local）をプロジェクトルート検出に基づき行う。
    - .env の読み込みで OS 環境変数を上書きしない保護機構を実装。
    - 必須環境変数取得用の _require() と各種設定プロパティ（DB パス、API トークン、環境判定フラグ等）を提供。
    - PAPER_FILL_MODE 等の入力バリデーションを実装。
- 環境設定・検証用 CLI
  - `kabusys.config_setup`：.env の対話式ウィザードでの作成・更新を実装。
    - シークレット入力、選択肢、既存値の再利用、.env の書き込みロジックを提供。
  - `kabusys.validate_config`：起動前に環境変数や config/*.yaml の存在・簡易構文検証を行う CLI を実装。
    - 必須環境変数検査、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば実施）、本番環境向けガード等をチェック。
    - --strict オプションで警告を失敗扱いにできる。
- 実行コンポーネント起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て〜 ExecutionEngine の起動・停止ループ（スレッド）を実装。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 監視コンポーネント起動スクリプト
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する仕様。
    - 停止フラグ検知、例外発生時のログ保持、SQLite / DuckDB 接続の初期化・クローズを実装。
- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`：統一的ログ設定ユーティリティを実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ディレクトリ作成失敗時のフォールバックを実装。
  - `kabusys.utils.process_priority`：psutil を使ったプロセス優先度・CPU affinity 設定ユーティリティを実装。
    - Windows / POSIX (Linux, Darwin, FreeBSD) 間の差分吸収、アクセス権限失敗時の警告ロギング、set_cpu_affinity を提供。
- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全てが 0 の場合は等配分へフォールバック。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap：セクター集中を抑えるための候補フィルタリングを実装（売却予定銘柄除外や unknown セクター扱いの挙動を明示）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームは 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position と aggregate の上限、コストバッファ考慮、スケールダウンと残差処理の実装。
- Paper Trading / 検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード用の SQLite を参照して検証レポートを出力する CLI を実装。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（P95 を含む）を集計・判定。
    - デフォルト閾値を定義（稼働率 99% など）し PASS/FAIL を判定。
    - 日付フィルタ機能（--from / --to）と DB パス指定（--db / 環境変数）を提供。
- 研究（計算）モジュール（部分実装）
  - `kabusys.research.factor_research`：ファクター計算の土台を実装（Momentum / Value / Volatility / Liquidity の設計方針、calc_momentum の一部を含む）。DuckDB を想定したデータ参照設計。

### Changed
- なし（初回リリースのため変更項目はありません）

### Fixed
- なし（初回リリースのため修正履歴はありません）

### Notes / Implementation details
- .env のパーサは quoted 値のバックスラッシュエスケープや inline コメントの扱いなどを考慮して堅牢に実装している。
- ログは stdout を標準出力にし、ファイル出力に失敗してもコンソール出力は継続するよう設計されている（cron 等でのリダイレクトを考慮）。
- プロセス優先度設定は権限エラーや未対応 OS を安全にスキップするフォールトトレラントな実装になっている。
- Paper Trading と本番のデータストアは明確に分離される（paper_sqlite_path を使用）。
- 一部ファイル（例: factor_research）は途中までしか含まれておらず、今後の実装で補完が想定される（TODO コメントあり）。

---

今後のリリースでは次のような改善が想定されます（例）:
- factor_research の完実装（全ファクター計算と正規化ユーティリティ統合）
- ExecutionEngine / SystemMonitor の詳細なログとメトリクスの拡充
- 単体テストおよび CI 設定の追加
- 銘柄ごとの lot_size マスタ対応（position_sizing の拡張）

以上。必要であればこの CHANGELOG を英語化したり、バージョン／日付を調整したりできます。どの形式で出力するか（ファイルに保存・PR 用コピー等）指示してください。