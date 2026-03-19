# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: [バージョン] - 日付（YYYY-MM-DD）

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点と設計上の注意点は以下の通りです。

### Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは `0.1.0`。

- 設定管理
  - 環境変数 / .env 読み込みモジュールを実装（kabusys.config）。
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して .env/.env.local を自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト用）。
    - .env のパースはコメント行、export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメントを考慮。
    - OS 環境変数を保護するための protected 機構と override フラグを実装。
  - Settings クラスを提供（settings インスタンス）。
    - J-Quants / kabu API / Slack / DB パス等の必須/既定設定アクセスプロパティ。
    - env（development/paper_trading/live）や log_level の検証、便宜プロパティ（is_live 等）。

- データ層（J-Quants）
  - J-Quants API クライアント実装（kabusys.data.jquants_client）。
    - 固定間隔の RateLimiter（120 req/min）を実装し API レート制御。
    - 再試行（指数バックオフ、最大 3 回）と 408/429/5xx のリトライポリシー。
    - 401 受信時にリフレッシュトークンを使って ID トークンを自動更新し 1 回リトライ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT を用いた冪等保存を行う。
    - レスポンス JSON のデコード失敗や PK 欠損行のスキップ・ログ出力を行う。
    - 型変換ユーティリティ（_to_float / _to_int）を実装。

- データ層（ニュース収集）
  - RSS ニュース収集モジュール（kabusys.data.news_collector）を追加。
    - defusedxml を用いた安全な XML パース。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - バルク INSERT のチャンク化や 1 トランザクションでの挿入最適化、INSERT RETURNING による挿入数取得を想定。
    - 既定 RSS ソース（Yahoo Finance）を追加。

- リサーチ（ファクター計算・探索）
  - factor_research モジュールを実装（kabusys.research.factor_research）。
    - Momentum（1/3/6M リターン、200 日移動平均乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER/ROE）を prices_daily / raw_financials を参照して計算。
    - 欠損・データ不足時の None ハンドリングを徹底。
  - feature_exploration モジュールを実装（kabusys.research.feature_exploration）。
    - 将来リターン計算（複数ホライズン、デフォルト [1,5,21]）および IC（Spearman の ρ）計算、ファクター統計サマリを提供。
    - ランク計算は同順位を平均ランクで処理し、浮動小数の丸めで ties 検出漏れを防止。
  - research パッケージの __all__ を整備して主な関数を公開。

- 戦略（特徴量エンジニアリング / シグナル生成）
  - feature_engineering モジュールを実装（kabusys.strategy.feature_engineering）。
    - research の生ファクターを取得してユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB 上の features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクション）して冪等性を担保。
  - signal_generator モジュールを実装（kabusys.strategy.signal_generator）。
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントごとの変換関数（シグモイド・逆転など）を実装し、欠損は中立 0.5 で補完。
    - 重み付け（デフォルト含む）の検証と正規化（合計が 1.0 になるよう再スケール）。
    - Bear レジーム（ai_scores の regime_score 平均 < 0、サンプル最小数チェック）では BUY を抑制。
    - BUY は閾値（デフォルト 0.60）を超えた銘柄に対してランク付け、SELL はポジションに対してストップロス（-8%）・スコア低下で生成。
    - SELL を優先し、signals テーブルへ日付単位の置換で書き込み（冪等）。

- API 安全性・運用性向上
  - ロギングや警告出力を各所に追加（fetch/save のスキップ警告・欠損データ警告・ROLLBACK 失敗警告など）。
  - トークンキャッシュをモジュールレベルで持ち、ページネーション間で再利用（_ID_TOKEN_CACHE）。
  - HTTP 429 の Retry-After ヘッダ尊重と指数バックオフの組合せ実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース XML パースに defusedxml を採用し XML Bomb 等の攻撃を防止。
- news_collector で HTTP/HTTPS 以外のスキームや不正なホストへのアクセスを想定して制限（実装方針として明記）。
- .env 読み込みは OS 環境変数を保護する設計（protected set）により外部環境の上書きを制御。

### Performance
- DuckDB への一括挿入をトランザクションおよび executemany を使ってオーバーヘッドを低減。
- news_collector でバルク INSERT のチャンクサイズを導入。
- J-Quants クライアントに固定間隔レート制御を導入し API レート違反を防止。

### Notes / Known limitations
- 一部の戦略仕様（例: トレーリングストップ、時間決済）は未実装（signal_generator 内コメント参照）。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- feature_engineering・signal_generator は発注層（execution）に依存しない設計。実際の発注連携は別層で実装予定。
- research モジュールは外部依存（pandas 等）を避け、標準ライブラリと DuckDB の SQL により実装。大規模データに対する最適化は運用時に検討が必要。
- news_collector の RSS フィード取得実装（HTTP レスポンスの制限・URL 検証等）は方針とユーティリティを用意。外部ネットワークアクセス周りの厳格な制限（プロキシ設定、タイムアウト、IP ホワイトリスト等）は運用環境で追加検討が必要。

---

この CHANGELOG はソースコードのドキュメンテーション文字列、関数名、定数、および実装コメントに基づいて作成しています。実際のリリースノートに含める項目（例: バグ修正詳細、互換性のあるマイグレーション手順など）は、開発・運用チームの追加情報に応じて更新してください。