CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース: KabuSys パッケージの基本機能を追加。
  - パッケージ情報 (バージョン 0.1.0) を定義（src/kabusys/__init__.py）。
- 起動スクリプト / デーモン類を追加。
  - 監視ループ起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag による優雅なシャットダウン。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用。
    - プロセス優先度を高く設定してから起動。
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成（実アカウント/モック選択）。
    - エンジンはスレッドで実行、停止フラグ検知で stop() を呼び出して停止。
    - PID ファイル管理（data/execution.pid）をサポート。
- 環境変数・設定管理（src/kabusys/config.py）
  - Settings クラスでアプリケーション設定を集中管理。
  - .env 自動読み込み:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込み。
    - OS 環境変数は保護され、.env.local は上書き可能。
  - 高度な .env パーサー（引用符、export プレフィックス、インラインコメント扱い等に対応）。
  - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
  - 監視・しきい値設定（CPU/MEM/DISK）や kill/ PID ファイルパス等をプロパティとして提供。
- 設定関連 CLI
  - 対話式 .env 作成/更新ウィザード（src/kabusys/config_setup.py）
    - 現在値表示、シークレットマスク、デフォルト値、選択肢対応。
    - .env の書き出し機能を提供（.env ファイルに保存するテンプレート記述）。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパースチェック（PyYAML があればパースまで）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギングとプロセス管理ユーティリティ（src/kabusys/utils）
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - stdout ストリームハンドラ（標準出力）と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 解決ルール、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority で Windows/POSIX を吸収する実装（安全なフォールバックと警告）。
    - set_cpu_affinity で最初の N コアに固定する機能（権限エラーは警告で無視）。
- ポートフォリオ構築（純関数群、DB 不要）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークロジック。
    - calc_equal_weights / calc_score_weights（スコア全ゼロ時は等配分にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補から除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に基づく乗数（未知のレジームは警告のうえ 1.0 にフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）対応、lot_size（単元）丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮した安全な配分ロジック。
- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - DuckDB を用いたファクター計算モジュールの追加（Momentum / Value / Volatility / Liquidity を計画）。（実装の一部が含まれる）
- Paper Trading 検証・レポートツール（src/kabusys/tools/paper_verification_report.py）
  - SQLite の paper_trading DB から稼働率、注文成立率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計しレポート出力。
  - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定。
  - CLI オプション: --from / --to / --db、環境変数 PAPER_TRADING_SQLITE_PATH より DB パス取得。
- DB/分析バックエンド統合
  - DuckDB 接続を各処理（研究・実行エンジン・ログ保管等）で使用する前提を導入（duckdb 接続生成コードが各スクリプトに追加）。
  - 監視テーブルの初期化ユーティリティ init_monitoring_db を各起動処理で呼び出し、冪等に監視テーブル存在を保証。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / 実装上の注記
- .env の自動読み込みはテスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により抑止可能。
- process_priority の設定は権限不足や未対応 OS の場合は警告を出してスキップする設計。
- 一部モジュール（例えば research.calc_momentum）は大量データを扱う前提で DuckDB を使用する設計になっており、DuckDB のインストールが必要。
- Paper Trading と本番 DB は明確に分離されるよう配慮されている（PAPER_TRADING_SQLITE_PATH / Settings.is_paper 等）。

------------

今後の改善候補（実装から推測）
- ファイル作成・DB マイグレーションの詳細なエラーハンドリング強化。
- portfolio の lot_size を銘柄別に扱うための拡張（stocks マスタへの lot_size 保存）。
- research モジュールの完全実装とユニットテストの追加。
- 実行エンジン / 監視のシステムテストおよびオーケストレーション（systemd / supervisor 等）サンプル。