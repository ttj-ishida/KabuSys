CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは、コードベースから推測される機能追加・改善点・注意点を基に作成しています。

Unreleased
----------

- 注意 / TODO
  - research/factor_research.py が途中で切れており（実装未完/省略あり）、追加実装が必要です。
  - position_sizing.calc_position_sizes 内に将来的な拡張（銘柄別 lot_size を持たせる等）の TODO が残っています。
  - price が欠損した場合のフォールバック価格戦略（risk_adjustment.apply_sector_cap の注記）など、いくつかの堅牢化ポイントがコメントで示されています。

v0.1.0 - 2026-04-21
-------------------

Added
- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag により検知してグレースフルに終了。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py を追加。
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離。
    - エンジン実行はデーモンスレッドで行い、停止フラグにより停止可能。PID ファイルの管理機能あり。

- 設定 / 環境読み込み
  - config.py を追加。
    - .env/.env.local の自動ロード（OS 環境変数を優先し、上書き保護あり）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
    - Settings クラスを提供し、設定値（パス・閾値・API トークン等）をプロパティとして取得可能。
    - KABUSYS_ENV, LOG_LEVEL 等の妥当性チェックと変換ロジックを実装。
    - PAPER_FILL_MODE の妥当性検証や Paper Trading 用 DB パス（paper_sqlite_path）を提供。

- 設定ツール / 検証
  - config_setup.py を追加。
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - シークレット項目のマスク表示、選択肢・デフォルト提示、既存 .env 読み込みをサポート。
  - validate_config.py を追加。
    - 起動前検証ツール。必須環境変数やパス、YAML ファイルの存在（PyYAML があればパース検証）などをチェック。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルスコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。スコア合計が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を計算して上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based ではリスク許容率・損切り率に基づく単位数計算。aggregate cap を超える場合はスケールダウンし、lot_size 単位で再配分するロジックを実装。
    - cost_buffer を使った保守的コスト見積もりによりスケーリングを考慮。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティ。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソール出力のみ行うフェールセーフ。
    - ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows: PRIORITY_CLASS, POSIX: nice）。
    - CPU affinity を最初の N コアに固定するヘルパー。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ(P95) 等を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - コマンドラインで期間指定 (--from / --to)／DB 指定 (--db) が可能。

- データベース・分析
  - DuckDB を分析用に使用（duckdb_path を Settings で管理）。多くのモジュールが DuckDB 接続を受け取り分析クエリを実行する設計。

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- 監視/実行の挙動統一
  - すべての起動スクリプトで最初に set_process_priority("high") を呼び出すようにしてプロセス優先度の標準化を導入。
  - ロギングの統一インターフェース (setup_logging) を全スクリプトで利用。

Fixed
- .env 読み込みの堅牢化
  - export プレフィックスや引用符、バックスラッシュエスケープ、行内コメントの処理などをサポートし、より実用的な .env パーサを実装。

Removed
- なし（初期リリース相当のため該当なし）。

Security
- 環境変数の必須チェック（J-Quants トークン、kabu API パスワード）や .env の自動ロード保護（OS 環境変数の上書きを防ぐ protected set）を実装。秘密情報は config_setup の対話でマスク表示。

Notes / Design decisions
- run_monitoring は環境に依らず本番用 sqlite_path を監視 DB として使用する設計になっています（監視は本番対象に対して行う想定）。
- run_execution は paper_trading 環境時に完全に本番 DB と分離する（paper_sqlite_path を使用）実装です。ペーパートレードの結果を本番データと混ぜない運用を想定しています。
- position_sizing では lot_size を共通値で扱う設計だが、将来的に銘柄別の lot_map を導入する余地を残しています（TODO）。
- risk_adjustment.apply_sector_cap は "unknown" セクターの銘柄を除外対象にしない方針。価格欠損時にエクスポージャーが過少評価される可能性があるため、将来的にフォールバック価格の導入を検討中。

Acknowledgments
- ログや設定周り、起動スクリプト、ポートフォリオ構築ロジック、Paper Trading 検証ツールなど、初期リリースに必要な主要機能を揃えた構成になっています。今後の実運用に向けて、テスト・例外処理・データ欠損対応の強化を推奨します。