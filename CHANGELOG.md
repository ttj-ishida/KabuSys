Keep a Changelog
=================

すべての重要な変更点を記録します。  
このファイルは "Keep a Changelog" の慣習に従って作成されています。

フォーマット
----------
- 変更はバージョンごとにまとめ、Added / Changed / Fixed / Removed / Security などのカテゴリで整理します。
- 日付はリリース日（YYYY-MM-DD）を使用します。

## [Unreleased]
（現在のブランチでまだリリースされていない変更）

---

## [0.1.0] - 2026-04-17
初回公開リリース

### Added
- 基本アプリケーションモジュールを追加
  - kabusys パッケージのエントリポイント（__version__ = 0.1.0）。
- 設定・環境変数まわり
  - Settings クラスを実装してアプリ設定を環境変数から取得。J-Quants / kabu API / LINE / DB パス / 監視閾値などをプロパティで提供。
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env と .env.local の読み込み順をサポートし、OS 環境変数は保護（上書き禁止）。
  - .env パースロジックを強化：export プレフィックス対応、引用符内のエスケープ、インラインコメントの取り扱いを実装。
  - PAPER_FILL_MODE（paper trading の挙動）を導入し、許容値をバリデート。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）を提供。
- CLI ツール
  - config_setup: 対話式ウィザードで .env を生成/更新するユーティリティを追加。機密値は入力確認時にマスク表示。デフォルト値や選択肢を提示して安全に初期設定可能。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース（PyYAML がある場合）を行う。--strict モードで警告を失敗として扱う。
  - tools/paper_verification_report: ペーパートレード用検証レポート生成スクリプト。期間指定と DB パス指定が可能で、稼働率・注文成功率・送信率・レイテンシ（P95）を算出し PASS/FAIL を判定する。
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。起動時にプロセス優先度を高に設定。paper_trading 環境では専用の paper_trading.db を使用して本番 DB と完全分離。停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）を扱う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 monitoring.db を使用する点に注意。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: シグナルの選別（select_candidates）と配分重み（calc_equal_weights, calc_score_weights）を実装。score が全て 0 の場合は等重配分へフォールバックし警告を出す。
  - risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに基づく乗数 calc_regime_multiplier を実装。unknown セクターはセクター上限の対象外とする。未知レジームは 1.0 でフォールバックしログ警告を出す。
  - position_sizing: 発注株数算出 calc_position_sizes を実装。risk_based / equal / score の allocation_method に対応、lot_size に基づく丸め、1 銘柄上限や aggregate cap によるスケーリング（残差処理で再配分）を行う。コストバッファ（手数料・スリッページ見積）を考慮。
- リサーチ / ファクター計算
  - research/factor_research: DuckDB 接続を使ったモメンタム・ボラティリティ等のファクター計算（calc_momentum, calc_volatility 等）。prices_daily / raw_financials のみ参照し外部 API に依存しない設計。
- ユーティリティ
  - utils/process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを実装。Windows / POSIX の差分を吸収し、psutil を利用。権限不足や未対応 OS では警告ログを出してスキップする。

### Changed
- DB 接続の分離ポリシー
  - run_execution は paper_trading 環境時に paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して、本番 monitoring DB とデータを分離するように設計。
  - run_monitoring は監視データ保存に常に本番 sqlite_path（Settings.sqlite_path）を使用する挙動を明確化（環境に依存しない）。
- ログ・起動フローの改善
  - run_execution / run_monitoring 起動時にプロセス優先度を最初に設定して安定性を向上。
  - run_execution のスレッド管理で停止フラグ検知時に ExecutionEngine.stop() を呼び、最大待機時間を導入して終了の安定性を高めた。
- .env 読み込みの優先順位と保護
  - OS 環境変数を保護（protected）して .env/.env.local の読み込みで意図せぬ上書きを防止するようにした。
  - .env.local は .env より後に読み込み（上書き）され、開発者ローカルの調整を優先できる。

### Fixed
- 環境変数パースの堅牢化
  - 引用符つき値内のバックスラッシュエスケープや export プレフィックス、行末のインラインコメント処理を正しく扱うように修正。
  - 無効な .env 行（キーバリューでない行）を安全にスキップするようにした。
- 配分・サイズ計算の安定化
  - calc_score_weights で全スコアが 0.0 の場合にゼロ除算を起こさず等金額配分にフォールバックし、警告ログを追加。
  - calc_position_sizes における aggregate スケールダウン後の残差分配ロジックで再現性（安定したソート順）を確保し、lot_size 単位での調整を正しく処理。
- プロセス優先度設定の失敗安全化
  - psutil のプラットフォーム差異や権限不足／未サポート API の場合に例外を握りつぶしてアプリを継続するようにした（警告ログを出力）。

### Security
- config_setup の対話式入力で機密値（J-Quants トークン、kabu API パスワード、LINE トークン）をマスク表示し、.env 出力時に誤って公開しないよう文言で注意を表示。
- .env は Git に絶対にコミットしない旨をテンプレートに明記。

### Documentation
- 各モジュールに docstring を追加・整備して使用方法や引数/戻り値の仕様を明確化。
- CLI（config_setup, validate_config, paper_verification_report）のヘルプメッセージを充実。

---

今後の予定（例）
- more granular lot_size per stock（銘柄ごとの単元対応）への拡張 TODO を position_sizing に記載。
- リスク・ストレステスト用の追加レポート、バックテスト連携の強化。
- research モジュールの追加ファクターと Z スコア正規化連携（kabusys.data.stats を利用）。


注記
----
- 本 CHANGELOG はソースコードの内容から推測して作成した初期の変更履歴です。リリースノート作成時に実際のコミット履歴やリリース差分に合わせて追記／修正してください。