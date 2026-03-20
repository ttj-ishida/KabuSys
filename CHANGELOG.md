# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このリポジトリのバージョンは src/kabusys/__init__.py の __version__ に従います。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 初期リリース
リリース日: 未設定

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを導入。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、CWD に依存しない自動 .env ロードを実現。
  - .env のパース実装（コメント対応、export 形式、クォート内のエスケープ処理、行インラインコメントの取り扱い）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 設定検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live 等）。
  - DB パスのデフォルト（duckdb / sqlite）を設定可能。
- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - API レート制御（120 req/min）を固定間隔スロットリングで実装する RateLimiter を導入。
  - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx 系でリトライ、429 の Retry-After を尊重。
  - 401 受信時の自動トークンリフレッシュ（1回）を実装。モジュールレベルで ID トークンをキャッシュ。
  - DuckDB への保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等化。
  - データ型安全化ユーティリティ（_to_float / _to_int）。
  - 取得時の fetched_at を UTC で記録し、Look-ahead バイアスのトレースを可能に。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存するモジュールを追加。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - セキュリティ対策: defusedxml を使用した XML パース、HTTP/HTTPS スキーム制限、受信サイズ上限（10 MB）によるメモリDoS対策、SSRF・XML Bomb への考慮。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性確保。
  - DB へはチャンク化バルクINSERT（チャンクサイズ制限）で保存し、INSERT RETURNING により挿入数を正確に得られる設計。
  - デフォルト RSS ソース定義（例: Yahoo Finance）。
- リサーチユーティリティ (src/kabusys/research/)
  - factor_research: prices_daily / raw_financials を用いたファクター計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日ウィンドウでの乖離）。
    - Volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、volume_ratio。
    - Value: per, roe（最新の報告書を参照）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）および統計サマリー（factor_summary）、rank ユーティリティを実装。
    - calc_forward_returns は複数ホライズン対応（デフォルト [1,5,21]）で、営業日ベースのリードを利用して効率良く取得。
    - calc_ic は Spearman の ρ（ランク相関）を計算、十分なサンプルが無い場合は None を返す。
  - research パッケージの再エクスポート（calc_momentum 等と zscore_normalize）を提供。
- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で生成した raw ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
  - 指定列を Z スコア正規化し ±3 でクリップ、日付単位で冪等（DELETE + bulk INSERT トランザクション）。
  - 欠損や非有限値の扱いを考慮。
- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア（final_score）を算出し signals テーブルに書き込む generate_signals を実装。
  - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を計算するヘルパ関数を実装（シグモイド変換、欠損は中立 0.5 補完）。
  - 重みのマージ・検証と正規化（デフォルト重みを持ち、ユーザ指定は検証後に合計が1になるよう再スケール）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負の場合、サンプル閾値あり）による BUY シグナル抑制。
  - SELL（エグジット）判定ロジックを実装（ストップロス -8% とスコア低下）。保有銘柄の価格欠損時の判定回避、SELL 優先ポリシー。
  - signals テーブルへの日付単位置換（トランザクション＋bulk insert）で冪等を保証。
- その他
  - strategy パッケージのエクスポート（build_features, generate_signals）。
  - research モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみを想定。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 既知の制限 / 未実装 (Notes / Todo)
- signal_generator のエグジットロジックにおいて、トレーリングストップや時間決済（60 営業日超）などは未実装（コメントに記載）。これらは positions テーブルに peak_price / entry_date 等が必要。
- news_collector の一部処理（実際の RSS パース・DB マップ（news_symbols）との紐付けなど）は本ファイルの続き実装が必要（提示コードは一部）。
- data.stats の zscore_normalize の実装は別モジュールに存在（再利用を想定）。（本リリースでは該当ユーティリティを参照して使用している）
- execution パッケージは空の初期プレースホルダ（発注ロジックは別途実装予定）。

### セキュリティ (Security)
- news_collector で defusedxml を採用し XML 関連攻撃（XML Bomb 等）を軽減。
- ニュースの URL 正規化によりトラッキングパラメータを除去、ID の衝突・スプーフィングを軽減。
- RSS 受信サイズ制限（10MB）を導入しメモリ DoS を防止。
- J-Quants クライアントは認証トークン管理と自動リフレッシュを実装し、401 の取り扱いで誤った再帰を防止するため allow_refresh フラグを導入。

---

注: 上記 CHANGELOG はソースコードの実装内容から推測してまとめた初期リリースの概要です。実際のリリース日や API 仕様の変更、追加のモジュール実装などは別途反映してください。