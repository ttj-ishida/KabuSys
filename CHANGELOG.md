# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の慣習に従い、安定版リリースごとに要約を残します。  

各エントリは大きく "Added / Changed / Fixed / Security" に分類しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム「KabuSys」の主要コンポーネントを実装しました。主な実装内容は以下の通りです。

### Added
- パッケージ基礎
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を定義。
  - パッケージエクスポート: data / strategy / execution / monitoring を __all__ に登録。

- 環境設定 (kabusys.config)
  - .env/.env.local 自動読み込み機能（プロジェクトルート(.git または pyproject.toml)を探索）。
  - .env のパース実装（コメント、export 形式、クォート／エスケープ対応、インラインコメント処理）。
  - 環境変数の保護機構（OS 環境変数を override しない設定 / .env.local で上書き可能）。
  - 必須変数取得ユーティリティ `_require` とバリデーション済み Settings クラス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境モード検証（development / paper_trading / live）とログレベルの検証。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
  - HTTP リクエストラッパー `_request`：リトライ（指数バックオフ、最大3回）、429 の Retry-After 優先、401 でのトークン自動リフレッシュ（1回保証）。
  - ページネーション対応の fetch メソッド: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
  - DuckDB への冪等保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（ON CONFLICT DO UPDATE を利用）。
  - 入力値変換ユーティリティ `_to_float`, `_to_int`。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録（Look-ahead バイアス対策）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集基盤（デフォルトに Yahoo Finance Business の RSS を含む）。
  - XML パースに defusedxml を利用して XML ベースの攻撃耐性を確保。
  - 受信上限バイト数制限（MAX_RESPONSE_BYTES = 10MB）を実装してメモリ DoS を緩和。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
  - 記事 ID を正規化 URL の SHA-256 先頭で生成し冪等性を確保。
  - バルク INSERT のチャンク化（パフォーマンス / SQL 長制限対策）。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING を想定）。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200日移動平均乖離率）計算: `calc_momentum`
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）: `calc_volatility`
    - Value（EPS から計算する PER / ROE）: `calc_value`
    - 各関数は DuckDB の prices_daily / raw_financials テーブルを参照して結果を (date, code) キーの dict リストで返す。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: `calc_forward_returns`（複数ホライズン対応、ホライズンは [1,5,21] がデフォルト）。
    - Information Coefficient（Spearman の ρ）計算: `calc_ic`（rank を内部で計算）。
    - ファクター統計サマリ: `factor_summary`（count/mean/std/min/max/median）。
    - ランク計算ユーティリティ `rank`（同順位は平均ランク、丸めで ties の検出漏れを防止）。
  - research パッケージのエクスポートに主要ユーティリティを登録。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング: `build_features`
    - research の計算結果をマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化（z-score）処理を呼び出し、±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）し冪等性を確保。
  - シグナル生成: `generate_signals`
    - features と ai_scores を統合して各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - 重み付け合算により final_score を生成（デフォルト重みを採用、ユーザ指定 weights は検証・正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）に基づき BUY 抑制。
    - BUY は threshold（デフォルト 0.60）超えで発生、SELL はストップロス（-8%）や final_score 低下で判定。
    - positions / prices を参照して SELL 判定を行い、signals テーブルへ日付単位で置換して保存。
  - strategy パッケージのエクスポートに build_features / generate_signals を登録。

- データ統計ユーティリティ
  - zscore_normalize はデータ層（kabusys.data.stats）から利用（research / strategy から参照）。

### Changed
- （初回リリースのため過去バージョンからの変更点はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- ニュース XML のパースに defusedxml を使用し XML-based attack を軽減。
- news_collector で URL スキームチェック・IP/SSRF の考慮（設計上の注記）、RSS の受信サイズ制限を導入。

### Notes / Known limitations / TODO
- strategy のエグジット条件のうち「トレーリングストップ（直近最高値に基づく）」や「時間決済（保有 60 日超過など）」は未実装であり、positions テーブルに peak_price / entry_date 等の追加フィールドが必要。
- news_collector による外部 HTTP 呼び出し・解析はネットワーク依存であり、リトライやバックオフ戦略の詳細（J-Quants 同様）は将来の改善点。
- DuckDB 側のテーブル定義（raw_prices, raw_financials, market_calendar, prices_daily, raw_news, features, ai_scores, positions, signals 等）はこのリリースではコード中の SQL 参照に基づく想定があるため、導入時にスキーマ整備が必要。
- tests / CI の追加は今後の課題。

### 必須環境変数
このリリースを利用するには少なくとも以下の環境変数の設定が必要です（kabusys.config.Settings の `_require` により未設定時に例外）。
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

---

今後のリリースでは以下の点を予定しています（例）:
- execution 層の実装（kabuステーション API 経由での発注ロジック）
- モニタリング/アラート機能の強化（Slack 通知、監視ダッシュボード）
- news_collector の言語処理（簡易な NLP による news → ai_score 生成パイプライン）
- テストカバレッジと CI の整備

---

この CHANGELOG はリポジトリの実装内容から推測して作成しています。実際のリリースノート作成時は差分・コミットログを参照して更新してください。