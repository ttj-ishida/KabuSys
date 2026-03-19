# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

[Unreleased]

[0.1.0] - 2026-03-19
================================

Added
-----
- パッケージの初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数・設定管理
  - settings を提供する settings クラスを実装（kabusys.config）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
  - .env パーサー実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑制可能。

- データ取得・保存（J-Quants API）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
  - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュを実装。
  - ページネーション対応の fetch_* API（daily_quotes, financial_statements, market_calendar）を実装。
  - DuckDB へ冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT を利用）。
  - 文字列→float/int の安全な変換ユーティリティ (_to_float / _to_int) を実装。
  - API 呼び出し時の JSON デコードエラー時に詳細を報告。

- ニュース収集
  - RSS ベースのニュース収集モジュールを実装（kabusys.data.news_collector）。
  - デフォルト RSS ソース定義（Yahoo Finance のカテゴリ RSS）。
  - URL 正規化（トラッキングパラメータ除去、スキーム・ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）、XML 防御（defusedxml）の適用、SSRF 対策の考慮。
  - 記事 ID は正規化後の SHA-256 ハッシュで生成する方針を採用（冪等性確保）。
  - DB へのバルク INSERT をチャンク化して挿入する実装方針（INSERT チャンクサイズ定義）。

- リサーチ / ファクター計算
  - 研究用モジュールを実装（kabusys.research）。
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe、raw_financials から最新財務を取得）
    - DuckDB SQL ベースでの実装、営業日欠損に配慮したスキャン範囲バッファを採用
  - 特徴量探索ツール（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）
    - IC（Information Coefficient）計算（calc_ic：Spearman の ρ）
    - factor_summary（count/mean/std/min/max/median）と rank（同順位は平均ランク）

- 特徴量エンジニアリング / シグナル生成
  - build_features（kabusys.strategy.feature_engineering）:
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性保証）。
  - generate_signals（kabusys.strategy.signal_generator）:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や反転処理を適用し、最終スコアを重み付き合算。
    - weights 引数の妥当性チェックと合計が 1 でない場合の再スケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - SELL（エグジット）判定としてストップロス（-8%）およびスコア低下を実装。
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）。

Changed
-------
- 初期リリースのため該当なし。

Fixed
-----
- 初期リリースのため該当なし。

Known issues / Notes
--------------------
- signal_generator のエグジットロジックでは一部条件が未実装（コード内注記）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- ニュース収集における記事 ID 生成や RSS パースの細部は設計方針として記載されているが、実際の収集・紐付けロジックの細部は今後の実装/テストで調整が必要。
- .env パーサーは多くのケースを考慮しているが、極端に非標準な .env フォーマットでの挙動は保証外。
- get_id_token/getter の例外やネットワーク障害時の取り扱いはリトライ設計を組み込んでいるが、本番運用での監視が推奨される。

Security
--------
- defusedxml を用いた XML パーシングで XML Bomb 等の攻撃を軽減。
- news_collector で HTTP(S) 以外のスキームや内部 IP への接続制限など SSRF 対策を想定した設計を記載。運用ルールの併用を推奨。

その他
------
- ドキュメントや設計メモ（StrategyModel.md, DataPlatform.md 等）に準拠したコメント・実装方針をコード内に反映。
- 外部依存は最小限（duckdb, defusedxml）。標準ライブラリで可能な処理は標準ライブラリで実装する方針。

-- End of changelog --