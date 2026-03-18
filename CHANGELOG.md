# CHANGELOG

すべての重要な変更点を追跡します。本ファイルは Keep a Changelog の形式に準拠します。  
初期リリース (v0.1.0) の内容は、リポジトリ内のソースコードから推測して記載しています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 初期リリース
最初の公開バージョン。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成とエクスポート定義（src/kabusys/__init__.py）。バージョンは 0.1.0。

- 設定 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を探索してルートを特定。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される（protected）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント (#) の扱いをサポート。
  - Settings クラスにより必須変数の取得や検証を提供。
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの取得プロパティ。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の既定値処理。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値を定義）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - API 呼び出し共通処理: 固定間隔の RateLimiter（120 req/min を想定）。
    - 再試行ロジック（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対するリトライ。
    - 401 受信時の自動トークンリフレッシュ（1 回）を実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への冪等保存関数:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使用して保存。
      - save_financial_statements: raw_financials テーブルへ保存。
      - save_market_calendar: market_calendar テーブルへ保存（取引日/半日/SQ判定を整形）。
    - 型変換ユーティリティ: _to_float / _to_int（厳密な int 変換ルールを採用）。
    - id_token キャッシュと取得ユーティリティ（get_id_token）。

  - ニュース収集モジュール (news_collector.py)
    - RSS フィードから記事を取得し raw_news / news_symbols に保存する一連の処理を提供。
    - セキュリティ・堅牢性のための実装:
      - defusedxml を利用した XML パース（XML Bomb 対策）。
      - SSRF 対策: URL スキーム検証 (http/https のみ)、リダイレクト時のホスト検査、ホストがプライベート/IP の場合は拒否。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - Content-Length チェックと受信バイト数上限。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、スキーム・ホスト小文字化、クエリソート、フラグメント削除。
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字を使用して冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - 銘柄コード抽出: 4 桁数字の抽出と既知コードセットによるフィルタ（extract_stock_codes）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事 ID を返す。チャンク処理とトランザクションで安全に保存。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク＆トランザクションで保存。

  - DuckDB スキーマ定義 (data/schema.py)
    - Raw レイヤの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義の雛形を含む）。
    - テーブルとカラムの型・制約 (CHECK、PRIMARY KEY) を定義し、データ整合性を保つ設計。

- 研究 (Research) モジュール (src/kabusys/research/)
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 指定日から指定ホライズン（営業日）分の将来リターンを一度のクエリで計算。ホライズンの検証（1〜252）あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装。データ不足・分散ゼロのケースで None を返す。
    - rank: 同順位は平均ランクにするランク付け実装（丸め誤差対策として round(v,12) を使用）。
    - factor_summary: カラム別の count/mean/std/min/max/median を計算する軽量統計ユーティリティ（None 値除外）。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）で、DuckDB の prices_daily を参照する想定。

  - ファクター計算 (factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均との乖離）を計算。必要行数が不足する場合は None を返す。
    - calc_volatility: atr_20（20日 ATR）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均出来高）を計算。true_range の計算は prev_close の存在を正確に扱う。
    - calc_value: raw_financials の最新財務データを結合して PER（EPS が 0 または欠損時は None）と ROE を計算。
    - DuckDB の prices_daily / raw_financials のみ参照し、本番の発注 API 等にはアクセスしない設計。

- パッケージ公開用の __all__（research サブパッケージのエクスポート）に主要関数を追加。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector と RSS フェッチ周りで複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト先検査）。
  - 外部から受け取るリソースのサイズ検査（Gzip/Bomb 対策）。
  - URL のトラッキングパラメータ除去により、外部リンクを扱う際の冗長情報を低減。

### Notes / Design decisions
- Research モジュール内の集計処理は外部ライブラリに依存せず、DuckDB のウィンドウ関数と標準 Python の組合せで実装されています。これにより軽量で配布後の互換性が高く保たれます。
- J-Quants クライアントはレート制限とリトライ・トークン更新を組み合わせて堅牢に API を利用できるよう設計されています。ただし実環境では追加の監視やエラーハンドリングが必要になる場合があります。
- .env パーサは Bash 風の書式を多くサポートしますが、すべての edge-case を網羅することを目的としていないため、極端に複雑な .env 値は注意が必要です。

---

今後のリリースでは、次の点の追加・改善が想定されます（コードからの推測）:
- Feature Layer / Execution Layer の完全実装（戦略モデル・発注処理）。
- より多くのユニットテストと CI の追加。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づくユーザ向けガイドの同梱。

質問や追記してほしい項目があればお知らせください。