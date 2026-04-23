# Changelog

すべての注目すべき変更をこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

なし

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム "KabuSys" の基本機能を追加しました。

### Added（追加）
- 基本パッケージ情報
  - パッケージバージョンを追加（src/kabusys/__init__.py: `__version__ = "0.1.0"`）。

- 起動スクリプト
  - 実行エンジンスクリプトを追加（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db デフォルト）を使用し、MockBrokerClient 経由で分離されたペーパートレード実行をサポート。
    - _STOP_FLAG（data/stop_requested.flag）を監視して安全に停止できる仕組みを実装。
    - 実行中の PID を data/execution.pid に記録する仕組みを想定（pid_file を受け渡し）。
    - RiskManager、OrderManager、Reconciler 等の組み立てと ExecutionEngine のスレッド実行ロジックを実装。
    - duckdb 接続を受け取り分析用 DB と連携。

  - 監視モニタ起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（data/monitoring.db デフォルト）を使用する設計。
    - data/stop_requested.flag による停止検知を実装。
    - 例外発生時のログ出力とリトライループを実装。

- 設定管理・検証・インストール支援
  - Settings クラスを追加（src/kabusys/config.py）
    - .env および .env.local の自動ロード（OS 環境変数を保護して上書き挙動を制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 閾値設定など）をプロパティで取得。
    - 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - is_live / is_paper / is_dev ヘルパーを提供。

  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）
    - .env の初期作成・更新を支援する CLI ウィザード。
    - 秘匿項目はマスク表示、既存値の再利用、選択肢のバリデーション、保存前の確認を実装。
    - .env の書き出しテンプレートを提供（コミット禁止の注意書き含む）。

  - 設定検証コマンドを追加（src/kabusys/validate_config.py）
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検査（PyYAML 未インストール時は警告）等を実装。
    - --strict モードで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保管）をルートロガーに設定。
    - ログレベル / ログディレクトリの決定ロジック（引数 > 環境変数 > デフォルト）。
    - 既存ハンドラの安全な再設定と、ディレクトリ作成失敗時のフォールバック処理を実装。

  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収した優先度設定（high/normal/low）。
    - psutil を用いた実装。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity を提供（最初の N コアに固定）。

- ポートフォリオ構築ライブラリ（純関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有比率が閾値を超えるセクターの新規候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を提供。未知のレジームは 1.0 でフォールバックし警告を出す。

  - 株数決定・投下資金制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた発注株数計算（risk_based, equal, score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash） に対するスケーリング、cost_buffer を考慮した保守的見積り。
    - スケールダウン時の残差配分ロジック（fractional remainder）を実装。

  - 上記をまとめたパッケージエクスポート（src/kabusys/portfolio/__init__.py）

- Research / Tools
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）
    - Momentum / MA200 / ATR / Volume 等の計算ロジック設計を実装（DuckDB を用いる想定）。
    - 注意書き・計算窓長の定義を含む（ファイル途中で実装継続中の箇所あり）。
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite DB を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等の指標を集計・表示。
    - 閾値を定義して PASS/FAIL 判定を行う。日付範囲指定（--from / --to）や DB パス指定（--db）に対応。
    - 空やテーブル欠損時の耐性（sqlite3.OperationalError を捕捉して N/A 指定）を実装。

### Changed（変更）
- 環境変数ローディング挙動
  - .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うように変更。プロジェクトルートが特定できない場合は自動ロードをスキップして、配布後の動作を安定化。

- .env パーサーの堅牢性強化（src/kabusys/config.py）
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメントの扱い改善を実装。
  - 上書きルール（override / protected）を導入し OS 環境変数を保護。

- ログ出力先の取り扱い
  - ログの StreamHandler を stdout に固定（stderr ではない）。cron/Task Scheduler などでリダイレクトしやすいよう配慮。

### Fixed（修正）
- なし（初回リリースのため既知のバグ修正履歴はまだありません）。

### Known issues / Notes（既知の問題・注意）
- research/factor_research.py は一部実装が途中（ファイル末尾で切れている）です。必要なクエリや補助関数の完成が必要です。
- position_sizing と risk_adjustment のいくつかの計算は価格データが欠損する場合に保守的な挙動（スキップや警告）を採る設計になっています。プロダクション導入時は前日終値などのフォールバック価格導入を検討してください。
- ログディレクトリ作成やプロセス優先度設定は環境権限に依存します。権限不足時は警告を出してフォールバックする挙動です。

---

このリリースでは、運用に必要な起動スクリプト・設定管理・検証ツール・ログ/プロセスユーティリティ・ポートフォリオ構築ロジック・検証レポート出力といった基盤機能を一通り提供しています。今後はファクター計算の完成、ExecutionEngine や SystemMonitor の詳細実装・テスト、ドキュメント整備・サンプル設定ファイルの追加を予定しています。