# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGは提供されたコードベースの内容から実装・設計方針を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回公開（初期実装）。以下の主要コンポーネントと機能を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）
    - バージョン `0.1.0`
    - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml で特定）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env パース機能（コメント・export 形式・シングル/ダブルクォート・エスケープ対応）
    - 環境変数取得ヘルパ _require と Settings クラス（J-Quants / kabuAPI / Slack / DB パス / env / log level 等）
    - env / log_level のバリデーションと is_live/is_paper/is_dev のユーティリティ

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント（株価日足 / 四半期財務 / マーケットカレンダー）
    - レート制御（_RateLimiter、120 req/min 固定間隔スロットリング）
    - 再試行（指数バックオフ、最大3回、408/429/5xx を対象）
    - 401 応答時の自動トークンリフレッシュ（1 回だけリトライ）
    - ページネーション対応（pagination_key の連結取得）
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
      - 冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE を使用
    - ユーティリティ関数（_to_float / _to_int）で安全な型変換

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と前処理（デフォルトソース: Yahoo Finance ビジネスカテゴリ）
    - セキュリティ／堅牢化
      - defusedxml による XML パース（XML Bomb 等への防御）
      - SSRF 対策（URL スキーム検証、ホストがプライベートアドレスでないか検査、リダイレクト時の検査）
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック
      - HTTP リダイレクト時の事前検査用ハンドラ（_SSRFBlockRedirectHandler）
    - URL 正規化（トラッキングパラメータ（utm_* 等）除去、クエリソート、フラグメント除去）
    - 記事ID生成: 正規化 URL の SHA-256 の先頭 32 文字で冪等性を保証
    - テキスト前処理（URL 除去・空白正規化）
    - DuckDB への保存
      - save_raw_news: チャンク分割してトランザクション単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用（新規挿入IDを正確に返す）
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT 無視、返却は実際に挿入された件数）
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、既知コード集合でフィルタリング（extract_stock_codes）
    - 統合収集ジョブ run_news_collection: 複数ソースを独立して処理、失敗しても他ソースは継続。新規記事に対し銘柄紐付けを一括挿入

- DuckDB スキーマと初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を提供
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与
    - 頻出クエリ向けのインデックス定義
    - init_schema(db_path) でディレクトリ作成・DDL 実行を行い DuckDB 接続を返す
    - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - 差分更新の設計（最終取得日確認 → 必要分のみ取得）
    - backfill_days による再取得（デフォルト 3 日）
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）
    - ETLResult dataclass: 実行結果・品質問題・エラー情報を保持し、辞書化可能
    - テーブル存在チェック・最大日付取得ヘルパ
    - 取引日調整機能（_adjust_to_trading_day）
    - 個別 ETL ジョブ（例: run_prices_etl）: 差分計算、fetch/save 呼び出し、ログ出力
    - 品質チェックモジュール（quality）との連携を想定（コード内で参照）

### Security
- defusedxml を使った XML パースで XML 関連の攻撃に備慮
- RSS フェッチでの SSRF 対策（スキーム検証、プライベートIP/ホスト排除、リダイレクト検査）
- レスポンスサイズ制限と gzip 解凍後のチェックによりメモリDoSを軽減
- .env 読み込み時に OS 環境変数を保護する protected オプションを実装

### Notes / Known limitations
- pipeline.run_prices_etl の戻り値部分など、提供コードの一部が途中で切れている（実装継続が必要な箇所がある可能性あり）。
- strategy/ execution / monitoring パッケージはパッケージ公開用に空の __init__.py が配置されているものの、具体的な戦略・発注・監視ロジックはまだ実装されていない。
- jquants_client の HTTP 実装は urllib を使用しており、非同期処理や高並列処理の対応は未実装（必要に応じて改善の余地あり）。
- quality モジュール参照があるが、実装本文は提供コードに含まれていない。品質チェックの具体的実装は別途必要。

### Breaking Changes
- なし（初回リリース）

---

（以降のリリースでは、各バグ修正・機能追加・破壊的変更を上記フォーマットで追記してください。）