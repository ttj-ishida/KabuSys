# CHANGELOG

すべての変更は「Keep a Changelog」形式に従います。  
このプロジェクトの最初の公開バージョンを記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージの初期リリースを追加。
  - パッケージメタ: kabusys/__init__.py（バージョン 0.1.0、公開エクスポート: data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォートのエスケープ、行末コメント処理などに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 環境変数取得ユーティリティ Settings を実装（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル等）。
  - 値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性チェック。
  - duckdb/sqlite の既定パス設定（expanduser 対応）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - v1 API 向けの取得・保存ユーティリティを実装。
  - 機能:
    - ID トークン取得（refresh token 経由）
    - 日次株価（fetch_daily_quotes）・財務データ（fetch_financial_statements）・市場カレンダー（fetch_market_calendar）のページネーション対応取得
    - DuckDB へ冪等的に保存する関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - 実装上の特徴:
    - 固定間隔スロットリングによるレート制御（120 req/min の遵守）
    - リトライ（指数バックオフ、最大3回、408/429/5xx 対応）
    - 401 受信時はトークン自動リフレッシュ（1 回のみ）してリトライ
    - fetched_at を UTC で記録し Look-ahead Bias を追跡可能に
    - 入力の型変換ユーティリティ（_to_float / _to_int）を提供

- ファクター計算（研究用）（src/kabusys/research/factor_research.py）
  - Momentum / Volatility / Value の各ファクター計算を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離率）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR・出来高系）
    - calc_value: per, roe（raw_financials の最新レコードを使用）
  - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計（外部 API にはアクセスしない）。
  - スキャン範囲や欠損時の None 戻りなど、実運用を想定した扱いを実装。

- 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
  - 将来リターン計算: calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト）
  - IC 計算: calc_ic（Spearman のランク相関（ρ）を実装、データ不足時は None）
  - ランク付けユーティリティ: rank（同順位は平均ランク、浮動小数丸め対応）
  - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median を算出）
  - 設計方針として DuckDB の prices_daily テーブルのみ参照し、本番 API に依存しないことを明記。

- research パッケージのエクスポート（src/kabusys/research/__init__.py）
  - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank を公開。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に保存する一連の処理を実装。
  - 主な機能・設計:
    - RSS 取得（fetch_rss）: defusedxml を用いた安全な XML パース、gzip 解凍対応、Content-Length / 最大受信バイト数チェック（デフォルト 10MB）
    - SSRF 対策: URL スキームチェック（http/https のみ）、リダイレクト先の事前検証、ホストがプライベート/ループバック/リンクローカルの場合は拒否
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を保証
    - テキスト前処理（URL除去・空白正規化）
    - DB 保存: save_raw_news（チャンク挿入、1 トランザクション、INSERT ... RETURNING による実際挿入 ID 取得）、news_symbols のバルク保存
    - 銘柄コード抽出（4桁数字）と既知銘柄フィルタリング（extract_stock_codes）
    - 総合収集ジョブ run_news_collection（ソース単位で独立してエラーハンドリング）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw layer の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions のテーブル定義を含む）。
  - 各テーブルに PRIMARY KEY / CHECK 制約や fetched_at デフォルトを設定しデータ整合性を確保。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector において複数の SSRF/Malicious XML 対策を導入:
  - defusedxml を用いた XML パース
  - リダイレクト時のスキーム/ホスト検証（_SSRFBlockRedirectHandler）
  - プライベート IP/ホスト判定（_is_private_host）による内部アドレスアクセス禁止
  - レスポンスサイズ上限と gzip 解凍後の再検査（Gzip bomb 対策）
  - URL スキームの厳格チェック（http/https のみ）
- API クライアントでの認証トークン取り扱い:
  - トークン自動更新の実装により 401 時のリカバリを行うが、再試行制御により無限ループを回避。

### 既知の制約 / 今後の課題
- research モジュールは標準ライブラリのみで実装しており、大規模データ処理の最適化（pandas 等の採用）は未検討。
- calc_value では PBR・配当利回りは未実装（注記あり）。
- schema.py の Execution 層などの定義（ファイル末尾の raw_executions 定義は途中まで）について、将来的な拡張が必要。
- jquants_client の RateLimiter は固定間隔スロットリング方式。より柔軟なバースト処理・トークンバケットが必要になり得る。

---

その他、コード中に豊富なログ出力・警告処理・例外メッセージを配置しており、運用時のトラブルシュートを容易にする設計になっています。