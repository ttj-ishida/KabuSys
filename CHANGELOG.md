# CHANGELOG

すべての注記は Keep a Changelog のフォーマットに準拠しています。  
この CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

### Added
- 基本パッケージ構成を追加（kabusys ルートパッケージ、submodule: data / research / strategy / execution / monitoring を想定）。
- settings を通した環境変数管理の自動読み込み機能を追加
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - export KEY=val 形式やクォート・エスケープ、インラインコメント等に対応した .env パーサを実装。
- Settings クラスを導入し、アプリケーション設定（J-Quants トークン、kabu API 設定、Slack、DB パス、実行環境、ログレベル等）を型安全に取得・検証するインターフェースを追加。
  - KABUSYS_ENV / LOG_LEVEL の値検証、is_live / is_paper / is_dev のユーティリティを提供。
- Data 層: J-Quants API クライアントを追加
  - 固定間隔のレートリミッタ（120 req/min）を実装。
  - 再試行（指数バックオフ、最大 3 回）・ステータスコード判定（408/429/5xx）に基づくリトライロジックを実装。
  - 401 発生時の自動トークンリフレッシュとリトライ、モジュールレベルの id_token キャッシュをサポート。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - レスポンスパース・型変換ユーティリティ（_to_float / _to_int）を実装し不正データを安全に扱う。
- News 層: RSS ニュース収集モジュールを追加（news_collector）
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホストの小文字化）を実装。
  - RSS 取得時の受信サイズ制限（MAX_RESPONSE_BYTES）・トラッキングパラメータの除去・記事 ID のハッシュ化方針などを盛り込んだ安全志向の実装方針を追加。
  - defusedxml を用いた XML パースによるセキュリティ対策を明記。
  - bulk INSERT のチャンク化等パフォーマンス配慮を導入。
- Research 層: ファクター計算・探索ユーティリティを追加
  - ファクター計算（calc_momentum / calc_volatility / calc_value）を実装（prices_daily / raw_financials を参照）。
  - 将来リターン計算 calc_forward_returns を実装（複数ホライズン対応、SQL による一括取得）。
  - IC（スピアマンのランク相関）計算 calc_ic、ランク付け util rank を実装。
  - factor_summary による基本統計量サマリー出力を実装。
  - zscore 正規化ユーティリティ（kabusys.data.stats を参照）への依存指定。
- Strategy 層: 特徴量生成・シグナル生成モジュールを追加
  - feature_engineering.build_features を実装
    - research モジュールの生ファクターを統合してユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムについて Z スコア正規化 → ±3 でクリップ。
    - 日付単位で features テーブルへ冪等 UPSERT（DELETE→INSERT のトランザクション）を実現。
  - signal_generator.generate_signals を実装
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
    - デフォルト重み・閾値（デフォルト: threshold=0.60）を実装し、ユーザー重みの検証・再スケーリングをサポート。
    - Bear レジーム判定（AI の regime_score 平均）による BUY 抑制ロジックを導入。
    - エグジット判定（ストップロス -8%・スコア低下）による SELL シグナル生成。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）を実装。
- パッケージ公開 API を __all__ で整理（strategy, research などの公開関数を明示）。

### Changed
- なし（初期リリース想定）

### Fixed
- なし（初期リリース想定）

### Security
- defusedxml の使用、RSS パース時の受信サイズ制限、URL 正規化・トラッキング除去、HTTP スキーム検証などにより外部入力による攻撃（XML Bomb / SSRF / メモリ DoS 等）への対策を明記。
- J-Quants クライアントで 401 リフレッシュ回復を実装し認証失敗時の安全な再試行を導入。

---

## [0.1.0] - 2026-03-20

この初期リリースは上記 Unreleased の実装をパッケージ化したものとして想定しています。

### Added
- パッケージの初期バージョンを公開。
- 環境変数管理（.env 自動読み込み / Settings クラス）。
- J-Quants API クライアント（取得・保存・レート制御・リトライ・トークン自動更新）。
- DuckDB を用いたデータ保存用の save_* 関数群（raw_prices / raw_financials / market_calendar 用）。
- RSS ニュース収集基盤（正規化・セキュアパース・bulk 保存戦略）。
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）。
- 戦略モジュール（特徴量構築、シグナル生成、売買ルールの実装）。
- ロギングと入力検証を強化（各所で warning/info/debug を出力）。

### Fixed
- N/A（初回リリース）

### Security
- defusedxml と入力制限による XML/HTTP セキュリティ対策を実装。

---

注:
- 本 CHANGELOG はコードの実装内容から推測して作成したため、実際のコミットメッセージやリリースノートと完全には一致しません。必要であれば、実際のコミットログやリリース日・変更差分を元に微調整します。