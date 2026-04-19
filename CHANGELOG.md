# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
この CHANGELOG は提示されたコードベースの内容から機能追加・設計決定・修正点を推測して作成しています。

全般的な注意
- ここに記載した項目はソースコードの実装・コメント・TODO から推測したものであり、実際のコミット履歴ではありません。
- 日付は本ファイル作成日（2026-04-19）を使用しています。

## [Unreleased]
- 次バージョンで検討すべき事項（コード上の TODO / 改善候補）
  - portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を導入する検討。
  - portfolio.position_sizing: 将来的に銘柄別の単元（lot_size）をサポートするための拡張（stocks マスタを参照）を検討。
  - research.factor_research モジュールの実装完了（calc_momentum の実装途中のため残作業あり）。
  - ロギングのリモート/集中管理やより詳細なローテーションポリシーの検討。
  - 単体テスト・統合テストの追加（現状では機能単位の実装はあるがテストコードは見えない）。

---

## [0.1.0] - 2026-04-19

Added
- 初期リリースとしてシステムの主要コンポーネントを実装。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを実装。
      - プロセス優先度を "high" に設定する処理を追加（set_process_priority）。
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て処理を実装。
      - ExecutionEngine を別スレッドで起動し、 stop フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。PID ファイル管理。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告を出力。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計（settings.sqlite_path）。
      - stop フラグ（data/stop_requested.flag）検知でループを終了、KeyboardInterrupt をハンドルして安全終了。
  - 設定関連
    - config.py
      - Settings クラスを実装し、環境変数経由でアプリ設定を統一的に取得。
      - .env の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env のパースはシングル/ダブルクォート、export プレフィックス、インラインコメント等に対応。
      - 各種プロパティ（J-Quants、kabu API、DuckDB/SQLite パス、paper_trading 用の設定、監視閾値、環境判定ユーティリティ等）を提供。
    - config_setup.py
      - 対話式ウィザードで .env を作成/更新する CLI を実装。既存 .env の読み込み・既存値の再利用・シークレットマスク表示に対応。
    - validate_config.py
      - 起動前に .env や config/*.yaml の妥当性をチェックする CLI を実装。--strict モードを提供して警告も失敗扱いにできる。
      - 必須環境変数未設定や KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML が存在する場合）などを行う。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 統一ロギング設定ユーティリティを実装。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
      - LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップして安全に続行。
    - utils/process_priority.py
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows/Linux (POSIX) の差を吸収しつつ、失敗時は警告を出す。
      - psutil を利用。アクセス権限の問題が発生しても例外を握りつぶして警告ログを出力する設計。
  - ポートフォリオ構築ロジック（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点時のタイブレークロジックあり）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限ロジックを実装（既存保有のセクター別エクスポージャー算出、上限超過セクターの候補除外）。"unknown" セクターは制限の対象外。
      - calc_regime_multiplier: market_regime に応じたレジーム乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバックし警告。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各 allocation_method に対応した株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1 銘柄上限および aggregate cap によるスケーリング、cost_buffer を考慮した保守的計算、残差に基づく追加配分ロジックなどを実装。
  - 研究・ツール
    - research/factor_research.py
      - ファクター計算モジュール（モメンタム・MA200 乖離・ATR 等の仕様と定数を定義）。DuckDB 接続を受けて prices_daily を参照する設計（calc_momentum の実装は途中）。
    - tools/paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI を実装。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を出力する。
      - P95 計算実装、閾値（稼働率 99%、成立率 90% 等）と CLI オプション（--from/--to/--db）を提供。
  - その他
    - パッケージ識別子 __version__ = "0.1.0" を設定。
    - モジュールのエクスポートを __all__ で整理（kabusys パッケージ）。

Changed
- 環境変数ロード戦略を明確化（OS 環境 > .env.local > .env）。既存 OS 環境変数は保護され、.env.local は上書き可能。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対してデフォルトにフォールバックし警告を出す挙動を実装。
- logging_setup: ログ出力先を stdout に統一（StreamHandler）し、ファイル出力失敗時にフォールバックする挙動を実装。既存ハンドラを再構成して二重登録を防止。

Fixed
- .env パーサーの耐久性向上
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
- process_priority のエラー耐性強化
  - psutil による優先度設定が失敗した場合もプロセスは継続し、警告ログのみ出力するよう変更。

Security
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に格納する設計。config_setup の出力にて .env を Git にコミットしないよう明記。
- validate_config にて本番環境（KABUSYS_ENV=live）の場合、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告するチェックを追加。

Notes / Known issues
- research/factor_research.calc_momentum の実装が途中で終わっている（ファイル末尾が切れているように見える）。実運用前に完成が必要。
- portfolio.risk_adjustment.apply_sector_cap は price が欠損するケースへのフォールバック処理が未実装（TODO コメントあり）。
- position_sizing の将来的な拡張点として銘柄別 lot_size をサポートする設計メモが残されている。
- run_monitoring はコード上で「監視は環境にかかわらず本番 sqlite_path を使用する」と明記しているため、監視 DB の分離が必要な環境では注意が必要。
- 実際のブローカークライアント実装（BrokerClientFactory や MockBrokerClient）の詳細はこの差分からはわからないため、実運用前に接続試験が必要。

---

この CHANGELOG はソースコードから読み取れる仕様・実装意図に基づいて作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて更新してください。