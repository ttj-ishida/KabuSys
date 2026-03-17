# Changelog

全ての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
バージョン番号は Semantic Versioning に従います。

## [Unreleased]

（今後の変更をここに記載）

## [0.1.0] - 2026-03-17

初回リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定：.git または pyproject.toml）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env / .env.local の読み込み順序と上書きルール（OS 環境変数は保護）
  - .env パーサ: export 形式やクォート、インラインコメント等に対応
  - 必須変数取得ヘルパー _require()
  - Settings クラスを公開（プロパティ例）
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env (development/paper_trading/live の検証), log_level（検証）、is_live / is_paper / is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）
  - リトライ戦略: 指数バックオフ（最大3回）、HTTP 408/429/5xx を対象
  - 401 発生時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライ
  - id_token のモジュールキャッシュ（ページネーション間で共有）
  - Look-ahead bias 防止のため取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ (_to_float / _to_int)

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を取得・前処理・保存する一連処理を実装
  - デフォルト RSS ソース（Yahoo Finance のカテゴリ RSS）を定義
  - 安全設計
    - defusedxml を使用して XML Bomb 等に対策
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートIP/ループバック判定、新しいリダイレクト先の検証（_SSRFBlockRedirectHandler）
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査
    - トラッキングパラメータ除去（utm_*, fbclid 等）および URL 正規化
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
  - テキスト前処理: URL 除去、空白正規化
  - DuckDB への保存関数
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク単位で実行し、実際に挿入された記事IDを返却（トランザクションでコミット/ロールバック）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複排除、RETURNING で挿入数を正確に返す）
  - 銘柄コード抽出 (extract_stock_codes): 本文から 4 桁銘柄コードを抽出し、与えられた known_codes のみに限定して重複除去して返す
  - 統合ジョブ run_news_collection: 複数ソースを独立に扱い、個別エラーを他ソースに影響させない

- スキーマ管理 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - 主要テーブルを網羅的に定義（例: raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）
  - 制約・CHECK を用いたデータ品質担保（例: volume >= 0, side IN ('buy','sell') など）
  - インデックス定義（頻出クエリに対する最適化）
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等）
  - get_connection(db_path) による既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL ヘルパー群とジョブ
  - 最終取得日の検出ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）
  - 市場カレンダーを参照して非営業日を直近営業日に調整するヘルパー (_adjust_to_trading_day)
  - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days をデフォルトで遡って再取得し API の後出し修正を吸収）
  - ETLResult データクラス: 実行結果、品質問題、エラー一覧を集約して返却。quality モジュールとの連携を想定
  - 設計上の方針を反映（差分更新、バックフィル、品質チェックは Fail-Fast としない）

### 変更 (Changed)
- 初期リリースのためなし

### 修正 (Fixed)
- 初期リリースのためなし

### セキュリティ (Security)
- RSS パーシングに defusedxml を利用し XML 関連攻撃の緩和を実装
- RSS フェッチ時に SSRF 対策を導入（スキーム/ホスト検査、リダイレクト検査、プライベートアドレス拒否）
- HTTP 応答の最大サイズと Gzip 解凍後のサイズチェックを追加してメモリ DoS を低減

### 既知の制限・注意点 (Known issues / Notes)
- quality モジュールは pipeline から参照される設計になっているが、詳細チェックの実装状況に応じて ETL の挙動が変わります（ETL は品質エラーを収集して呼び出し元に報告する設計）。
- get_id_token は settings.jquants_refresh_token に依存するため、本番実行前に環境変数の設定が必要（_require により未設定時は ValueError を送出）。
- run_prices_etl の戻り値は現在までの実装により (fetched_count, saved_count) となる想定ですが、呼び出し側での扱いに注意してください（将来的に ETLResult を返すなど拡張する可能性あり）。

### 破壊的変更 (Breaking Changes)
- 初回リリースのためなし

---

（今後のリリースでは機能追加・修正・互換性の変更をこのファイルに追記します。）