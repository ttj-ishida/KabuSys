# Changelog

すべての重要な変更点はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本CHANGELOGはリポジトリ内のソースコードから機能・設計を推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]
- 開発中の変更点はここに記載します。

## [0.1.0] - 2026-03-17
初回リリース

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージを導入。公開 API: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（配布後も動作）。
  - .env / .env.local の読み込み順序を実装。OS 環境変数は保護（上書き防止）。
  - .env パース機能:
    - コメント・空行無視、export KEY=val 形式対応、クォート内のエスケープ対応、インラインコメントの扱いなど。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DBパス、環境・ログレベル判定など）。
  - env と log_level の入力検証（許容値のチェック）、便宜的プロパティ is_live/is_paper/is_dev。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアント実装。
  - レートリミッタ実装（120 req/min を固定間隔スロットリングで遵守）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - データ保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - DuckDB への保存は冪等化（ON CONFLICT DO UPDATE）して重複を排除。
    - PK 欠損行のスキップと警告ログ出力。
    - fetched_at に UTC タイムスタンプを記録して Look-ahead Bias のトレーサビリティを確保。
  - 数値変換ユーティリティ (_to_float / _to_int) を提供（不正値や空値は None）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news へ保存する機能を実装（DEFAULT_RSS_SOURCES に Yahoo Finance を設定）。
  - セキュリティ対策:
    - defusedxml を用いて XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - リダイレクト時も事前検査するカスタム RedirectHandler を導入。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）を超えるレスポンスは拒否。gzip 解凍後も上限検査。
    - User-Agent / Accept-Encoding を設定して取得。
  - トラッキングパラメータ除去（utm_* 等）と URL 正規化機能。正規化後の SHA-256（先頭32文字）で記事 ID を生成し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS の pubDate を UTC に正規化して格納。パース失敗時は警告を出し現在時刻で代替。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事IDのみを返す。全てを 1 トランザクションで処理（ロールバック対応）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING 1）。チャンク処理とトランザクション対応。
  - 銘柄コード抽出ロジック:
    - 4桁数字パターンから known_codes の集合に含まれるものだけを抽出し重複排除。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution） のテーブル群を定義。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤー: features, ai_scores。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）や適切なデータ型を定義。
  - 頻出クエリ向けのインデックスを作成（コード×日付スキャンやステータス検索を想定）。
  - init_schema(db_path) でディレクトリ自動作成と全テーブル+インデックスを作成（冪等）。get_connection() で既存 DB へ接続できる。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新方式の ETL を実装するための基盤（取得差分計算、バックフィル、品質チェックフック設計）。
  - ETLResult データクラスを導入（取得数 / 保存数 / 品質問題 / エラーの集約、辞書化支援）。
  - 差分取得ユーティリティ（テーブル存在チェック、最大日付取得）。
  - 市場カレンダーに基づく営業日調整ロジック（_adjust_to_trading_day）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date 等のヘルパー。
  - run_prices_etl 実装（差分計算、backfill_days による再取得、fetch と save の呼び出し）。（コードベースの一部で更なる ETL ジョブが続く設計）

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- news_collector において SSRF/内部ネットワークアクセス防止、XML パース時の安全ライブラリ使用、レスポンスサイズ制限、gzip 解凍後の検査など複数の防御策を実装。
- jquants_client の HTTP リトライ制御と認証トークン自動更新ロジックにより不正な再試行や無限ループを回避。

### 互換性に関する注意 (Notes)
- DuckDB スキーマは多くのテーブルと制約を持つため、既存の DB と互換性を保つために init_schema は冪等であるものの、DDL 変更時は運用上のマイグレーション検討が必要です。
- 環境変数の自動ロードはプロジェクトルートの検出に依存します。特殊な配布形態では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化することを推奨します。

---

今後の予定（例）
- ETL の品質チェックモジュール quality の実装と統合。
- strategy / execution / monitoring モジュールの具体的な戦略実装・発注フロー・監視機能の実装。
- テストカバレッジ拡充と CI ワークフローの整備。