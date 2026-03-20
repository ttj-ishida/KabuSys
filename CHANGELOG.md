# Changelog

すべての重要な変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

全般的な方針:
- バージョンごとに「Added / Changed / Fixed / Security / Notes」等のセクションを用意しています。
- 本リリースはパッケージ内部の実装に基づき推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ骨格
  - pakage 名称: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py にて定義)
  - エクスポート: data, strategy, execution, monitoring をトップレベルで公開

- 環境設定読み込み / 設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - .env の行パーサ実装:
    - 空行・コメント行対応、export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし時のインラインコメント判定（# 前が空白・タブの場合のみ）
  - .env 読み込み時の上書き制御（.env は上書きせず、.env.local は上書き）と OS 環境変数保護機構（protected set）
  - Settings クラスによる型付きプロパティ提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須チェック
    - KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の利便性プロパティ

- データ収集クライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース処理（_request）:
    - 固定間隔のレート制限実装（120 req/min 相当）
    - リトライ処理（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 Unauthorized を検知した場合のリフレッシュトークン自動更新（1 回だけ）と再試行
    - ページネーション対応（pagination_key）
    - JSON デコード失敗時の詳細エラー
  - トークン処理:
    - get_id_token(refresh_token=None) によるリフレッシュトークン経由の ID トークン取得
    - モジュールレベルの ID トークンキャッシュ（ページネーション間共有）
  - データ取得関数:
    - fetch_daily_quotes (OHLCV, pagination)
    - fetch_financial_statements (四半期データ, pagination)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB 保存関数（冪等性）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 多数の変換ユーティリティ（_to_float, _to_int）で型安全にパース

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集パイプライン（既定ソースに Yahoo Finance を追加）
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - HTTP/HTTPS 以外のスキーム拒否、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）
    - SSRF 周りの基本対策（IP 検査やソケットレベルチェックを想定した実装方針）
  - URL 正規化:
    - トラッキングパラメータ（utm_* 等）除去、クエリのソート、小文字化、フラグメント除去
    - 正規化した URL の SHA-256 ハッシュ（先頭 32 文字）を記事IDとして冪等性保証
  - テキスト前処理（URL 除去、空白正規化）、バルク挿入時のチャンク処理（_INSERT_CHUNK_SIZE）

- リサーチモジュール (src/kabusys/research/*.py)
  - calc_momentum, calc_volatility, calc_value
    - prices_daily / raw_financials を用いたファクター計算実装
    - Mom (1M/3M/6M) / MA200 乖離 / ATR20 / atr_pct / avg_turnover / volume_ratio / per / roe 等
    - スキャン範囲のバッファや欠損時の None 処理
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターン計算（1/5/21 日がデフォルト）
    - calc_ic: スピアマンのランク相関（ランク同順は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランク、浮動小数誤差対策として round(..., 12) を使用
  - これらは外部依存（pandas 等）を使用せず標準ライブラリ + duckdb による実装方針

- 戦略モジュール (src/kabusys/strategy/*.py)
  - feature_engineering.build_features
    - research の calc_* を呼び出して生ファクターを結合
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）
    - Z スコアを ±3 でクリップして外れ値影響を抑制
    - DuckDB への日付単位の置換（DELETE → INSERT、トランザクションで原子性確保）
  - signal_generator.generate_signals
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - デフォルト重み・閾値を採用（weights の補完・正規化処理あり）
    - AI レジームスコアの平均により Bear 判定（サンプル数閾値あり）
    - Bear レジーム時は BUY シグナルを抑制
    - BUY: final_score >= threshold、SELL: ストップロス（-8%）またはスコア低下（threshold 未満）
    - positions / prices_daily を参照して EXIT 条件判定
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）
    - 未登録コンポーネントは中立値 0.5 で補完することで欠損銘柄の不当な降格を防止

### Security
- XML パースに defusedxml を採用（news_collector）
- ニュース受信サイズ制限（10 MB）でメモリ DoS の緩和
- J-Quants クライアント:
  - レート制限（120 req/min）に従う実装
  - リトライ・バックオフ、429 の Retry-After ヘッダ尊重
  - 401 時のトークンリフレッシュで認証フローの安全性を維持
- .env ローダーは OS 環境変数を保護する protected set をサポート（テストや CI で安全に使える）

### Notes / Known limitations / TODO
- signal_generator の一部エグジット条件は未実装:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加が必要
- 内部で参照するユーティリティ（例: kabusys.data.stats.zscore_normalize）は別モジュールで提供される前提
- DuckDB のスキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本パッケージ外で用意される前提
- 一部ネットワーク/IO 操作は同期実装（urllib）であり、高スループット用途では非同期実装の検討余地あり

### Dependencies（注）
- duckdb
- defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等

---

この CHANGELOG は、提供されたコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は、リリース日時、著者、変更理由（issue/PR 番号）などを追加することを推奨します。