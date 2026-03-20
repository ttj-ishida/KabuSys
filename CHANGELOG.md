# CHANGELOG

すべてのスコアは Keep a Changelog の形式に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測した主な追加点・設計方針・安全対策などの要約です。

### Added
- パッケージ基礎
  - パッケージ初期化（kabusys.__init__）およびバージョン管理（__version__ = "0.1.0"）。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数からの設定自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に検出するため、CWD に依存しない挙動。
  - .env パーサを独自実装（export 形式、クォート値、エスケープ、インラインコメント処理に対応）。
  - .env.local を使った上書き（override）機構と、OS 環境変数を保護する protected キーセット。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - 必須環境変数取得用の _require、設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL）、便宜プロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得。
    - ページネーション対応。
    - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。429 時は Retry-After ヘッダを優先。
    - 401 受信時はトークン（id_token）を自動リフレッシュして 1 回リトライ。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスを低減。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
    - 入力変換ユーティリティ（_to_float / _to_int）で不正値・空値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース取得基礎を実装（デフォルトソースに Yahoo Finance を含む）。
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ上限（10MB）、HTTP(S) スキームの厳格チェック、SSRF 対策の基本方針（IP 判定やソケット制限を想定する実装方針）。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）と記事 ID を SHA-256 ハッシュで生成して冪等性を確保。
  - DB 保存はトランザクション単位のバルク挿入、チャンク処理を想定。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算群を提供（factor_research: calc_momentum / calc_volatility / calc_value）。
    - Momentum: 約1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: 直近の raw_financials から EPS/ROE を参照して PER/ROE を計算（PER は EPS=0 や欠損で None）。
  - 研究用ユーティリティ（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）対応、SQL で効率的に取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランク）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）。
    - rank ユーティリティ: 同順位を平均ランクで処理、浮動小数丸めで ties 対策。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究モジュールで計算した raw ファクターを統合・正規化し features テーブルへ UPSERT（日付単位の置換）する処理を実装。
  - ユニバースフィルタ（price >= 300 円、20日平均売買代金 >= 5 億円）適用。
  - 正規化は zscore_normalize（kabusys.data.stats から提供）を使用、Z スコアを ±3 でクリップして外れ値影響を抑制。
  - ルックアヘッドバイアス防止のため target_date 時点のみのデータを使用。トランザクションで原子性を確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し signals テーブルへ書き込む処理を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算し、重み付き合算（デフォルト重みを提供）。重みは外部から上書き可能で妥当性検査および再スケーリングを行う。
  - AI レジーム集計による Bear 判定（サンプル閾値あり）。Bear レジーム時は BUY シグナルを抑制。
  - SELL シグナル（エグジット）判定:
    - ストップロス（終値/avg_price - 1 < -8%）
    - final_score の閾値未満によるクローズ
    - 保有銘柄に価格が取得できない場合は判定をスキップして誤クローズを防止
    - 一部条件（トレーリングストップ、時間決済）は未実装で将来拡張を想定
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。
  - weights の不正値（非数値、NaN/Inf、負値、未知キー）は無視して警告を出す。

### Security
- 外部データ処理におけるセキュリティ対策を明記・実装（defusedxml の使用、HTTP(S) のみ許可、受信サイズ制限、.env パース時の警告等）。
- 認証トークンキャッシュおよび自動リフレッシュの実装は、無限再帰を防ぐため allow_refresh フラグやリフレッシュ回数制御を導入。

### Documentation / Design Notes
- 多数のモジュールで設計方針・処理フロー・SQL の説明コメントを充実させ、ルックアヘッドバイアス対策や冪等性などトレードオフに関する注記を残しています（運用・レビューに有用）。
- DuckDB を主要なストレージとして想定し、SQL ウィンドウ関数等を活用してパフォーマンスと正確性を両立する実装方針。

### Known limitations / TODO
- news_collector の一部処理（実際の RSS 取得ループや DB 挿入の詳細）はファイル切れによりトレースを途中で停止していますが、設計は安全性と冪等性を念頭に置いています。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブル側の情報（peak_price / entry_date 等）を必要とするため未実装。将来的な positions スキーマ拡張で実装予定。
- 一部機能（外部 API のエラーケースの追加ハンドリング、詳細な監視/メトリクス）は今後の改善余地あり。

---

（注）上記 CHANGELOG は提供されたコード内容をもとに推測して作成した要約です。実際のリリースノートとして用いる場合は、テスト結果やリリース手順、正確な日付・関係者情報を追記してください。