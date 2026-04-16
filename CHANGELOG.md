# Changelog

すべての変更は「Keep a Changelog」の仕様に準拠して記載しています。主にソースコードから推測できる機能追加・改善点・修正点をまとめています。

## [Unreleased]

### Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite を使用し、Mock ブローカー経由で分離された検証が可能（data/paper_trading.db）。停止フラグの検出や PID ファイルの管理、スレッドでの実行停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。監視は常に本番用 sqlite_path を参照するようになっている。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）。risk_based / equal / score の各配分方式、lot サイズ丸め、aggregate cap によるスケールダウンと再配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）。

- リサーチ・分析機能を追加
  - research/factor_research.py: モメンタム・ボラティリティ・バリューなどのファクター計算（DuckDB を使った SQL 実装）。MA200、ATR20、各種モメンタム（1M/3M/6M）や PER/ROE 計算を提供。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、スピアマンランク相関による IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats）等と結合して公開。

- ニュース NLP スコアリング機能を追加
  - ai/news_nlp.py: raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。スコアのクリップ（±1.0）、チャンク処理、再試行（指数バックオフ）、レスポンス検証、部分書き換えによる部分失敗耐性などを備える。ニュース収集ウィンドウの計算ユーティリティ calc_news_window を提供。

- 検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。閾値（稼働率99%、成功率90%、送信率95%、P95 200ms）を定義。

- 設定・環境読み込みの改善
  - config.py: プロジェクトルート検出（.git または pyproject.toml を探索）に基づく自動 .env 読み込みを実装（.env → .env.local、OS 環境変数の保護対応）。 .env のパースはクォート内エスケープやインラインコメントに対応。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。Settings クラスに多数のプロパティ（DB パス、paper_trading 用パス、PID/kill フラグパス、閾値、env/log_level のバリデーション等）を追加。

- プロセス優先度・CPU 固定ユーティリティを追加
  - utils/process_priority.py: Windows/Linux（POSIX）差異を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority、CPU affinity を設定する set_cpu_affinity を実装。権限不足等の例外は警告ログに落とすフェールセーフを備える。

### Changed
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能に。0 以下や不正値はデフォルト（60 秒）にフォールバックし、警告を出力する。

- DB 接続の扱い
  - run_monitoring は監視用途の DB として環境にかかわらず本番用 sqlite_path を使用する仕様（意図的に分離しない運用想定）。
  - run_execution は KABUSYS_ENV に応じて paper_trading 用 DB（settings.paper_sqlite_path）を使用するようにし、paper_trading モードでは本番 DB から分離して動作。

- position_sizing のアルゴリズム改善
  - aggregate cap 適用時のスケーリング。スケールダウン後の残余キャッシュを利用して単元（lot_size）単位で端数配分を行うロジックを追加し、最大上限（_max_per_stock）や raw_shares の上限を尊重する安全弁を実装。

- factor_research / feature_exploration の SQL ロジック
  - DuckDB を利用した集計クエリの最適化・堅牢化（欠損値の扱い、ウィンドウ関数のカウント条件、スキャン範囲のカレンダーバッファ等）。将来リターン計算は任意ホライズンを受け入れ、引数検証を強化。

### Fixed
- .env パーサの堅牢化
  - _parse_env_line で export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理を適切に扱うように修正。無効行のスキップを明確化。

- ニュース NLP の安全対策
  - API キー未設定時に ValueError を送出するチェックを追加。API レスポンス検証・部分更新戦略により API 部分失敗時のデータ保全性を向上。

- process_priority のフェールセーフ
  - 権限不足や未対応 OS での動作失敗時に警告ログを出して処理を継続するように改善。

- report/集計系の欠損対応
  - paper_verification_report のクエリでテーブル不在やデータ不足（OperationalError 等）を捕捉して N/A 表示にフォールバックするようにした（クリーンな CLI 出力を確保）。

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で解決し、未設定時は明示的にエラーを出すようにして漏洩や未設定による不具合を防止。

---

## [0.1.0] - 2026-04-15
初期リリース相当。上記 Unreleased の内容を含むベース実装を公開。
- 基本的な実行・監視パイプライン、ポートフォリオ構築、ポジションサイジング、リスク調整、リサーチ（ファクター計算・特徴量解析）、ニュース NLP、検証ツール、設定管理、ユーティリティ関数などを含むモジュール群を実装。
- パッケージメタ情報: __version__ = "0.1.0"

カテゴリ定義:
- Added: 新規機能の追加
- Changed: 既存機能の挙動改善・変更
- Fixed: バグ修正や堅牢化
- Security: セキュリティに関わる改善

注記:
- 上記はソースコードから推測して作成した変更履歴です。細かな動作仕様や追加の修正履歴は実際のコミットログやリポジトリのタグを参照してください。