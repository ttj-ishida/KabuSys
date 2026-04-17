KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

Unreleased
----------
(なし)

0.1.0 - 2026-04-17
-----------------
Added
- 初期リリース: パッケージバージョンを __version__ = "0.1.0" として公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用することで本番 DB と完全に分離。
    - エンジンはデーモンスレッドで起動し、data/execution.pid と stop フラグ（data/stop_requested.flag）により制御。
    - RiskManager / Reconciler / OrderManager / OrderRepository を組み立てる初期構成を実装（RiskConfig にデフォルト値を設定）。
    - duckdb 接続を受け取り分析用 DB と連携。
  - run_monitoring.py: システム監視ポーリングスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非数）はデフォルトにフォールバックし警告を出力。
    - 監視は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ検出で安全にループ終了。DB 接続（SQLite / DuckDB）は終了時に確実にクローズ。
- 設定関連
  - config.py: .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env/.env.local のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
    - Settings クラスを実装し、J-Quants / kabu / LINE / DB / 監視 / システム設定等のプロパティを提供。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を組み込み。
    - 環境変数保護（OS 環境変数を protected として上書き防止）をサポート。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 複数の設定項目定義と入力プロンプト、既存 .env の読み込み・マスク表示・保存機能を実装。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリチェック、config/*.yaml 存在チェック（PyYAML 未導入時は警告）など。
    - --strict オプションで警告をエラー扱いにして終了コード 1 を返す。
- ポートフォリオ建設ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。スコアが全て 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックにより候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的見積り、端数処理（残余キャッシュで lot 単位の補正）を実装。
- utils
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応。psutil を利用して nice / HIGH_PRIORITY_CLASS を設定。
    - アクセス権限不足や未対応 OS の場合は警告を出力して安全にスキップ。
    - set_cpu_affinity によりプロセスの CPU affinity を最初の N コアにピン留め可能（エラー時は警告）。
- 研究系 / 分析
  - research/factor_research.py: DuckDB を用いたファクター計算を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（データ不足時は None を返す）。
    - DuckDB 上で SQL ウィンドウ関数を用いた効率的な実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプション対応。
    - P95 計算、各種 SQL クエリ、N/A 表示整形を実装。
- パッケージ初期化
  - kabusys/__init__.py: エクスポートモジュール一覧とバージョン定義を追加。
  - kabusys/portfolio/__init__.py で主要関数を公開。

Changed
- .env の読み込み優先順位を明確化: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- validate_config の出力を情報 / 警告 / エラーで整理し、strict モードを導入。
- run_execution/run_monitoring でプロセス優先度を起動直後に設定するよう統一。

Fixed
- run_monitoring: MONITOR_POLL_INTERVAL に不正値（0/負数/非数）が設定された場合に ValueError を避けてデフォルトにフォールバックする処理を追加し堅牢化。
- 各起動スクリプトにおいて SQLite / DuckDB 接続を finally で確実にクローズするよう改善（リソースリーク防止）。
- .env パーサーのクォート内エスケープとインラインコメント処理を強化し、実運用での想定外文字列（スペースやエスケープ）に耐えるようにした。

Security
- 本リリースでは特にセキュリティ脆弱性の修正は含まれていませんが、.env ファイルの生成時に「.env を絶対に Git にコミットしない」旨の注意を明記。

Notes / TODO
- position_sizing.calc_position_sizes の価格欠損（price == 0）の場合のフォールバックロジックは将来的に改善予定（前日終値や取得原価を使用する等）。
- apply_sector_cap の unknown セクター扱い、単元株単位の銘柄別拡張（lot_size の銘柄別対応）等は将来の拡張候補。
- research/factor_research のさらなるファクタ実装、統合テストの追加が望ましい。

コマンド例
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証:      python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動:      python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

(この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして利用する際は、コミット履歴やリリース管理者による確認を推奨します。)