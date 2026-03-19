# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システムのコア機能を含む基盤実装を追加。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API: data, strategy, execution, monitoring をエクスポート）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートを .git / pyproject.toml から特定して自動ロード（CWD 非依存）。
  - .env と .env.local の優先度制御（OS 環境変数保護、override ロジック）。
  - 行パーサーは export プレフィックス、クォート・エスケープ、インラインコメント等に対応。
  - 必須設定取得ヘルパー _require と Settings クラスを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を想定）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション、開発/ペーパー/ライブ判定プロパティを提供。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）のための固定間隔スロットリング RateLimiter 実装。
  - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。429 の場合は Retry-After を優先。
  - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライする機能。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性を保つため ON CONFLICT DO UPDATE を使用。
  - fetch/save 系で取得時刻（fetched_at）を UTC ISO8601 形式で記録。
  - レスポンスパーシング用の安全な数値変換ユーティリティ (_to_float, _to_int) を提供。
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得と raw_news 保存の基礎実装を追加（既定ソースに Yahoo Finance を含む）。
  - 記事ID を URL 正規化後のハッシュで生成して冪等性を確保する方針を反映。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）を実装。
  - defusedxml を用いた XML パースやレスポンスサイズ上限（MAX_RESPONSE_BYTES）など、セキュリティ考慮を実装方針に明記。
  - DB バルク INSERT チャンク処理、挿入件数の正確な算出を想定。
- リサーチ/ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装。
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - Volatility: 20 日 ATR、atr_pct、20 日平均売買代金、volume_ratio を計算。
    - Value: per（株価/EPS）、roe を prices_daily と raw_financials から算出。
    - 各計算は prices_daily / raw_financials のみ参照し、データ不足時の None ハンドリングを実装。
  - 研究用ユーティリティ（feature_exploration）を実装。
    - calc_forward_returns: 将来リターン（デフォルト 1/5/21 営業日）を計算するクエリ実装。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties の検出精度向上）。
  - research パッケージの公開 API を整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターを取り込み、ユニバースフィルタ（価格・流動性）を適用し、Z スコア正規化（±3 クリップ）して features テーブルへ UPSERT（トランザクションで日付ごとの置換）する build_features を実装。
  - ユニバース条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - 正規化対象列とクリップ値が定義済み。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ保存する generate_signals を実装。
  - 統合重みのデフォルト（momentum/value/volatility/liquidity/news）と BUY 閾値（default 0.60）を実装。ユーザ指定重みは検証・正規化して合計 1 に調整。
  - スコア計算補助:
    - Z スコアをシグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - AI ニューススコアの補完（未登録時は中立）。
  - Bear レジーム検知（ai_scores の regime_score 平均が負で、サンプル数閾値あり）により BUY を抑制。
  - SELL（エグジット）判定の実装:
    - ストップロス（現在価格 / avg_price - 1 < -8%）優先判定。
    - final_score が threshold 未満の場合に SELL。
    - 価格欠損時は SELL 判定をスキップ（誤クローズ防止），features に存在しない保有銘柄は score=0 として扱う。
  - signals テーブルへの書き込みは日付単位で削除→挿入（トランザクション）し冪等性を担保。
- 汎用性・堅牢性
  - 多くの DB 操作でトランザクション制御（BEGIN/COMMIT/ROLLBACK）を行い、例外時にロールバックを試みるロギングを実装。
  - ロガー出力、警告ログを各所に追加し、異常ケースを可視化。
  - 外部依存を最小化（標準ライブラリ + duckdb + defusedxml）する設計方針。

### Security
- news_collector で defusedxml を用いた XML パースを採用し、XML Bomb 等への対策方針を明記。
- RSS 取得時のレスポンスサイズ制限（MAX_RESPONSE_BYTES）や URL 正規化でトラッキング除去を実施。
- jquants_client の HTTP リトライでは 429 の Retry-After を尊重する等、健全な API 利用を想定。

### Known limitations / TODO
- エグジット条件の一部（トレーリングストップ、時間決済など）はコメントとして未実装。positions テーブルに peak_price / entry_date 等の拡張が必要。
- Value ファクターの PBR・配当利回りは未実装。
- news_collector の一部セーフガード（SSRF/IP ブロック等）は方針コメントがあるが、抜粋コードでは未完実装の箇所がある可能性あり。
- execution / monitoring パッケージはスケルトンあるいは未実装（発注 API 連携は層を分ける設計）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

注: この CHANGELOG は提供されたソースコードの内容およびソース内コメントから推測して作成しています。実際のリリースノートはプロジェクトのリリース日時・バージョン管理履歴に基づいて調整してください。