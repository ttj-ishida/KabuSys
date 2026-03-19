# Changelog

すべての notable な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
フォーマットは安定しており、将来のリリースで変更点を追跡できます。

---

## [0.1.0] - 2026-03-19

初期リリース（コードベースから推測して作成）。

### 追加 (Added)
- パッケージ基盤
  - パッケージルート: `kabusys` (バージョン 0.1.0) を追加。
  - top-level export: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 環境設定 / config
  - 環境変数・設定読み込みモジュール `kabusys.config` を追加。
    - .env ファイル読み込みの自動化（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は上書き）。  
    - 環境自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - .env のパースは以下に対応:
      - 空行・コメント行（#）の無視
      - `export KEY=val` 形式の対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォート無しの値については `#` の直前が空白・タブならインラインコメントとして除去
    - `Settings` クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどのプロパティを提供。必須キー未設定時は ValueError を投げる。

- データ取得・保存（J-Quants）
  - `kabusys.data.jquants_client` を追加。
    - J-Quants API クライアント実装（取得関数: daily quotes / financial statements / market calendar）。
    - レート制限対策: 固定間隔スロットリングで 120 req/min を順守する RateLimiter。
    - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx をリトライ。429 の場合は `Retry-After` を優先。
    - 401 エラー時の自動トークンリフレッシュを 1 回行いリトライ。
    - モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
    - ページネーション対応（pagination_key を用いたループ）。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE。
      - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
      - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - データ変換ユーティリティ `_to_float` / `_to_int` を用意（安全な型変換）。

- ニュース収集
  - `kabusys.data.news_collector` を追加。
    - RSS フィードの取得・正規化・保存処理（raw_news テーブルへ冪等保存）。
    - URL 正規化機能:
      - スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント除去、クエリパラメータをキーでソート。
    - 記事 ID は URL 正規化後の SHA-256 の先頭（冪等化のため）。
    - セキュリティ対策:
      - defusedxml を使って XML Bomb 等に対処。
      - HTTP/HTTPS 以外のスキームを拒否して SSRF を低減。
      - 最大レスポンスサイズ制限（MAX_RESPONSE_BYTES; デフォルト 10MB）でメモリ DoS を緩和。
    - バルク INSERT のチャンク処理や INSERT RETURNING を想定した設計。

- リサーチ（factor 計算・探索）
  - `kabusys.research.factor_research` を追加。
    - momentum / volatility / value 等の定量ファクター計算:
      - mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）、
      - atr_20 / atr_pct / avg_turnover / volume_ratio（ボラティリティ・流動性）、
      - per / roe（財務データと株価の組み合わせ）。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照する方針。
    - 欠損やデータ不足時の安全な None 処理。
  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン計算（calc_forward_returns、ホライズン指定可、ひとつのクエリで取得）。
    - IC（Information Coefficient, Spearman の rho）計算（rank を内部で実装）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリに依存しない実装（標準ライブラリ + duckdb）。

- 特徴量エンジニアリング
  - `kabusys.strategy.feature_engineering` を追加。
    - research の生ファクターを統合・正規化して `features` テーブルへ UPSERT。
    - ユニバースフィルタ:
      - 最低株価 >= 300 円、20 日平均売買代金 >= 5 億円 を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - 日付単位で削除→挿入する置換（トランザクションで原子性確保）。

- シグナル生成
  - `kabusys.strategy.signal_generator` を追加。
    - features と ai_scores を統合して最終スコア(final_score) を算出し、BUY/SELL シグナルを生成して `signals` テーブルへ保存（冪等）。
    - スコア計算:
      - momentum/value/volatility/liquidity/news の重み付け（デフォルト重みを実装）。ユーザ提供の weights は妥当性検証・フォールバック。
      - Z スコアをシグモイド変換して 0〜1 にマッピング。
      - コンポーネントが None の場合は中立値 0.5 で補完。
    - Bear レジーム検出:
      - ai_scores の regime_score 平均が負で、かつ十分なサンプル数ある場合に Bear と判断し BUY を抑制。
    - エグジット（SELL 条件）:
      - ストップロス（終値 / avg_price - 1 <= -8%）優先判定。
      - final_score が閾値未満で SELL。
      - 一部未実装の判定（トレーリングストップ、時間決済）について注記あり。
    - 日付単位で signals を置換（トランザクションで COMMIT/ROLLBACK を扱う実装）。

- その他
  - `kabusys.data` と `kabusys.research` の __init__ に主要 API を公開（便利な再エクスポート）。
  - ロギングの広範な利用とエラーハンドリング（警告・例外の明示的処理）を全体で採用。
  - DuckDB を中心としたデータパイプライン設計（SQL + Python の組合せで計算・集計）。

### 変更 (Changed)
- 初版のため、変更履歴はなし（初期追加のみ）。

### 修正 (Fixed)
- 初版のため、修正履歴はなし。

### セキュリティ (Security)
- news_collector で defusedxml を使用、レスポンスサイズ制限、URL 正規化とスキーム制限により XML/SSRF/DoS のリスク低減を図っている点を明記。

---

注: 上記の CHANGELOG は提示されたソースコードの内容から推測して作成した初期リリースノートです。実際のリリース日やバージョン付け、追加での変更・修正がある場合は適宜更新してください。