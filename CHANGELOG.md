CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

unreleased
----------

0.1.0 - 2026-04-19
------------------

Added
- 全体
  - 初期公開リリース。パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
- 設定関連
  - 環境変数/.env 管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）。
    - .env の自動読み込み（.env, .env.local）、OS 環境変数を保護する仕組み。
    - 複数の設定プロパティを公開（DB パス、API トークン、Paper Trading 設定、閾値、ログレベル等）。
    - 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を作成/更新可能。秘密項目はマスク表示。
  - 設定検証ツール CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・パス・config/*.yaml の存在・YAML パースなどをチェック。
    - --strict オプションで警告をエラー扱いにできる。
- 実行/監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）に切り替え、Mock ブローカー経由で完全分離して実行。
    - プロセス優先度を高設定（set_process_priority を利用）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行用 pid ファイル出力処理をサポート。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループを終了。
- ポートフォリオ構築（純粋関数）
  - 銘柄選定・重み計算モジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補抽出（score 降順・同点時の tie-break）および等金額／スコア加重配分を提供。
  - セクター集中制限・レジーム乗数モジュールを追加（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター上限適用（sell コードの除外、unknown セクターの扱いなど）と、market regime に応じた乗数計算（bull/neutral/bear）を提供。
  - 発注株数決定・投下制約モジュールを追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の各割当方式をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に対するスケーリング）、cost_buffer による保守的見積りを実装。
  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。
- 実行ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を明確化。ログディレクトリ作成失敗時にはファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/その他を抽象化して nice/priority を設定。psutil を利用し、権限や未実装関数に対しては警告ログでフォールバック。
- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB パス引数/環境変数の優先度をサポート。
- 研究用ファクター計算（骨格）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム/MA/ATR/流動性等の計算方針と定数を定義。DuckDB 接続を受けて計算する設計（実装は継続）。

Changed
- N/A（初回リリースのため変更履歴はありません）。

Fixed
- 設定読み込みや運用面での堅牢化を多数実装
  - .env のパースでクォート内のエスケープやインラインコメント、export プレフィックスに対応（src/kabusys/config.py）。
  - 自動 .env ロード時にプロジェクトルートが見つからない場合は安全にスキップする挙動を追加。
  - ログディレクトリ作成・ファイルハンドラ生成の失敗時に stdout のみで継続するフォールバックを追加（src/kabusys/utils/logging_setup.py）。
  - process priority / cpu affinity 設定で権限不足や未サポート OS の場合に例外を握りつぶしログ出力でスキップする安全処理を追加（src/kabusys/utils/process_priority.py）。
  - run_execution/run_monitoring で DB 接続を必ずクローズする finally ブロックを保証。

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / TODO
- factor_research の実装は途中（コード終端が未完）。引き続きファクター計算関数の完成が必要です。
- position_sizing の price フォールバック（前日終値や取得原価等）について TODO コメントあり。
- 将来的に単元株数を銘柄別に扱うための設計拡張が想定されている（lot_size の銘柄別化）。
- 一部の外部依存（psutil, duckdb, PyYAML 等）により環境構築が必要。validate_config と config_setup を使い初期設定を行ってください。

Contributing
- バグ報告・改善提案は Issue を立ててください。開発者向けには validate_config と config_setup を先に実行して動作環境を整えてください。