# Changelog

すべての重要な変更を追跡します。フォーマットは "Keep a Changelog" に準拠しています。

全般的な注意事項:
- 環境変数は .env/.env.local または OS 環境から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- ログやデータベース等のデフォルトパスはプロジェクトルート配下の data/ や logs/ を使用します（必要に応じて環境変数で上書き可能）。

## [0.1.0] - 2026-04-22

### Added
- 初回リリース: KabuSys パッケージ（バージョン 0.1.0）。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックし警告を出す。
    - 監視は環境にかかわらず production の sqlite_path を使用（monitoring 用 DB は本番 DB を参照）。
    - 停止制御にプロジェクトルート/data/stop_requested.flag を使用。
    - DuckDB へ接続（duckdb_path）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）に対応。
    - Thread を使ったデーモン実行および安全な停止処理を実装。
- 設定管理:
  - config.py
    - Settings クラスを導入。環境変数経由で各種設定を取得（J-Quants、kabuAPI、LINE、データベースパス、監視閾値、KABUSYS_ENV 等）。
    - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を検出し、優先順 OS env > .env.local > .env で読み込む（デフォルト）。既存 OS 環境は保護される。
    - .env パース機能はシングル/ダブルクォート、エスケープ、export KEY=val 形式、コメント処理などに対応。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）など入力検証を実装。
  - config_setup.py
    - `.env` を対話式に作成・更新するウィザードを追加。必須項目・デフォルト・選択肢を提示し、シークレットはマスク表示。生成された .env はコミットしないよう注意喚起。
  - validate_config.py
    - 起動前に .env および config/*.yaml（存在確認・YAML パース）を検証する CLI を追加。
    - REQUIRED/OPTIONAL 環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、PyYAML 未インストール時のスキップ、KABUSYS_ENV=live 時の追加ガード（LINE 通知や Kill Switch）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py
    - すべての起動スクリプトから統一的に呼べるロギング設定を提供。
    - stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler, 30 日保持）によるファイル出力をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR / 引数による優先度解決と、ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（"high"/"normal"/"low"）を提供。Windows と POSIX（Linux/Mac/FreeBSD）に対応。アクセス拒否等は警告を出してスキップ。
    - set_cpu_affinity を提供し、任意のコア数にピンニング可能（存在しない場合や権限エラーは警告）。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（タイブレーク: score 降順、同点は signal_rank 昇順）。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有セクター比率が上限を超える場合に、そのセクターの新規候補を除外（unknown セクターは除外対象外）。売却予定銘柄はエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。Bear 時は 0.3（大幅縮小）等のデフォルトマップを採用。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じて発注株数を決定（"risk_based", "equal", "score" をサポート）。
      - risk_based: 損切り幅 stop_loss_pct と許容リスク率 risk_pct に基づく株数算出。
      - equal/score: 重みと max_utilization に基づく配分、lot_size（例: 100 単元）で丸め。
      - 単元丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ）を考慮した安全なスケーリングを実装。残余キャッシュを用いた端数処理（fractional remainder）による追加配分ロジックを搭載。
- 研究/ファクター計算:
  - research/factor_research.py（未完の箇所あり、モメンタム/MA/ATR/流動性等の計算方針を実装予定）
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクター計算を行う設計。戻り値は (date, code) をキーとする dict のリストを想定。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - CLI による期間指定（--from/--to）や DB パス指定（--db）。デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ。P95 計算、各種 NULL/データ不足のハンドリングを実装。
    - デフォルト合格基準（しきい値）を定義: 稼働率 >= 99.0% 等（ソース内定数で可変）。
- パッケージ初期化:
  - __init__.py によるパッケージメタ情報（__version__ = "0.1.0"）とエクスポート宣言。

### Changed
- なし（初期リリースのため変更履歴はありません）。

### Fixed
- なし（初期リリースのため修正はありません）。

### Security
- .env ファイルは生成ウィザードで明示的に「.env を絶対に Git にコミットしないこと」を記載。機密情報（API トークン等）はウィザードでマスクして表示。

### Notes / Implementation details（重要な挙動・運用注意）
- run_monitoring は Monitoring 用の DB として Settings.sqlite_path を参照し、KABUSYS_ENV にかかわらず production 監視 DB を使用する点に注意してください（監視データは環境に関わらず同一 DB を想定）。
- run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と完全分離するよう設計されています。ペーパートレード/本番を明確に分けたい場合は KABUSYS_ENV を適切に設定してください。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後も安全に動作するよう設計）。
- process_priority の変更は権限のない環境で失敗する可能性があり、その場合は警告を出してスキップします（実行環境の権限に依存します）。
- research/factor_research.py は設計・一部実装が含まれますが、ファイル末尾に未完の箇所が存在します（今後の実装で完成予定）。

### Breaking Changes
- なし

今後の予定（予定項目）
- research/factor_research の完遂とユニットテスト追加
- 監視・発注周りの E2E テスト、error/alerting の強化（LINE 通知等）
- 単体テスト・型アノテーション補完、CI ワークフロー整備

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノート作成時はコミットログや PR 説明をもとに内容を精査・追記してください。