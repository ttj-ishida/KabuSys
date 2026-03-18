# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

なお、本 CHANGELOG はソースコードから機能・目的を推測して作成しています（実装内容を要約）。

## [Unreleased]

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期リリース: kabusys の基本モジュール群を追加
  - src/kabusys/__init__.py によりパッケージを公開（data, strategy, execution, monitoring を __all__ に設定）。
  - バージョン 0.1.0 を設定。

- 設定・環境変数管理 (`src/kabusys/config.py`)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト時に便利）。
  - .env パースロジックを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行末コメント扱いなど）。
  - Settings クラスで必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして取得。
  - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）とログレベル検証を実装。
  - DB ファイルパスのデフォルト（duckdb/sqllite）プロパティを追加。

- データ層（DuckDB）周り
  - スキーマ定義モジュールを追加（src/kabusys/data/schema.py）
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル DDL を定義。
    - Raw / Processed / Feature / Execution の層構造に合わせた設計意図を明記。

- J-Quants API クライアント (`src/kabusys/data/jquants_client.py`)
  - API 呼び出しユーティリティ (_request) を実装。
    - 固定間隔のレート制御（120 req/min）を実装する RateLimiter を導入。
    - 再試行ロジック（指数バックオフ、最大試行回数、特定ステータス 408/429/5xx のリトライ対象化）。
    - 401 受信時にリフレッシュトークン経由で id_token を自動更新して再試行（1 回のみ）。
    - ページネーション対応（pagination_key を使ったループ取得）とモジュールレベルの id_token キャッシュ。
  - データ取得関数を実装:
    - fetch_daily_quotes: 日足（OHLCV）取得
    - fetch_financial_statements: 財務四半期データ取得
    - fetch_market_calendar: JPX カレンダー取得
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いた更新で冪等性を確保
  - 入出力ユーティリティ: _to_float / _to_int を実装し堅牢な型変換を提供。

- ニュース収集モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィード取得と前処理パイプラインを実装:
    - fetch_rss: RSS 取得・XML パース・記事抽出（defusedxml に基づく安全なパース）。
    - preprocess_text: URL 除去、空白正規化。
    - URL 正規化と記事 ID 生成（_normalize_url / _make_article_id: SHA-256 の先頭32文字）。
    - SSRF 対策: スキーム検証、ホストのプライベートアドレス判定（_is_private_host）、リダイレクト検査用ハンドラ。
    - レスポンス上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズ検査などメモリ DoS 対策。
    - トラッキングパラメータ除去（utm_* 等）。
  - DB 保存関数:
    - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入と単一トランザクションによる保存（ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複排除・チャンク挿入）。
  - 銘柄コード抽出ロジック:
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出し known_codes でフィルタ（重複除去）。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースを巡回して記事取得→保存→銘柄紐付けを実行。ソース単位でエラーハンドリングして継続実行。

- リサーチ / ファクター計算モジュール（src/kabusys/research）
  - feature_exploration.py:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）先までの将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（ties の平均ランク処理を含む）。
    - rank: 値リストを平均ランクに変換（丸めによる ties 検出対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - いずれも DuckDB の prices_daily テーブルのみ参照し、本番取引 API にはアクセスしない設計（Research 環境向け）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離（ma200_dev）を計算（ウィンドウサイズとスキャンバッファを考慮）。
    - calc_volatility: ATR20、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播を厳密に制御）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（report_date <= target_date の最新財務データを利用）。
    - すべて DuckDB 経由で完結する実装。結果は (date, code) をキーとした dict のリストで返却。
  - research パッケージ __all__ に主要関数を公開（zscore_normalize は kabusys.data.stats からインポートして公開）。

### Security
- RSS パーサに defusedxml を使用して XML-based 攻撃を軽減。
- fetch_rss 実装で SSRF 対策:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査（DNS 解決を行い複数 A/AAAA レコードをチェック）。
  - リダイレクト先の再検証用カスタムハンドラを導入。
- HTTP 取得で Content-Length / 実読み込みサイズ上限を設け、Gzip ボム対策を実施。
- J-Quants クライアントで 401 発生時のトークン自動リフレッシュは 1 回のみ行い、無限再帰を回避。

### Performance / Reliability
- J-Quants クライアント:
  - 固定間隔のスロットリング（120 req/min）でレート制限に準拠。
  - ページネーション処理と id_token キャッシュにより効率的な取得を実現。
  - 再試行（指数バックオフ、Retry-After 優先）で一時的なネットワーク障害に耐性を持たせる。
- news_collector:
  - チャンク挿入（_INSERT_CHUNK_SIZE）と単一トランザクション／INSERT RETURNING により DB 書き込みオーバーヘッドを削減。
  - 重複除去ロジックで不要な重複挿入を防止。
- research モジュールは SQL ウィンドウ関数を多用して DuckDB 上で効率的に集計。

### Notes / Other
- 研究系関数（factor_research, feature_exploration）は本番発注や外部 API にアクセスしないことを明記（安全性・再現性重視）。
- 外部依存は最小限（duckdb, defusedxml）。pandas 等の高レベルライブラリに依存しない設計。
- 環境変数の必須チェックは Settings._require にて ValueError を投げるため、実行前に環境設定ミスを早期に検出可能。

### Breaking Changes
- 初版リリースのため特になし。

---

開発上の注記:
- この CHANGELOG はソースコードの実装内容をもとに作成しています。リリースノートとして配布する際は、実際のリリース日付やバージョニングポリシーに合わせて調整してください。必要であれば英語版やより詳細なファイル別の変更点一覧も作成できます。