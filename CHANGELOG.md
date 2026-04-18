CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。

注: 以下はリポジトリ内のコードから推測して作成した変更履歴です。実際のコミット履歴がある場合はそちらを優先してください。

Unreleased
----------

- 既知の未実装 / TODO:
  - research/factor_research.py が途中（関数内で処理が切れている箇所あり）。モメンタム計算ロジックの続き実装が必要。
  - position_sizing における price フォールバック（前日終値や取得原価など）や銘柄別 lot_size の拡張は TODO コメントで残されている。
  - 一部の処理で将来的な拡張（銘柄別 lot_size、フォールバック価格など）が示唆されている。

- 改善案（提案）:
  - run_monitoring / run_execution の起動ロジックにおける停止フラグの運用や PID ファイルの取り扱いについてのドキュメント化。
  - paper_trading 用 DB/ログのバックアップ運用および DuckDB の管理手順の明記。

0.1.0 — 初回リリース (推定)
---------------------------

Added
- 基本機能および起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) による外部停止対応と execution.pid 管理。
    - RiskManager に初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず production 相当の sqlite_path を使用して監視 DB に記録する設計（明示的に本番パスを利用する仕様）。
    - 停止フラグ検知と例外ハンドリングを行い安定してループを継続。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序・上書きルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - .env パースの堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等）。
    - Settings クラスを導入し、アプリ設定（DB パス、API トークン、ログレベル、監視閾値、環境判定等）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の妥当性チェックを実装。
  - config_setup.py
    - 対話式 .env ウィザード（CLI）を追加。既存 .env 読み込み・編集・保存機能を提供。
    - secret 項目はマスクして表示。保存前に確認プロンプトあり。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および YAML パース（PyYAML 利用可能時）などを検証。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分。スコア全0 の場合は等分配へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超えるセクターの新規候補を除外するロジック。
      - sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
      - "unknown" セクターは上限制限を適用しない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を決定。
      - risk_based: 許容リスク率・損切り率に基づくポジションサイズ計算。
      - equal/score: ウェイトに応じた配分（max_per_stock, lot_size による丸め）。
      - aggregate cap: 全銘柄合計コストが available_cash を超えた場合にスケールダウン。残差（fractional remainder）を考慮して lot_size 単位で再配分するアルゴリズム。
      - cost_buffer を考慮した保守的見積り（スリッページ・手数料）。
      - lot_size は現在は全銘柄共通だが将来的に銘柄別対応を想定した TODO がある。

- ユーティリティ
  - utils/logging_setup.py
    - 共通のロギングセットアップ関数を追加。
    - stdout（StreamHandler）と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソール出力のみ継続。
    - ログレベルとログディレクトリの解決順をドキュメント化。
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（psutil 利用）。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への固定（psutil 利用）。例外時は警告を出してスキップ。

- データ解析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを計算して表示。
    - Pass/Fail 基準値を定義（例: uptime >= 99.0%, fill_rate >= 90% 等）。
    - 日付フィルタ（--from, --to）および DB パス指定（--db）をサポート。
    - P95 計算と欠損データの扱いに配慮した実装。

- データベース / 分析
  - DuckDB 統合
    - 複数のモジュール（tools, research, execution など）で duckdb 接続を利用する設計を採用。デフォルトパスは data/kabusys.duckdb。

Changed
- 設計上の重要点（ドキュメント化）
  - 監視（monitoring）は起動環境にかかわらず本番向け sqlite_path を使用する仕様（run_monitoring の明示的な挙動）。
  - .env の自動読み込みはプロジェクトルートが特定できない場合はスキップして安全側に寄せる実装。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス対応、引用文字列中のバックスラッシュエスケープ処理、インラインコメントの扱い等により .env の多様な記法への耐性を向上。

Security
- .env に関する注意喚起を config_setup の生成ヘッダに明記（.env を Git に絶対コミットしないこと）。

Removed
- なし（初回リリース相当のため削除はなし）。

Deprecated
- なし。

Notes / Known limitations
- research/factor_research.py が途中で終わっており、ファクター計算モジュールの完全実装は未完。
- 一部のロジックは現在シンプルなフォールバック（price=0 の扱い等）をしており、実運用でのデータ欠損ケースに対する堅牢化が今後の課題。
- psutil による優先度設定 / CPU affinity は権限不足やプラットフォーム差異で失敗する可能性があり、その場合は警告ログが出て処理を継続する設計。

作者注
- 実際のリリースノートを作成する際はコミット単位の差分や issue/ticket の参照を追加してください。
- 本 CHANGELOG はソースコードの実装内容・コメントから推測して作成しています。