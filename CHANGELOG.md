# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
慣例に従い主要な追加・変更点を日本語でまとめています（コードベースから推測・要約）。

## [Unreleased]

### Added
- 監視用ポーリングプロセス起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60秒）。
  - 停止はプロジェクト直下 data/stop_requested.flag の存在で検知。
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して DB に接続。
  - sqlite3 / duckdb 接続を確立し、SystemMonitor.check_once() をポーリング実行。予期しない例外はログに出力して継続。

- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py
  - プロセス優先度を高に設定（set_process_priority("high")）。
  - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
  - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止は data/stop_requested.flag により検知し、エンジンスレッドへ停止要求を送る。

- 設定管理・自動 .env ロードを実装
  - src/kabusys/config.py
  - .env ファイル（.env, .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。OS 環境変数を保護する機構あり。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env の行パーサは export プレフィックス、クォート文字列内のバックスラッシュエスケープ、コメント処理などに対応。
  - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値 / ログ等）への型付きアクセサを備える。バリデーション（列挙値や閾値の妥当性チェック）を実施。

- 設定ウィザードを追加
  - src/kabusys/config_setup.py
  - 対話式で .env を作成・更新するウィザードを提供。既存 .env の読み込み、値のマスク表示（シークレット）等をサポート。
  - 書き込みテンプレートにデフォルト値や注意書きを含める。

- 設定検証 CLI を追加
  - src/kabusys/validate_config.py
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML が無ければ警告）、本番環境向けガードチェック等を実行。
  - --strict オプションで警告を失敗扱いにできる。

- ロギングセットアップユーティリティを提供
  - src/kabusys/utils/logging_setup.py
  - StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテーション、30日保持）をルートロガーへ設定。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - LOG_LEVEL / LOG_DIR の解決優先順を実装。

- プロセス優先度・CPU affinity ユーティリティを追加
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX（Linux, macOS, FreeBSD）双方に対応。psutil を使い nice 値や Windows 優先度クラスを設定。
  - set_process_priority(level)（high/normal/low）、set_cpu_affinity(cpu_count) を提供。権限不足等の失敗時は警告ログでフォールバック。

- ポートフォリオ構築モジュールを追加
  - src/kabusys/portfolio/*
  - portfolio_builder: 候補選定（スコアソート）、等金額配分・スコア加重配分を提供。スコア合計が0のとき等分配にフォールバック。
  - risk_adjustment: セクター集中上限適用（既存保有評価に基づく候補除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算。単元株丸め、1銘柄上限・総利用上限（aggregate cap）、コストバッファ考慮のスケーリング実装（残差に基づく追加配分ロジック含む）。

- Paper Trading 検証レポート生成スクリプトを追加
  - src/kabusys/tools/paper_verification_report.py
  - Paper Trading（SQLite）を参照して稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定を出力。
  - 各指標の閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）を定義。P95 計算、日付フィルタ対応、DB 存在チェックを実装。
  - コマンドライン引数 --from/--to/--db をサポート。

- 研究用ファクタ計算基盤を追加（部分実装）
  - src/kabusys/research/factor_research.py
  - モメンタム / MA / ATR / 流動性等のファクタ計算を意図した設計。DuckDB 接続を受け prices_daily および raw_financials テーブルを参照して計算する方針を採用。関数 calc_momentum 等の骨組みを実装（ファイル末尾で未完の可能性あり）。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - src/kabusys/portfolio/__init__.py、src/kabusys/tools/__init__.py を追加してモジュールエクスポートを整理。

### Changed
- なし（初期追加のため特記事項なし）

### Fixed
- MONITOR_POLL_INTERVAL のパースで不正値が与えられた場合にデフォルトへフォールバックし警告ログを出すように実装（run_monitoring 内の補助関数）。time.sleep に渡す不正値による ValueError を防止。

### Security
- 環境変数 (.env) の取り扱いにおいてシークレットはウィザードや出力でマスク表示。環境ファイルは絶対に Git にコミットしない旨の注記を .env 生成テンプレートに明示。

---

## [0.1.0] - 2026-04-19
初回リリース。上記の機能群（監視・実行起動スクリプト、設定管理とウィザード、設定検証 CLI、ロギング・プロセスユーティリティ、ポートフォリオ構築ロジック、Paper Trading レポート、研究用ファクタ基盤）を含む。

- 参照ファイル:
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_execution.py
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/portfolio/ (portfolio_builder, position_sizing, risk_adjustment)
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/research/factor_research.py
  - src/kabusys/__init__.py

注: 本 CHANGELOG は提供されたコードの内容に基づき推測して作成しています。実際のリリースノートとして利用する際は、差分履歴（コミットログ）や開発者の意図に基づいて追記・修正してください。