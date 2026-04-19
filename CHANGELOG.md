CHANGELOG
=========

すべての注目すべき変更を記録します。Keep a Changelog 準拠。

v0.1.0 - 2026-04-19
-------------------

注: このリリースはコードベースから推測して作成した初回のリリースノートです。実装の詳細は各モジュールのドキュメントやソースを参照してください。

Added（追加）
- 基本パッケージ情報
  - パッケージバージョンを設定: __version__ = "0.1.0"。

- 実行用スクリプト / サービス
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全に終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に完全に分離して記録。
    - 停止フラグと PID ファイルの管理を実装。スレッドで engine.run_session を起動・監視・停止。

- 設定 / ユーティリティ
  - config.py
    - Settings クラスを導入し、環境変数から設定を取得する統合的インターフェースを提供。
    - .env 自動読み込み（プロジェクトルート検出 .git / pyproject.toml を基準）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - PAPER_FILL_MODE に対する入力検証（有効値: instant/partial/never/reject）。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）や各種閾値（CPU/MEM/DISK）など多数の設定プロパティを提供。
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援する CLI を追加。
    - 機密項目はマスク表示、既存値の再利用、.env 保存時のテンプレート化と注意書きを提供（.env を Git にコミットしない旨）。
  - validate_config.py
    - 起動前のチェック用 CLI を追加（必須環境変数・KABUSYS_ENV・ログレベル・DBパス・config/*.yaml の存在・本番環境ガード等を検査）。
    - --strict フラグで警告も失敗扱いにできる。

- 分析 / レポート
  - tools/paper_verification_report.py
    - ペーパートレーディング検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照し、稼働率、注文成功率・送信率、API レイテンシ（平均/最大/P95）などを算出・判定（PASS/FAIL）。
    - P95 計算ユーティリティを実装。
    - コマンドライン引数で期間 (--from / --to)・DB パス (--db) を指定可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア重み（calc_score_weights）を追加。
    - スコア全てが 0 の場合に等分配へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）を追加。既存保有のセクター暴露を算出し上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ）を追加。未知レジームは警告のうえ 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - ポジションサイズ算出 calc_position_sizes を追加。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株数 (lot_size) で丸め、1銘柄上限・全体投下上限（aggregate cap）を考慮。コストバッファ（手数料・スリッページ見積り）を加味したスケーリングを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30世代保持）をルートロガーに設定。
    - 既存ハンドラのクリア・flush/close、ログディレクトリ作成失敗時はファイル出力をスキップする堅牢性を実装。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を追加。
    - Windows/Linux/macOS に対応するラッパー（psutil 利用）。権限不足時は警告を出してスキップ。

- リサーチ
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum/Value/Volatility/Liquidity）を計算するためのモジュールを追加（設計方針と定数、calc_momentum 等の骨組みを実装）。※ファイル末尾は途中で切れており実装の続きを含意。

Changed（変更）
- データベース周り
  - Monitoring 用の DB 初期化処理を冪等に（init_monitoring_db を呼んで存在保証）。
  - run_execution は paper_trading 環境のとき専用 SQLite を使用することで本番 DB と完全分離。

- 環境変数の読み込み優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む（.env.local は上書き、ただし OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を導入。

- .env パーサー強化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での違い）などを実装し堅牢性を向上。

- ロギング挙動
  - setup_logging は既にハンドラがある場合は一旦クリアしてから再設定するように変更（重複出力回避）。

Fixed（修正 / 改善）
- エラー耐性の向上
  - run_monitoring のチェックループ内で monitor.check_once() の例外を補足し、ログに記録して次ポーリングへ継続。
  - run_execution の起動前に停止フラグが立っている場合は即座に起動を中止する保護を追加。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、標準出力のみで継続するようにして失敗時の起動継続性を確保。

- validate_config
  - PyYAML が未インストールの場合は YAML 検証をスキップし警告を出す。config/*.yaml の存在チェックとパースエラー検出を実装。
  - 本番環境向けのガード（LINE トークンや KILL_FLAG_CLEAR_ON_START の危険設定を警告）を追加。

- position sizing のスケーリング
  - aggregate cap 適用時の丸め・残差処理（lot_size 単位での再配分）を実装し、利用可能現金を超えないよう慎重に配分するアルゴリズムを導入。

Security（セキュリティ）
- .env の取り扱いに関する注意表示を config_setup の生成ファイルに追加（.env を絶対に Git にコミットしないことを明示）。
- 機密環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings で必須とし、未設定時に起動前にエラーを発生させるチェックを提供。

Known issues / Notes（既知の問題・備考）
- research/factor_research.py は骨組みが実装されているがファイル末尾が途中で終わっており、いくつかの関数や処理が未完の可能性がある（実装の続きを要確認）。
- 一部の挙動（例: price が欠損したときのセクターエクスポージャー計算）は TODO コメントで将来的な改善が示されている。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存で動作しない場合がある。その場合は警告ログを出してスキップする。

参考（実装上の幾つかのデフォルト）
- MONITOR_POLL_INTERVAL のデフォルト: 60 秒（不正値時はデフォルトへフォールバック）。
- ログローテーション保持数: 30 日分。
- PAPER_FILL_MODE の有効値: instant / partial / never / reject（無効値はエラー）。
- Portfolio: 推奨ポジション数は 5〜15。デフォルト max_positions は 10。単元株 lot_size のデフォルトは 100。

今後の予定（提案）
- research モジュールの完全実装（ファクター計算の SQL とスコア生成）。
- 銘柄ごとの lot_size 等を持つマスタ導入による position_sizing の拡張。
- logging におけるログ転送・集約（外部ログサービス連携）や、monitoring のメトリクスエクスポート対応。

--- 

以上。必要であれば各項目をバージョン・コミット単位に分解した詳細な CHANGELOG（例: Unreleased 列挙、コミット参照、影響範囲）を作成します。どのレベルの詳細が欲しいか指定してください。