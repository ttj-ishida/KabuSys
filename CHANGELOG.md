# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag により制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用（本番 DB と完全分離）し、MockBrokerClient を利用する旨をドキュメント化。停止フラグ / PID ファイル管理を組み込み。

- 設定管理・自動 .env ロード
  - kabusys.config.Settings を実装。多数の環境変数を型変換して提供（J-Quants / kabu API / LINE / DB / 監視閾値 / ログ等）。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装し、.env / .env.local を自動で読み込む機能を追加（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント取り扱いルールを実装。

- ポートフォリオ構築ロジック（pure functions）
  - portfolio.portfolio_builder: シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。全スコアが 0 の場合は等金額配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームにより投下資金を調整する calc_regime_multiplier を追加（regime に応じた乗数マップを実装し未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio.position_sizing: 株数決定ロジックを実装（risk_based / equal / score の allocation_method 対応）。単元株（lot_size）で丸め、手数料/スリッページを見込む cost_buffer、aggregate cap によるスケールダウン、残差処理による再配分ロジックを実装。

- リサーチ（研究用）モジュール
  - research.factor_research: DuckDB を用いたモメンタム（1/3/6 か月・MA200乖離）、ボラティリティ（ATR20、出来高等）、バリュー（PER/ROE）計算関数を追加。データ不足時の None ハンドリング、SQL ウィンドウ関数を活用した実装。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、rank ユーティリティを追加。外部ライブラリに依存しない純粋 Python 実装。

- ニュース NLP スコアリング
  - ai.news_nlp: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出し ai_scores テーブルへ書き込む処理を追加。バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、スコアクリップ（±1.0）、タイムウィンドウ定義（JST 基準で前日 15:00 〜 当日 08:30）などを実装。API エラーや 429/5xx に対するリトライ戦略（指数バックオフ）やレスポンス検証を採用。

- ユーティリティ
  - utils.process_priority: マルチプラットフォーム対応のプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。CPU affinity 設定ヘルパーも提供。権限不足や未対応 OS では警告を出してスキップする安全策を実装。

- DuckDB / SQLite の利用
  - 多くのモジュールで DuckDB/SQLite 接続を受け取る設計に統一。各スクリプトは起動時に接続を作成し、終了時にクローズするよう実装。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定（しきい値はソース内定義）を標準出力に整形して出力。日付フィルタ（--from / --to）と DB パスの CLI オプションをサポート。

### 変更 (Changed)
- 監視・実行挙動
  - run_monitoring は MONITOR_POLL_INTERVAL に不正値（0 以下 や非整数）が与えられた場合に警告を出しデフォルト（60 秒）へフォールバックするように改良。
  - run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（data/monitoring.db のデフォルト）を監視用 DB として使用する旨を明記。
  - run_execution は paper_trading 環境時に paper_sqlite_path を優先して使用し、本番 DB と完全分離する動作を明確化。

- 設定読み込みのポリシー
  - .env のロード順序を OS 環境 > .env.local > .env として自動ロードの優先度を定義。既存の OS 環境変数はデフォルトで保護され、.env.local が上書きする挙動を明確化。

- ログ出力
  - 重要操作（プロセス優先度設定、起動環境、監視ループ開始/停止、エンジン停止等）に INFO/DEBUG ログを追加して運用時の可観測性を強化。

### 修正 (Fixed)
- .env 読み込みでのエラー処理
  - ファイル読み込み時の OSError を捕捉して警告を出すようにし、自動ロードが致命的に失敗しないように改善。

- process_priority 周りの堅牢化
  - 非対応 OS / 権限不足時に例外で停止させず警告ログでスキップするように修正（psutil の AccessDenied や NotImplementedError をハンドリング）。

- position_sizing / aggregate cap スケール処理
  - aggregate cap 超過時にスケールダウンして単元株丸めを考慮した再配分アルゴリズムを実装し、端数処理の安定性を向上（残差ソートでの安定順序付けを確保）。

- research モジュールの境界条件
  - ホライズン指定チェック（horizons が正の整数かつ 252 以下）や、データ不足時の None ハンドリングを厳格化。

- tools.paper_verification_report の堅牢化
  - SQLite のテーブル存在エラー（OperationalError）を捕捉してレポート出力を継続できるようにし、データ無し時の表示を N/A に統一。

### ドキュメント (Documentation)
- 各モジュールに docstring を追加し、設計方針・引数・戻り値・注意点（例: レジームの扱い、単元株丸めの将来拡張案等）を明記。
- ai.news_nlp、research、portfolio モジュールに設計ノート・処理フローを追加して利用者向けの理解を補助。

### その他
- パッケージ初期化ファイルに __version__ = "0.1.0" を設定。
- 複数箇所でデフォルトパス（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid 等）を明記し、デフォルトで動作可能な構成を提供。

---

今後の予定（候補）
- AI スコアリング周り: レスポンスの部分失敗時の部分ロールバック/リトライ戦略の強化、API レート制御の改善。
- position_sizing: 銘柄別 lot_size マスタの導入と銘柄別対応。
- monitoring: SystemMonitor の詳細なメトリクス定義とアラート連携（LINE 等）実装。