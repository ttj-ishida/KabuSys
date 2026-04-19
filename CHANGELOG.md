# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリースポリシー: 0.x 系はまだ安定版扱いではなく、互換性は保証されません。

## [0.1.0] - 2026-04-19

初回公開リリース。以下の主要機能・ユーティリティを導入しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 実行エントリ / デーモン風スクリプト
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` によるフラグ検知で行う。
    - 監視用 DB は環境にかかわらず本番用の sqlite_path を使用する実装。
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、専用の paper trading DB（`data/paper_trading.db`）へ記録して本番 DB と分離。
    - 停止フラグと PID ファイル（`data/execution.pid`）の扱いを実装。
    - スレッドでエンジンを実行し、フラグ検知で安全に停止する制御を実装。

- 設定・環境管理
  - Settings クラス: `src/kabusys/config.py`
    - 環境変数／.env ファイルからの設定取得を一括管理するクラスを追加。
    - 自動 .env 読み込み機構（プロジェクトルートを自動検出し、`.env` → `.env.local` の順で読み込み）を実装。OS 環境変数は保護（上書き不可）。
    - 各種設定プロパティを用意（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連設定、閾値等）。
    - `PAPER_FILL_MODE` の値検証（"instant" / "partial" / "never" / "reject"）。
    - `KILL_FLAG_CLEAR_ON_START` 等の bool フラグをサポート。
    - `Settings` インスタンスを `settings` としてモジュール末尾でエクスポート。

- 設定支援ツール / 検証ツール
  - config_setup: `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を初期作成／更新する CLI を追加。
    - デフォルト値、選択肢、シークレット表示（マスク）、保存確認などの UX を備える。
  - validate_config: `src/kabusys/validate_config.py`
    - .env と config/*.yaml の整合性・必須環境変数のチェックを行う CLI を追加。
    - PyYAML が存在すれば YAML パース検証を行い、不在時はスキップして警告を出力。
    - `--strict` フラグで警告を FAIL として扱うモードを提供。

- ロギング / プロセスユーティリティ
  - Logging setup: `src/kabusys/utils/logging_setup.py`
    - コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定するユーティリティを追加。
    - ログディレクトリ（`logs/`）の自動作成、`LOG_DIR`/`LOG_LEVEL` 環境変数対応、30 日分のローテーション保持を実装。
  - Process priority / affinity: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - アクセス権限不足や未対応 OS では安全にフォールバック。

- ポートフォリオ構築ライブラリ
  - portfolio_builder: `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 select_candidates（スコア降順・タイブレーク処理）。
    - 等配分 calc_equal_weights、スコア重み calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment: `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap：セクター集中制限を適用し、既存エクスポージャ超過セクターの新規候補を除外。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 にフォールバック。
  - position_sizing: `src/kabusys/portfolio/position_sizing.py`
    - calc_position_sizes：等配分／スコア配分／リスクベースの発注株数計算を実装。単元（lot_size）丸め、最大ポジション比率・投下上限・コストバッファ・スケーリング（aggregate cap）を考慮。
  - package export: `src/kabusys/portfolio/__init__.py` にて上記関数群を公開。

- 分析・検証ツール
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計・判定する CLI を追加。
    - 判定基準（閾値）を定義し、PASS/FAIL 判定と詳細レポートを出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。

- 研究・ファクター計算基盤（初期）
  - factor_research: `src/kabusys/research/factor_research.py`（骨組み）
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計方針を実装開始（モメンタム等の定数や関数雛形を含む）。
    - 将来的なファクター計算の基礎となるモジュール。

- DB 初期化ユーティリティ（監視用）
  - monitoring_db 初期化呼び出しを run_monitoring / run_execution で行い、監視テーブルが存在することを冪等に保証（`init_monitoring_db` を利用）。

### Changed
- 環境変数読み込みの振る舞い
  - `.env.local` は `.env` の上書きとして読み込まれる（OS 環境変数は保護される）。
  - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- ログ出力のデフォルト
  - コンソールは stdout を使用し、stderr ではなく stdout に統一（cron/task scheduler と組み合わせる際の扱いを容易化）。

### Fixed
- .env パーサの堅牢化
  - `src/kabusys/config.py` の `_parse_env_line` はクォート内のバックスラッシュエスケープやインラインコメントの扱いを考慮するよう改善し、より現実的な .env の記述に耐えるようにした。

- run_monitoring の例外ハンドリング
  - `monitor.check_once()` で予期しない例外が発生しても監視ループを継続し、ログにトレースを残して次のポーリングに進むようにした。

### Security
- 秘密情報の取り扱い
  - `config_setup` の対話ではシークレット入力をマスク表示し、`.env` の生成に際して Git にコミットしない旨の注意をファイル先頭に明記。

### Notes / Implementation details
- Paper Trading 分離
  - Paper Trading 実行時は `Settings.paper_sqlite_path` を使い、本番用 SQLite とは完全に分離する設計。
- デフォルト値
  - 多くの値に合理的なデフォルトを設定（例: `MONITOR_POLL_INTERVAL=60`, `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`, ログローテーション 30 日など）。
- フォールバック挙動
  - 未知の値・欠損データ・環境差（OS）に対して安全にフォールバックするよう実装（Unknown regime → multiplier=1.0、ログディレクトリ作成失敗時はファイル出力をスキップ、psutil の定数非対応時のフォールバック等）。

今後の予定（非網羅）
- research モジュールのファクター計算を完成させる（メモリ効率、DuckDB 最適化）。
- Strategy / Execution の詳細実装・テスト補完（リスク管理・再帰整合処理など）。
- 監視・アラート（LINE 通知）や運用向けガードの強化（KILL スイッチ運用の成熟化）。
- ドキュメント（使い方、設定例、運用手順）の整備。

もし特定の変更点をより詳細に書き起こしてほしい場合（例: run_execution の起動フローや calc_position_sizes のスケーリングロジック等）、どの箇所を重点的に記載するか教えてください。