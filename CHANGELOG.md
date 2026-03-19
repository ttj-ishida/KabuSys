# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。  

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期バージョンを追加（kabusys 0.1.0）。
  - package version は src/kabusys/__init__.py の __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動ロード（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出は .git または pyproject.toml を親ディレクトリから探索して判定（カレントワーキングディレクトリに依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途向け）。
  - .env のパース機能:
    - コメント行・空行を無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース。
    - クォート無し値のインラインコメント処理（直前が空白/タブの場合のみ）。
  - 必須設定の取得ヘルパー `_require` を提供（未設定時は ValueError を送出）。
  - Settings クラスにより以下の設定プロパティを提供:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
    - 環境判定: KABUSYS_ENV（development/paper_trading/live の検証）
    - ログレベル検証（LOG_LEVEL が有効な値か検証）

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API レート制限制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter を搭載。
    - 冪等性・耐障害性を考慮した HTTP 呼び出しユーティリティ:
      - 最大リトライ回数（3 回）、指数バックオフ、408/429/5xx に対するリトライ処理。
      - 401 はトークン自動リフレッシュ処理を行い 1 回リトライ（無限再帰防止フラグあり）。
      - ページネーション対応（pagination_key を用いたループ取得）。
    - データ取得関数:
      - fetch_daily_quotes（OHLCV 取得）
      - fetch_financial_statements（財務データ取得）
      - fetch_market_calendar（JPX カレンダー取得）
    - DuckDB への保存関数（冪等保存、ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes -> raw_prices テーブル
      - save_financial_statements -> raw_financials テーブル
      - save_market_calendar -> market_calendar テーブル
    - 型安全な変換ユーティリティ `_to_float`, `_to_int` を提供。

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードから記事を収集し raw_news に保存する処理の基礎を実装。
    - 設計上の安全対策:
      - defusedxml を用いた XML パース（XML Bomb 等の対策）。
      - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
      - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）削除、フラグメント除去、クエリキーソート。
      - 記事ID は正規化された URL の SHA-256 ハッシュ（先頭 32 文字）で生成する方針（冪等性確保）。
      - デフォルト RSS ソース（Yahoo Finance のカテゴリ RSS）を定義。
    - バルク保存のチャンクサイズと SQL 上の最適化（チャンク単位挿入）を想定。

- Research 層（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ、バリュー（per/roe）などを DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装:
      - calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
      - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
      - calc_value（per, roe）
    - 日付スキャンやウィンドウのバッファ（カレンダー日での余裕）を考慮した実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、factor_summary、rank（同順位は平均ランク）を実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。
  - zscore_normalize はデータ層のユーティリティを利用する前提で統合（kabusys.research.__init__ にエクスポート）。

- Strategy 層（kabusys.strategy）
  - 特徴量生成（kabusys.strategy.feature_engineering）
    - research モジュールで計算された生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定列の Z スコア正規化（対象列: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を行い ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）して冪等性・原子性を保証（トランザクション使用）。
    - 価格取得は target_date 以前の最新価格を参照し、休場日/当日欠損に対応。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存（DELETE + INSERT の日付単位置換で冪等）。
    - デフォルトの重みと閾値:
      - 重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - BUY 閾値: 0.60
      - ストップロス: -8%（SELL 判定）
      - Bear レジーム判定: ai_scores の regime_score の平均が負の場合（サンプル数閾値あり）
    - 重みはユーザ指定でフォールバック・検証・再スケールされる（不正値は無視）。
    - 欠損コンポーネントは中立値 0.5 で補完して過度な降格を防止。
    - SELL シグナル（エグジット）は positions と直近価格を参照して判定。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - BUY と SELL の競合処理: SELL 対象銘柄は BUY リストから除外し、ランクを再付与（SELL 優先ポリシー）。

- 共通設計・実装上の配慮
  - ルックアヘッドバイアス防止: すべての集計は target_date 時点でアクセス可能なデータのみを用いる設計方針を明記。
  - DuckDB を用いたローカル分析基盤を前提に、SQL と Python を組み合わせた実装。
  - 発注 API（execution 層）への直接依存を排除（strategy 層は signals テーブルへの書き込みまで）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- news_collector で defusedxml を使用し、XML パース時の安全性を考慮。
- news_collector の URL 正規化とトラッキングパラメータ除去により、潜在的な情報漏洩や冪等性の問題を軽減。

### Known issues / TODOs
- signal_generator の SELL 判定に関して、コメントで言及されている以下の条件は未実装（positions テーブルに peak_price / entry_date が必要）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- news_collector のコメントには「INSERT RETURNING で挿入数を返す」とあるが、実装はチャンク挿入を前提としており、DB 側の実装に依存する点があるため挙動の確認が必要。
- features 側で per（PER）は正規化対象外（inverse スコア変換の必要性がある）であることに注意。
- 一部の処理は DuckDB 上のテーブル構成（列名・インデックス・制約）に依存するため、初期スキーマの準備が必要。
- 外部ネットワーク呼び出し周り（J-Quants API）のテストはネットワーク/認証情報に依存するため、KABUSYS_DISABLE_AUTO_ENV_LOAD 等を使った分離テストの整備が推奨される。

---

参照: 各モジュール内の docstring とログ出力メッセージに実装方針・振る舞いの詳細を記載。詳細実装やテーブル定義はソースコード（src/kabusys/**）を参照してください。