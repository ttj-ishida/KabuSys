Keep a Changelog
=================

この CHANGELOG は提供されたコードベースの内容から仕様・実装を推測して作成したものです。実際のコミット履歴ではなく、コードから読み取れる機能追加・設計決定・修正点をまとめています。

フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- ドキュメント化 / テストの追加（推奨）
  - ユニットテストや統合テスト、API クライアントのモックテストの整備を推奨。
  - README / 使用例・API ドキュメントの追加を推奨。

- 実装予定（コード上で未実装・注記あり）
  - feature_engineering / signal_generator に記載された未実装の条件（トレーリングストップ、時間決済など）の実装。
  - execution 層の具体的な発注ロジックや monitoring モジュールの実装・公開。

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パブリック API: kabusys.strategy.build_features, kabusys.strategy.generate_signals をエクスポート。
  - __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env パースの堅牢化（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱い）。
  - 環境変数の必須チェック _require(), Settings クラスによるプロパティアクセスを提供（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベルなど）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。

- データ取得・保存: J-Quants クライアント (kabusys.data.jquants_client)
  - API ベース実装（/_BASE_URL）。
  - 固定間隔レートリミッタ実装（120 req/min 相当）、_RateLimiter。
  - 再試行（指数バックオフ）ロジック、HTTP 408/429/5xx のリトライ、429 の Retry-After 対応。
  - 401 受信時はトークン自動リフレッシュ（1 回）を行う仕組みと ID トークンキャッシュ。
  - ページネーション対応の fetch_... 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT / DO UPDATE を利用。
  - 入力パース用ユーティリティ (_to_float, _to_int) と取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止。

- ニュース収集 (kabusys.data.news_collector)
  - RSS 収集基盤実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策: defusedxml を利用した XML パース、受信バイト数上限、HTTP/HTTPS スキーム検証、SSRF を意識した設計。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホストの正規化、フラグメント除去、クエリソート）。
  - 記事IDの SHA-256 ベース生成方針（冪等性確保）。
  - バルク INSERT のチャンク処理とトランザクションまとめ挿入、INSERT 成功件数の正確な取り扱いを想定。

- リサーチ用モジュール (kabusys.research)
  - factor_research: prices_daily/raw_financials を用いたファクター計算を実装。
    - Momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日ウィンドウ）
    - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日ウィンドウ）
    - Value: per, roe（raw_financials の最新報告を結合）
  - feature_exploration:
    - 将来リターン算出(calc_forward_returns)（複数ホライズン対応、SQL で一括取得）
    - スピアマンランク相関 (calc_ic) とランク関数(rank)
    - factor_summary: 基本統計量 (count/mean/std/min/max/median)
  - zscore_normalize ユーティリティを data.stats から利用する前提で統合。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で計算した raw factor をマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定カラムの Z スコア正規化、±3 でのクリップ実装。
  - features テーブルへ日付単位で置換（DELETE→INSERT のトランザクション）により冪等性を確保。
  - DuckDB を直接受け取る設計（発注層へ依存しない）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出するフレームワーク実装。
  - コンポーネントスコア:
    - momentum (複数モメンタム + ma200_dev をシグモイド→平均)
    - value (PER を 20 を基準にスケール)
    - volatility (ATR の Z スコアを反転してシグモイド)
    - liquidity (volume_ratio のシグモイド)
    - news (AI スコアのシグモイド、未登録は中立)
  - 重みのマージ/検証、合計が 1 でない場合のリスケール、無効値のスキップ等の堅牢化。
  - Bear レジーム判定（ai_scores.regime_score 平均が負 → BUY を抑制）。サンプル不足時の誤判定防止ロジック。
  - BUY の閾値（デフォルト 0.60）・STOP-LOSS（-8%）等のルール実装。
  - 保有ポジションに基づく SELL 判定（positions テーブルを参照）、価格欠損時の安全処理。
  - signals テーブルへ日付単位で置換して保存（トランザクション＋バルク挿入）。

Changed
- ロギング・エラーハンドリングの追加
  - 各モジュールで詳細な logger 呼び出しを追加（info/debug/warning）。
  - DB トランザクション失敗時に ROLLBACK の例外を警告し、その上で例外を再スローする実装。

- データ欠損への安全策
  - 各種計算で None / 非有限値（NaN/Inf）の取り扱いを厳密化。
  - features に存在しない保有銘柄は final_score = 0 と扱う旨の明示、価格が取得できない場合は売却判定をスキップする安全策を追加。

Fixed
- 冪等性の担保
  - raw_xxx / features / signals への書き込みを ON CONFLICT / DELETE→INSERT のパターンで実装し、重複や再実行による二重書き込みを防止。

Security
- ニュース収集で defusedxml の使用や受信サイズ制限、URL 正規化による SSRF / XML Bomb 対策を組み込み。
- HTTP クライアントでタイムアウトや再試行制御を実装し、外部依存関係からの例外耐性を向上。

Documentation
- 各モジュールに docstring が充実（設計方針、処理フロー、引数/戻り値の説明、未実装事項の注記）。

Notes / Limitations (コード上で明示)
- execution パッケージはプレースホルダ（発注 API への接続・実行ロジックは未実装）。
- 一部戦略ルール（トレーリングストップ、時間決済）はコメントとして記載されているが未実装。
- ai_scores / positions などの外部テーブルの前提に依存するため、スキーマ準備とデータ供給が必要。

参照
- パッケージの公開 API は kabusys.strategy.build_features / kabusys.strategy.generate_signals を想定。
- データ格納: DuckDB を前提（関数は DuckDBPyConnection を受け取る設計）。

--- 

（この CHANGELOG はコード内容からの推測に基づくため、実際の変更履歴やコミットメッセージとは異なる場合があります。必要であれば、実コミット履歴や担当者に基づいて修正・追記してください。）