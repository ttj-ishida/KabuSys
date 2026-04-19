Keep a Changelog — 変更履歴
========================

すべての注目すべき変更をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

バージョン
----------

0.1.0 - 2026-04-19
~~~~~~~~~~~~~~~~~~

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行エントリスクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading のときは専用の paper trading SQLite (data/paper_trading.db) を使用し、本番 DB と分離して動作。
      - ブローカークライアント生成は BrokerClientFactory を通して行う。
      - ExecutionEngine は別スレッドで実行され、data/execution.pid に PID を書き込む想定（pid_file 経由）。
      - 停止は data/stop_requested.flag により検出して安全に停止する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを記録。
      - 停止フラグ（data/stop_requested.flag）でループを終了。
      - check_once() 呼び出し中の例外を捕まえてログに出力し、次ポーリングに復帰する耐障害性を持つ。
  - 設定・環境管理
    - config.py: .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
      - .env / .env.local の読み込みルール（OS 環境変数を保護する protected 機能）。
      - export プレフィックス、クォート対応、インラインコメントの取り扱いなどをサポートする独自パーサを実装。
      - 多数の設定プロパティ（DB パス、API トークン、閾値、環境判定メソッド等）を提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
      - 多数の設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL、Kill Switch 設定 等）を対話的に設定して .env を生成。
  - 設定検証
    - validate_config.py: 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース（PyYAML がインストールされている場合）などを検査。
      - --strict オプションで警告も FAIL 扱いに可能。
  - ロギング・ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
      - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定。
  - プロセス優先度 / CPU affinity
    - utils/process_priority.py:
      - set_process_priority(level): Windows / POSIX を吸収して優先度を設定。許可がない場合は警告を出してスキップ。
      - set_cpu_affinity(cpu_count): 指定コア数に固定するユーティリティを提供（アクセス権等がない場合は警告でスキップ）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルのソートと上位選出。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全0 の場合は等分配にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: 同一セクター上限（max_sector_pct）に基づく候補除外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告と 1.0 フォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。
      - 単元株（lot_size）で丸め、個別上限・aggregate cap のスケールダウンロジック、cost_buffer による保守的見積り、残差処理で lot 単位の追加配分などを実装。
      - 将来的な拡張点（銘柄別 lot_size マッピングなど）を TODO コメントで明示。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py:
      - ペーパートレード用 SQLite を集計し、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等のレポートを出力。
      - CLI で期間（--from / --to）と DB パス（--db）を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH にも対応。
      - レポートは閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL を判定。
  - Research（計算モジュール）
    - research/factor_research.py: DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算するための下地を追加（モジュール設計・定数・calc_momentum の導入）。DuckDB の prices_daily/raw_financials を参照する設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 秘匿情報（API トークン / パスワード等）は .env に格納する前提。config_setup では .env を絶対に Git にコミットしないよう注意喚起を追記。

Notes / Known limitations
- run_monitoring は監視用 DB として常に settings.sqlite_path を使う設計になっており、KABUSYS_ENV による切り替えは行わない（監視データは本番 DB に記録される前提）。
- .env パーサは多くのケース（quoted values, export prefix, inline comments の特別扱い）に対応するが、極端な edge case のパース保証は行わない。
- process_priority / cpu_affinity は権限やプラットフォーム依存のため、失敗時は警告を出して処理を継続する設計。
- position_sizing 等の金融ロジックには多数の設計上の仮定（lot_size 共通、価格フォールバック未実装など）があり、運用前のレビューと実データでの検証が必要。
- research.calc_momentum の実装はファイル末尾で途中（start_da で切れている箇所）が存在するため、完全実装は今後の作業が必要。

開発者向け補足
- パッケージバージョンは src/kabusys/__init__.py の __version__= "0.1.0" に設定。
- 自動テストや CI のセットアップは別途必要。validate_config.py や config_setup.py, logging_setup の挙動はユニットテストの対象に適する。

ライセンス・貢献
- 本 CHANGELOG はコードベースから推定して作成しています。実際のリリースノートは運用ルールに従って更新してください。