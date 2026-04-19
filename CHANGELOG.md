CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記載しています。  
慣例に従い Breaking Changes（互換性を壊す変更）がある場合は明示します。

[Unreleased]
------------

- （現時点の差分は特にありません。新機能・修正があればここに追記してください。）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: バージョン情報を __version__ = "0.1.0" として公開。
- 起動/運用用スクリプトを追加
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定。停止制御はプロジェクト直下の data/stop_requested.flag による（同ファイルの存在検出でループ終了）。Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBroker を利用（本番 DB と完全分離）。プロセス優先度の設定、STOP フラグ / PID ファイル処理、デーモンスレッドによる実行管理を実装。
- 設定関連
  - config.py: Settings クラスを実装。環境変数の自動読み込み（.env, .env.local）をプロジェクトルート（.git または pyproject.toml）から行う仕組みを導入。export 形式やクォート、インラインコメントを適切にパースする堅牢な .env パーサ実装を追加。PAPER_FILL_MODE のバリデーションや paper_sqlite_path 等のプロパティを提供。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を実装（.env テンプレートの書き出し機能含む）。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在・パース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（score 降順、signal_rank によるタイブレーク）、等金額配分 / スコア加重配分（スコア全部 0 の場合は等金額フォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケールダウンと残差処理（fractional remainder に基づく追加配分）、cost_buffer による保守的見積りなどを実装。
  - portfolio/__init__.py: 主要関数を公開するパッケージ入口を用意。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout に StreamHandler を出力（cron/Task Scheduler の取り扱いを考慮）、日次ローテーションの TimedRotatingFileHandler を設定（デフォルト logs/ ディレクトリ、30 日分保持）。既存ハンドラのクリーンアップや、ログディレクトリ作成失敗時のフォールバック（ファイルロギングを無効化してコンソールのみ）を実装。
  - utils/process_priority.py: psutil を利用したクロスプラットフォームのプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS と POSIX の nice 値の差分吸収）と CPU affinity 設定関数を実装。権限不足時は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して CLI 出力。日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。基準値（稼働率 99%、fill 90%、send 95%、P95 200 ms）による PASS/FAIL 判定を実装。
- リサーチ（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。Momentum/Value/Volatility/Liquidity の設計方針と定数を定義し、calc_momentum の実装開始（DuckDB 接続を受け取る設計）。

Changed / Design notes
- DB 初期化の冪等性を確保
  - monitoring.monitoring_db.init_monitoring_db を用いて起動時に監視用テーブルの存在を保証（何度でも安全に呼べる）。
- 実行時の安全設計
  - stop flag / kill flag, pid ファイルなど OS 上での停止・監視運用を想定した設計を導入。実行スクリプトはいずれも停止フラグをチェックして安全に終了する。
- ログ出力の取り扱い
  - stdout を採用（stderr ではない）ことで、ログの集約・リダイレクト運用を容易にした。
- .env 自動読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込み。OS 環境変数は protected として .env による上書きを防止。
- 設定のバリデーション強化
  - PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等の値チェックを厳密化し、不正値での実行を防止。
- ポートフォリオ / 取引ロジック
  - 各段階（選定・重み付け・ポジションサイズ算出・セクター制限）を独立した純粋関数として実装し、テスト容易性と再利用性を確保。

Fixed
- ランタイムの堅牢性向上
  - run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や不正な文字列の場合にデフォルトにフォールバック（ValueError を避ける）。
  - logging_setup で既存ハンドラを安全に flush/close してから削除するようにして二重登録を防止。
  - run_execution で停止フラグが既に立っている場合は起動をスキップして即時終了する安全挙動を実装。

Security
- 環境変数ファイル (.env) の注意喚起
  - config_setup にて .env の生成時に「.env を絶対に Git にコミットしないこと」をドキュメント化。

Notes / Limitations
- research/factor_research.calc_momentum はモジュール骨格と定数を含み実装が開始されていますが、ファイル末尾で切れており完全実装ではありません。DuckDB のテーブル構造（prices_daily 等）に依存するため、実運用前にテストと追加実装が必要です。
- position_sizing の lot_size は現状全銘柄共通で固定（将来的に銘柄別単元対応を予定）。
- process_priority や CPU affinity の適用は権限やプラットフォームによってはスキップされる可能性があります（警告ログのみで継続します）。

参考: 主要ファイル一覧（本リリースで追加/更新された主なモジュール）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/portfolio/*.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

以上。