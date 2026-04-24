CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

0.1.0 - 2026-04-24
------------------

Added
- 基本アプリケーションの初期リリースを追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト / デーモン制御
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルの存在で検知。
    - 監視は環境変数 `KABUSYS_ENV` に関わらず本番用の sqlite_path を使用して監視 DB を初期化。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続を併用。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを抽象化（モック/実装切替可能）。
    - ExecutionEngine をバックグラウンドスレッドで実行し、stop flag を監視して終了。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。

- 設定管理
  - config.py: 環境変数読み込み・管理を追加。
    - .env / .env.local の自動ロード（優先順位: OS 環境 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサは export プレフィックス、クォート文字列、エスケープ、インラインコメントを考慮して堅牢に実装。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE 通知、DB パス、監視閾値、環境判定など）。
    - `PAPER_FILL_MODE` の検証（"instant" | "partial" | "never" | "reject"）。
    - `is_live` / `is_paper` / `is_dev` の判定ヘルパー。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 標準項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL 等）を対話的に収集して .env を生成。
    - 既存 .env の読み込みと既存値利用、秘匿値のマスク表示に対応。
    - 生成時に .env ファイルを上書き保存する機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検査。
    - `--strict` オプションで警告も失敗として扱う。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（標準出力 stdout）と TimedRotatingFileHandler（毎日ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - 既存ハンドラのクリーンアップを実施し二重登録を防止。
  - utils/process_priority.py:
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する関数を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限・未実装 API の例外は警告で継続）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルの選別 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等配分 calc_equal_weights と スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有と当日売却予定を考慮、"unknown" セクターは制限対象外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - 株数決定ロジック calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size 単位）、per-stock 上限、aggregate cap（available_cash に収まるようスケールダウン）や端数処理の再配分ロジックを実装。
    - cost_buffer による保守的コスト見積り対応。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム等のファクター計算基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - 1M/3M/6M リターンや MA200 乖離、ATR、出来高指標などの定義と定数を追加（実装は継続中）。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、P95 レイテンシ等を集計して検証レポートを標準出力に生成する CLI を追加。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義して PASS/FAIL 判定を出力。
    - 日付範囲フィルタ (--from, --to) と DB パス指定 (--db) に対応。

Changed
- n/a（初回リリース）

Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判定などを適切に処理することで .env の解析の正確性を向上。
- MONITOR_POLL_INTERVAL の値検証を追加
  - 0 以下や整数変換失敗時は警告を出してデフォルト（60 秒）にフォールバック。

Security
- .env に機密情報が含まれることを明示し、config_setup で生成された .env を絶対に Git にコミットしないよう注記。

Known issues / Notes
- research/factor_research.py の一部実装が途中で切れている（calc_momentum の実装が継続中）。本リリースではファクター計算フレームワークの骨組みを提供しているが、完全実装は今後のリリースで追加予定。
- process_priority や CPU affinity の操作は OS 権限に依存するため、権限不足時は警告を出してスキップする挙動。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化するが、その際は stderr に警告を出力する点に留意。

-----

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴ではありません。必要に応じて日付・詳細をプロジェクト実際のリリースノートに合わせて調整してください。