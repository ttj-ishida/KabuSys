# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
各リリースには主な追加機能・変更点・修正点を日本語で記載しています。

なお、以下の内容はリポジトリ内のソースコードから推測して記載したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

### Added
- 監視・実行用のランチャースクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB から完全分離。
    - 実行用 PID ファイル（data/execution.pid）管理、停止フラグ検出時に安全に停止。

- 設定関連の CLI を追加
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新。
    - シークレット値のマスク表示、選択肢のバリデーション、.env 保存時のテンプレート出力。
    - .env を絶対にコミットしない旨の警告を出力。
  - validate_config.py
    - 環境変数と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等の妥当性チェック、DB パスの親ディレクトリチェックを実装。
    - PyYAML が無い場合は YAML 検証をスキップ（警告出力）。--strict オプションで警告を FAIL 扱いにできる。

- 設定管理機能の追加/強化
  - config.py
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env の堅牢なパース実装（export プレフィックス対応、シングル/ダブルクォートおよびエスケープ処理、インラインコメントの扱い）。
    - Settings クラスを公開し、環境変数の取得・バリデーションを提供（各種パス、閾値、paper_trading 用設定など）。
    - PAPER_FILL_MODE の値チェック（instant/partial/never/reject）を実装。

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、同点時は signal_rank 昇順のタイブレークを実装。
    - calc_equal_weights / calc_score_weights: スコアがすべて 0 の場合は等金額配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。
    - リスクベース計算、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）対応。
    - 価格未取得時のスキップや上限（max_position_pct / max_utilization）適用を実装。

- 分析・検証ツールを追加
  - tools.paper_verification_report.py
    - ペーパートレード用 DB から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計しレポート出力。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）と DB パス上書きオプション（--db）を提供。

- ユーティリティ類
  - utils.logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保管）をルートロガーに設定。
    - ログディレクトリの作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログ設定の再設定時に既存ハンドラを明示的に閉じてから差し替える実装。
  - utils.process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供（権限不足・未対応 OS 時は警告でスキップ）。

- DuckDB 統合
  - 一部モジュールで duckdb 接続を受け取り、分析用データ（prices_daily 等）を扱う設計に対応。

### Changed
- ロギングの挙動の標準化
  - すべての起動スクリプトから setup_logging を呼び出す想定によりログ出力が統一。
  - StreamHandler を stdout に出力する方針（cron 等からのリダイレクトを想定）。

- DB パス・環境分離の方針明確化
  - 監視 (monitoring) は環境にかかわらず監視用（本番） sqlite_path を使用する設計。
  - 実行 (execution) は KABUSYS_ENV に応じて paper_trading 用 DB を選択し、ペーパートレードは本番 DB と完全分離。

### Fixed
- .env 読み込みの堅牢化
  - シングル/ダブルクォート内でのバックスラッシュエスケープなどを正しく解釈するよう改善。
  - .env の自動ロードはプロジェクトルートが特定できない場合はスキップするように変更。

### Security
- .env を明示的に Git 等へコミットしない旨を config_setup のテンプレートに記載（機密情報保護の注意喚起）。

---

## [0.1.0] - 2026-04-18

初回公開リリース。上記の機能を含む最初のパブリックバージョン。

### Added
- プロジェクト基本機能一式を実装・公開
  - 実行・監視用ランチャー (run_execution.py / run_monitoring.py)
  - 設定ロード・Settings クラス（config.py）
  - 設定ウィザードと検証ツール（config_setup.py / validate_config.py）
  - ポートフォリオ構築（選定・重み付け・リスク調整・ポジション決定）
  - ExecutionEngine 等の呼び出しインフラ（BrokerClientFactory を介したブローカ抽象化、OrderManager / RiskManager 等の組立）
  - ロギング・プロセス優先度設定ユーティリティ
  - ペーパートレード検証レポートツール
  - DuckDB を用いた分析対応

### Changed
- すべての起動スクリプトで同一のログ設定を利用するように統一。

### Fixed
- N/A（初回リリースのため既知の小修正を含まず）

---

注:
- この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のコミットメッセージや履歴に合わせて適宜調整してください。