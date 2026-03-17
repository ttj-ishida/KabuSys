# CHANGELOG

このプロジェクトは Keep a Changelog の慣習に従って変更履歴を管理します。  
フォーマット: https://keepachangelog.com/（日本語）

注: 以下の記載はリポジトリ内のコードから推測して作成した初期リリース概要です。

## [Unreleased]

## [0.1.0] - 初期リリース
最初の実装リリース。日本株自動売買基盤（データ取得、保存、ニュース収集、スキーマ定義、設定管理、簡易ETL）の主要コンポーネントを追加。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名と公開モジュール一覧（data, strategy, execution, monitoring）を定義。
    - バージョン情報 (__version__ = "0.1.0") を設定。

- 環境設定と自動 .env ロード
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準に探索）。
    - .env パースの詳細実装（コメント・export プレフィックス・クォート・エスケープなどに対応）。
    - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
    - Settings クラスを提供し、J-Quants、kabuステーション、Slack、DB パス、実行環境（development/paper_trading/live）、ログレベル等のプロパティを取得可能に。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制御（120 req/min）を行う固定間隔スロットリング RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx の再試行）を実装。
    - 401 Unauthorized を検出した場合のリフレッシュトークンによる自動再取得（1回のみ）を実装。
    - get_id_token() による ID トークン取得（POST）実装。
    - ページネーション対応での fetch_daily_quotes、fetch_financial_statements を実装。
    - market_calendar（JPX マーケットカレンダー）取得関数を実装。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT DO UPDATE による重複回避）。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録して Look-ahead バイアスのトレーサビリティを確保。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正な値に耐性を持たせる。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得して raw_news に保存する機能を実装。
    - defusedxml を使用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカルでないことをチェック（直接 IP と DNS 解決の両方を検査）。
      - リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES＝10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）を実装、記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - テキスト前処理（URL除去・空白正規化）。
    - fetch_rss()、save_raw_news()（INSERT ... RETURNING で実際に挿入された ID を返す）、save_news_symbols()、_bulk 保存関数を実装。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes に基づくフィルタ）を実装。
    - run_news_collection() により複数 RSS ソースの収集を統合し、ソース毎に独立したエラーハンドリングを実施。

- データベーススキーマ（DuckDB）定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL を定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を付与。
    - 頻出クエリ向けのインデックスを定義。
    - init_schema(db_path) でディレクトリ作成 → 接続 → テーブル/インデックス作成を行う（冪等）。
    - get_connection(db_path) を提供。

- ETL パイプラインの基礎
  - src/kabusys/data/pipeline.py
    - ETL のフロー設計（差分更新、保存、品質チェック）を組み込んだモジュール骨格を実装。
    - ETLResult データクラスで ETL 実行結果・品質問題・エラー一覧を表現。
    - テーブル存在確認・最大日付取得などのユーティリティ関数を実装。
    - 市場カレンダーに基づく営業日調整ロジック（_adjust_to_trading_day）を実装。
    - 差分更新用のヘルパー関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
    - run_prices_etl()（差分取得 → 保存 → ログ）の実装（backfill_days による再取得処理をサポート）。※ファイル末尾は実装の断片で終わっているため、一部実装が継続する想定。

### 変更 (Changed)
- なし（初回リリースのため過去変更は無し）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- ニュース収集での SSRF 対策、XML パースの防御（defusedxml 使用）、レスポンスサイズ制限（メモリ DoS/Gzip bomb 対策）を明示的に実装。

### 既知の制限 / 注意点 (Known issues / Notes)
- pipeline.run_prices_etl のファイル末尾が途中で終わっているように見える（提示されたコードの範囲内では戻り値のタプルが不完全）。完全な ETL シーケンス（quality モジュール連携、他ジョブの統合）は引き続き実装・確認が必要。
- settings の必須環境変数未設定時は ValueError を送出するため、実運用環境では .env の整備または環境変数の注入が必須。
- DuckDB に対する SQL 実行は文字列連結箇所が存在するため（例: f-string でテーブル名など）、外部からの不正入力をそのまま渡さないよう呼び出し側で注意が必要（現状は内部用途を想定）。
- ニュース抽出の銘柄コード検出は 4 桁数字パターンに依存しているため、その他形式の識別子には対応していない。

---

今後の予定（例）
- pipeline の完全実装（品質チェック結果の扱い、財務データ・カレンダー ETL の実装完了）。
- execution 層（kabuステーション連携、注文管理、約定取り込み）および strategy・monitoring モジュールの具体実装。
- 単体テスト・統合テストの整備（ネットワーク I/O のモック化、DB の一時環境でのテスト）。
- ドキュメント（DataPlatform.md、API 使用例、運用手順）の追加。

---

（以上）