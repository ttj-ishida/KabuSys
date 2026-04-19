CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
慣習: 変更はカテゴリ別（Added / Changed / Fixed / ...）で記載しています。

[Unreleased]
------------

- なし（次回リリースに向けた未確定の変更はここに記載されます）。

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリースを公開。
- 実行系・監視系の起動スクリプトを追加:
  - run_execution: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV に応じて Paper Trading 用 DB を分離し、MockBrokerClient を利用する仕組みを想定。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ (data/stop_requested.flag) による安全停止に対応。
- 設定管理:
  - Settings クラス（config.py）でアプリケーション設定を集中管理（環境変数の取得、バリデーション、デフォルト値の提供）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出を行い .env / .env.local を適切な優先度で読み込む。OS 環境変数は保護）。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID / kill flag 等の設定項目を追加。
- 対話式設定ウィザードを追加:
  - config_setup.py: .env を対話的に生成・更新するウィザードを提供（既存値の読み込み・マスク表示・保存）。
- 設定検証ツールを追加:
  - validate_config.py: .env と config/*.yaml の存在・簡易チェックを行う CLI。必須環境変数の未設定検出、KABUSYS_ENV の妥当性チェック、PyYAML が無い場合のフォールバック等を実装。--strict オプションで警告を失敗扱いにできる。
- ログ基盤を整備:
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力をルートロガーに設定。ログディレクトリの自動作成、作成失敗時のファイルハンドラ無効化フォールバック、LOG_LEVEL / LOG_DIR の解決順を実装。
- プロセス優先度・CPU 固定ユーティリティ:
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度を設定。CPU affinity を最初の N コアに固定する関数も提供。アクセス権限や未対応環境での安全なフォールバックを実装。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: シグナル候補選定と等金額・スコア加重配分（calc_equal_weights / calc_score_weights / select_candidates）。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ考慮を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市況レジームに応じた資金乗数（calc_regime_multiplier）。未知レジームでのフォールバックと警告出力を実装。
- 解析・検証ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB パスの柔軟な解決ロジックを実装。
- DuckDB と SQLite の併用を想定:
  - 複数スクリプトで duckdb/SQLite 接続を確立する実装を追加（duckdb_path / sqlite_path / paper_sqlite_path を Settings で管理）。
- 監視用 DB 初期化の冪等化:
  - init_monitoring_db 呼び出しにより監視テーブル生成を保証（既存 DB に対しても安全に呼べる設計）。
- パッケージ情報:
  - __init__.py にバージョン 0.1.0 を設定。

Changed
- .env 読み込みの挙動:
  - .env 解析を強化（export プレフィックス対応、引用符付き値のエスケープ処理、インラインコメントの扱いの改善）。
  - 読み込み優先度を OS 環境変数 > .env.local > .env として明確化。OS 環境変数を保護するため protected set を導入。
- ログハンドラ設定の挙動を整理:
  - 既存ハンドラがある場合は一度 flush/close してから削除し、二重出力を防止。
  - stdout を使う理由やファイルハンドラのフォールバック動作を明記。
- run_execution の DB 分離ポリシー:
  - paper_trading 環境では paper_sqlite_path（data/paper_trading.db がデフォルト）を使用し、本番 DB と完全分離する挙動を明確化。
- ポジションサイズ計算:
  - risk_based と equal/score 方式の両方をサポートし、手数料・スリッページを見積る cost_buffer を導入して aggregate cap 計算に反映。
- process_priority のプラットフォーム差分抽象化:
  - Windows の優先度定数は getattr で安全に取得し、未サポート OS では警告ログを出してスキップ。

Fixed
- 環境変数パースの不整合対応:
  - _parse_env_line の改良により、引用符付き値のエスケープ文字処理やコメントの誤判定を修正。不正な行は無視するように安定化。
- ログディレクトリ作成失敗時の致命的障害を回避:
  - 例外発生時にファイルハンドラ作成をスキップしてコンソール出力のみで継続するように修正。
- プロセス優先度設定時の例外耐性を向上:
  - AccessDenied 等の例外発生時に警告ログを出し処理を継続するようにし、起動が止まらないように改善。
- run_execution/run_monitoring の停止処理強化:
  - data/stop_requested.flag による安全停止検出を追加。実行中スレッドの停止時に Engine.stop() を呼ぶなど安全に終了する挙動を実装。

Security
- .env ファイルに関する注意書きを config_setup の出力に追加（.env を絶対に Git にコミットしない旨の明記）。

Notes / Implementation details
- Paper Trading と Live の DB は明確に分離される設計（paper_trading 環境は paper_sqlite_path を使用）。
- Monitoring は本番 sqlite_path を使用することで一貫した監視データの集約を意図（run_monitoring の実装注記）。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックし警告出力する（安全側に寄せた実装）。
- Position sizing の aggregate cap は lot_size（現状 100）単位で調整される。将来的な拡張（銘柄別 lot_size）は TODO 記載。
- tools/paper_verification_report の閾値（稼働率・成功率など）はソースコード上の定数で定義されており、必要に応じて調整可能。

今後の予定（例示）
- research/factor_research.py の続き実装（ファクター計算ロジックの完成）。
- テストカバレッジ拡充（ユニットテスト・統合テストの追加）。
- docs/ に設計ドキュメント（PortfolioConstruction.md 等）の同梱と README の拡充。
- 銘柄別 lot_size 対応や、より高度な手数料モデルの導入。

--- 

この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜修正してください。