CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリースを追加。
- 基本情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 設定・環境変数周り
  - .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 高度な .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを実装（環境変数の取得・検証、デフォルト値の提供、env/log_level/paper_fill_mode 等のバリデーションを含む）。（src/kabusys/config.py）
- 対話式環境設定ウィザード
  - python -m kabusys.config_setup で .env を対話的に作成・更新する CLI を追加。既存値の読み取り、シークレットのマスク表示、保存テンプレートを提供。（src/kabusys/config_setup.py）
- 設定検証ツール
  - python -m kabusys.validate_config による起動前チェックを追加。必須環境変数・KABUSYS_ENV の妥当性・YAML ファイルの存在とパース（PyYAML がある場合）・DB パス等を検査。--strict フラグで警告も失敗扱いに。（src/kabusys/validate_config.py）
- 実行エンジン起動スクリプト
  - ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、paper_trading 時は専用 SQLite を使用し本番 DB と分離、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド実行・停止フラグ対応、PID ファイル取り扱いを実装。（src/kabusys/run_execution.py）
- 監視ループ起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様、停止フラグ検知でループ終了。（src/kabusys/run_monitoring.py）
- プロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity を実装。Windows / POSIX の差分を吸収し psutil を利用して優先度・CPU affinity を設定（権限不足時は警告でスキップ）。（src/kabusys/utils/process_priority.py）
- ポートフォリオ構築
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。スコア全て 0 の場合は等分配へフォールバック。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限適用（apply_sector_cap）。既存保有のセクター別エクスポージャー算出と候補除外の実装、unknown セクターは上限適用外。レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の各配分方式、単元株（lot_size）丸め、max_position_pct/ max_utilization 等の上限、aggregate cap によるスケールダウンと端数処理（残差に基づく追加配分）、cost_buffer を用いた保守的見積りを実装。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポート整理。（src/kabusys/portfolio/__init__.py）
- リサーチ / ファクター計算
  - DuckDB 接続を用いたファクター計算の骨組みを追加。モメンタム（1M/3M/6M リターン、MA200 乖離）とボラティリティ（ATR, 平均売買代金, 出来高比率）算出関数を実装（prices_daily テーブル参照）。出力は (date, code) をキーとする dict のリスト形式。空データ時の None ハンドリングあり。（src/kabusys/research/factor_research.py）
- Paper Trading 検証ツール
  - paper_trading の履歴 DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を返すしきい値を定義。P95 計算・日付フィルタ・データ欠損時のフォールバックをサポート。（src/kabusys/tools/paper_verification_report.py）
- 監視 DB 初期化ユーティリティなど基盤モジュール（monitoring/system_monitor など参照 import が存在）。（複数ファイルからの初期化呼び出し）

Changed
- （初期リリースのため変更履歴はありません）

Fixed
- （初期リリースのため修正履歴はありません）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意
- .env の取り扱いにおいて、.env は決してリポジトリにコミットしないことを README 等で強調する設計（config_setup の出力テンプレートにも注意書きを含む）。
- Settings.paper_fill_mode の値検証や Settings.env / log_level の厳格チェックにより、起動時の誤設定を早期に検出する方針。
- run_monitoring はドキュメントコメントどおり監視用 DB に対して本番 sqlite_path を使用する（環境に依存しない挙動）。
- calc_position_sizes 等のアルゴリズムは現状単元株が全銘柄共通（lot_size）を前提としている。将来的な拡張（銘柄別 lot_map）は TODO コメントあり。
- psutil による優先度設定 / affinity の実行は権限不足や OS 未対応時に安全にフォールバックするよう実装。

今後の改善候補（非網羅）
- positions ごとの lot_size を銘柄別に持たせる拡張。
- price の欠損時のフォールバック価格算出（前日終値や取得原価など）。
- factor_research における追加ファクター（Value, Liquidity 等）の実装完了とテスト整備。
- テストカバレッジの追加（特に資金配分・スケール処理の境界条件）。
- モニタリング / 実行エンジンのより詳細な observability（メトリクス、Structured logging 等）。

-----