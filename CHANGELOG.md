Keep a Changelog に準拠した変更履歴（日本語）
========================================

すべての変更は SemVer に基づき記載しています。

v0.1.0 - 2026-04-19
-------------------

Added
- 基本パッケージ初版を追加
  - パッケージメタ情報を追加: src/kabusys/__init__.py に __version__ = "0.1.0"
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト data/paper_trading.db）へ記録する分離設計を導入。起動時にプロセス優先度を設定し、停止フラグによる安全停止をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する仕様。
- 環境・設定管理 CLI/ユーティリティ
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（.env のテンプレート生成、シークレット入力をマスク表示、保存時確認など）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。--strict オプションで警告を FAIL として扱える。PyYAML 未インストール時の挙動と警告表示に対応。
- 環境変数自動読み込み／堅牢化
  - config.py: .env の自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml）。読み込み優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。.env パーサを強化し、export 形式、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを追加し、アプリケーション設定（DB パス、API トークン、各種閾値、環境フラグ等）をプロパティ経由で提供。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を一括設定するユーティリティを追加。LOG_DIR 作成失敗時はファイル出力をスキップして console のみで継続するなど堅牢化。
  - utils/process_priority.py: Windows / POSIX を透過するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限制約や未対応 OS を安全にハンドリング。
- Portfolio 構築関連（純関数群）
  - portfolio/portfolio_builder.py: シグナルのソートと候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。全スコアがゼロの場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を追加。未知のレジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジック(calc_position_sizes) を追加。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）での丸め、ポジション上限や aggregate cap（利用可能現金へのスケールダウン）、手数料/スリッページ想定(cost_buffer) を考慮した配分ロジックを実装。残差分配のための安定した再現性アルゴリズムを導入。
  - portfolio/__init__.py で上記関数を公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード結果（data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。閾値（稼働率99%、成立率90%、送信率95%、P95 <= 200 ms）による PASS/FAIL 判定を実装。期間フィルタ（--from/--to）や DB パスオーバーライドをサポート。
- 研究モジュール（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子（モメンタム、MA、ATR、出来高指標等）を追加（未完の関数あり、将来的に duckdb SQL と組み合わせて計算予定）。
- データベース関連
  - 各起動スクリプトで duckdb 接続を受け取り使用。監視用 DB の初期化関数 init_monitoring_db が利用される（冪等なテーブル作成保証）。

Changed
- ログ出力先の標準化
  - ログのコンソール出力は stderr ではなく stdout を使用するように変更（cron/task scheduler でのリダイレクト運用を想定）。
- .env 読み込みの保護
  - 自動ロード時、OS 既存環境変数は保護され上書きされない（.env.local の override は許容だが OS 環境は保護）。

Fixed
- 環境値パースの堅牢化
  - .env の行解析でクォート内のバックスラッシュエスケープやインラインコメントを正しく処理するように改善。export KEY=val 形式をサポート。
- プロセス優先度設定の例外処理強化
  - 権限不足や未実装 API に対する例外（AccessDenied / AttributeError / NotImplementedError）を警告に落とすようにして、起動失敗を防止。

Security
- .env 取り扱い注意の明示
  - config_setup が生成する .env テンプレートに「.env は絶対に Git にコミットしないこと」を明記。

Notes / Usage highlights
- MONITOR_POLL_INTERVAL 環境変数で監視ループのポーリング間隔を設定可能（整数秒、1 未満は無効としてデフォルト 60 秒にフォールバック）。
- PAPER_FILL_MODE（instant/partial/never/reject）でペーパートレードの約定挙動を設定可能（不正値は例外）。
- PAPER_TRADING_SQLITE_PATH によりペーパートレード専用 DB のパスを指定可能。実運用（live）と開発/ペーパーは DB を分離する設計。
- validate_config により起動前の設定チェックがおこなえる。--strict を付けると警告もエラー扱い（exit 1）になる。
- logging_setup はログディレクトリ作成に失敗してもコンソール出力のみで継続するため、環境による起動失敗を防ぐ。

Known limitations / TODO
- research/factor_research.py はファクター計算の骨子を作成済みだが、完全実装/テストは未完。
- position_sizing の price フォールバック（前日終値や取得原価）や銘柄別 lot_size の拡張は TODO コメントあり。
- 一部ファイルは内部 API（ExecutionEngine、OrderManager、BrokerClient 等）への依存があり、結合テストが必要。

License
- （プロジェクトのライセンス情報をここに記載してください。）
  
以上。