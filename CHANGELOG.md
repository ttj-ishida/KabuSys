CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します（Keep a Changelog 準拠）。
このリポジトリの現在のパッケージバージョン: 0.1.0

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

初回公開リリース。以下の主要機能・ユーティリティ・ツールを追加しました。

### Added
- パッケージ基本構成
  - パッケージメタ情報（src/kabusys/__init__.py にて __version__="0.1.0" を定義）。
- 実行/監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止用フラグファイル（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応し、外部からの停止制御をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行い SystemMonitor.check_once() を定期実行。
    - 停止フラグ検知でループ終了、例外はログ出力して次ポーリングへ継続。
- 設定管理
  - config.py: 環境変数/UI 設定をまとめる Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env/.env.local の読み込み順と保護（既存 OS 環境変数を上書きしない）を実装。
    - 環境変数の必須チェック用ヘルパー _require、PAPER_FILL_MODE の検証、パス（duckdb/sqlite/pid 等）の Path 変換を提供。
    - is_live/is_paper/is_dev 布告的プロパティを追加。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（項目定義・既存 .env 読込・保存機能）。
  - validate_config.py: 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml 存在確認）。
    - PyYAML 未導入時は YAML 検証をスキップし警告。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 世代保持）を設定する setup_logging を追加。
    - LOG_DIR 指定や LOG_LEVEL 解決、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py:
    - psutil を用いたプロセス優先度設定（Windows / POSIX を吸収）と CPU affinity 設定ユーティリティを追加。
    - 権限不足などの場合は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順選択）、calc_equal_weights、calc_score_weights を実装。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター上限による候補除外）、calc_regime_multiplier（レジームに応じた資金乗数）を実装。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、per-position 上限、aggregate cap（資金不足時スケールダウン）および cost_buffer を考慮した安全なスケーリングを実装。
- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py にモメンタム等のファクター計算を追加（DuckDB 接続を受け prices_daily などのテーブルを参照する設計）。（注: ファイル末尾が一部未完な箇所あり。）
- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレーディング用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率・注文成功率・送信率・レイテンシ (avg/max/P95) を集計してレポート出力。
    - PASS/FAIL 判定閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from/--to）、DB パス指定（--db）に対応。
- DB/監視補助
  - monitoring.monitoring_db.init_monitoring_db を参照して、起動時に監視テーブルが存在することを保証する処理を run_* スクリプト双方に組み込み。
- その他ユーティリティ
  - .env 解析の堅牢化: export KEY=val 形式対応、クォート内のバックスラッシュエスケープと閉じクォート探索、インラインコメント処理（引用なしでは '#' の前にスペースがある場合のみコメントとみなす）などを実装。

### Changed
- ログ出力の統一:
  - 全起動スクリプトは setup_logging(app_name=...) を呼び出すようにしてログフォーマット・ファイル名を統一。
- run_monitoring/run_execution の DB 接続動作:
  - 監視プロセスは常に設定の sqlite_path（本番監視 DB）を使用する点を明示。
  - Execution は paper_trading 環境なら paper_sqlite_path を使い本番 DB と分離。

### Fixed / Hardened
- 設定読み込みの失敗耐性:
  - .env ファイル読み込みでファイルオープン失敗時に警告を出して継続するように変更。
  - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールログのみで継続。
- プロセス優先度および CPU affinity 設定において、権限不足や未サポート OS の場合に例外を投げず警告でスキップするように改善。
- run_monitoring のポーリング間隔取得で不正値（0 以下や非整数）を検出した場合に警告を出してデフォルト（60 秒）へフォールバック。

### Security
- config_setup で生成される .env に対して「絶対に Git にコミットしないこと」を明示するヘッダを追加（.env を機密情報として扱う旨の注意喚起）。

### Documentation / UX
- config_setup.py と validate_config.py に CLI ヘルプ・使用例を追加し、起動前のチェックフロー（設定ウィザード → validate_config）を推奨。
- tools/paper_verification_report.py の出力は見やすいレポート形式に整形し、データ不足時の N/A 表示やエラー時のメッセージを明確化。

### Dependencies / Optional
- duckdb と psutil を実行時依存として利用。
- PyYAML は config/*.yaml の内容検証で任意（未導入時は警告してスキップ）。

Notes
-----
- 初期リリースのため今後の改善候補:
  - research/factor_research の一部実装補完（ファイル末尾に未完箇所あり）。
  - 銘柄ごとの lot_size や価格フォールバックロジックの拡張（コメントで TODO を記載）。
  - ExecutionEngine / SystemMonitor 等コアコンポーネントの詳細（このリリースではエントリポイントからの組立て・起動ロジックを追加済み）。
- 本リリースでは機密情報（API トークン・パスワード等）を .env で管理する設計であり、.env を VCS に含めない運用が重要です。