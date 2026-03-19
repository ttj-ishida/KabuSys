# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システムのコア機能群を実装しました（パッケージ名: kabusys）。以下の主要コンポーネントと設計上の注意点を含みます。

### Added
- パッケージ公開情報
  - パッケージ __init__ にてバージョン "0.1.0" を設定。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定/環境変数管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - .env パーサは export KEY=val 形式、クォート文字列（エスケープ対応）、インラインコメント処理などをサポート。
  - Settings クラスによる型安全な設定アクセス（J-Quants トークン、kabu API 設定、Slack、DBパス、環境/ログレベルの検証メソッド等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許可値以外は ValueError を発生）。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得関数）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - HTTP リトライ（最大3回、指数バックオフ）、408/429/5xx ハンドリング、429 の場合は Retry-After を優先。
  - 401 受信時はリフレッシュ（get_id_token）して一度だけリトライする処理を実装。
  - ページネーション対応（pagination_key）とモジュール内トークンキャッシュ。
  - DuckDB 向け保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、冪等性のため ON CONFLICT DO UPDATE を使用。
  - CSV/JSON からの型変換ユーティリティ（_to_float / _to_int）。
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集の基礎構成を実装（デフォルトソース: Yahoo Finance の RSS）。
  - URL 正規化（トラッキングパラメータ除去・クエリソート・スキーム/ホストの小文字化、フラグメント削除）。
  - セキュリティ対策: defusedxml 利用、受信バイト数上限（MAX_RESPONSE_BYTES）、SSRF に配慮した URL 検証、トラッキングパラメータ除去等の設計方針を採用。
  - raw_news / news_symbols への冪等保存とバルク処理（チャンク制御）。
- リサーチモジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - MA200、ATR20、出来高移動平均、avg_turnover、PER/ROE などを SQL で算出。
    - 欠損やデータ不足に対する安全な None ハンドリング。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで動作するよう設計。
  - これらを research パッケージの __all__ で再公開。
- 戦略モジュール（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 = 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を確保。
  - signal_generator.generate_signals
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完、重み付け合算による final_score 計算（デフォルト重みを実装）。
    - 重みは入力で上書き可（検証・正規化・スケーリングを実施）。
    - Buy threshold デフォルト 0.60、Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）では BUY を抑制。
    - 売り（エグジット）判定: ストップロス（終値/avg_price -1 < -8%）とスコア低下（final_score < threshold）を実装。SELL シグナル優先で BUY から除外。
    - signals テーブルへ日付単位で置換（冪等）。
- その他
  - 設計やドキュメント文字列（docstring）にてルックアヘッドバイアス防止、冪等性、トランザクション制御、ログ出力の方針を明確化。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- news_collector で defusedxml を採用し XML 脆弱性への対策を実装。
- RSS/URL の扱いでトラッキングパラメータ除去と受信バイト数制限を導入し、メモリ DoS やトラッキングによる誤検出を軽減。
- J-Quants クライアントは 401 時のトークン自動刷新を限定的に行い、無限再帰を防止。

### Notes / Known limitations
- 一部の機能はドキュメント内で「未実装」として明記（例: signal_generator のトレーリングストップ、時間決済には positions テーブルの追加情報が必要）。
- news_collector の完全なパーシング/DB保存処理は安全方針を示す実装が中心で、実運用の際は RSS の取得・パース周りの追加テストが推奨されます。
- 外部依存を最小化する設計だが、DuckDB スキーマ（テーブル定義）や外部サービス（J-Quants, Slack, kabu API）に依存するため、統合時に環境変数設定や DB スキーマ準備が必要です。

---
作業内容や設計意図は各モジュールの docstring / ログメッセージにも明記されています。リリース以降の改善案（例: トレーリングストップ実装、ニューステキストの NLP 前処理強化、テストカバレッジ拡充など）は別Issueで管理することを推奨します。