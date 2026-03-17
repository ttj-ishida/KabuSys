CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
- パッケージメタ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポートモジュール: data, strategy, execution, monitoring
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export KEY=val 形式やクォート・インラインコメントの取り扱いに対応した .env パーサー実装。
  - 必須環境変数取得時に明確なエラーメッセージを返す _require を提供。
  - 環境（development / paper_trading / live）とログレベルの検証ロジックを実装。
  - DB パス（DuckDB / SQLite）などの型安全なプロパティを提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得をサポート。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - リトライ戦略（指数バックオフ、最大3回、408/429/5xx 対象）。
  - 401 発生時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有機能。
  - ページネーション対応の取得関数（fetch_* 系）。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装し、fetched_at を UTC で記録。
  - 型安全な変換ユーティリティ (_to_float / _to_int) を提供。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得・記事抽出パイプラインを実装。
  - デフォルト RSS ソース（Yahoo Finance）を定義。
  - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント削除）、SHA-256 ベースの記事ID生成（先頭32文字）を実装し冪等性を保証。
  - XML パースに defusedxml を利用し XMLBomb 等の攻撃耐性を確保。
  - SSRF 対策:
    - fetch 前にホストのプライベートIP判定。
    - リダイレクト時にスキーム/ホスト検査を行う専用ハンドラ(_SSRFBlockRedirectHandler) を使用。
    - http/https 以外のスキームを拒否。
  - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再検査を実装（メモリ DoS 対策）。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（UTC 変換、失敗時は代替時刻）。
  - DuckDB への保存:
    - raw_news に対するチャンク化したバルク INSERT + RETURNING（挿入された新規 ID を返す）。
    - news_symbols（記事 — 銘柄紐付け）をトランザクションで一括挿入。重複除去・チャンク化を実施。
  - 銘柄コード抽出ロジック（4桁数字候補を known_codes でフィルタリング）。
  - 集約ジョブ run_news_collection を提供し、各ソースごとに独立したエラーハンドリングを行う。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに対するチェック制約（NOT NULL / CHECK）や主キー、外部キーを定義。
  - 頻出クエリに対するインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→DDL実行→インデックス作成を行い、冪等的に初期化を行う。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新（差分取得）を前提とした ETL フローの基礎実装。
  - ETLResult データクラスによる実行結果集約（品質問題・エラー情報を含む）。
  - DB の最終取得日を調べるユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 営業日調整ヘルパー（_adjust_to_trading_day）とバックフィル（backfill_days）実装方針。
  - run_prices_etl の骨組み（差分算出、fetch → save の呼び出し、ログ出力）を実装。
- その他
  - 各種ログ出力（info/warning/exception）を適所に実装し、運用時の観察性を確保。
  - テスト容易性を考慮した設計（id_token 注入、_urlopen の差し替えやモック化を想定）。

Security
- RSS/HTTP 周りで SSRF 対策を実装（スキーム検証、プライベートアドレス検査、リダイレクト検査）。
- XML パースに defusedxml を使用して脆弱性（XML Bomb 等）を緩和。
- .env 読み込み時のファイル読み取り失敗で警告を出す実装（予期しない例外を抑止）。

Performance
- J-Quants API 呼び出しでレート制限（固定間隔）を実装し、API レート超過を防止。
- RSS の挿入処理をチャンク化・トランザクションでまとめて実行し、DB オーバーヘッドを低減。
- ページネーション処理でモジュールレベルのトークンキャッシュを共有して余分な認証コールを削減。

Reliability
- API 呼び出しに対するリトライ（指数バックオフ）と、401 発生時の自動トークンリフレッシュで耐障害性を向上。
- DuckDB 保存処理は冪等化（ON CONFLICT ... DO UPDATE / DO NOTHING）を採用。
- RSS パースでの堅牢なエラーハンドリング（パース失敗時は空リストで継続）を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Known limitations
- strategy, execution, monitoring パッケージはパッケージ構造として存在するが、今回のスナップショットでは具体的なアルゴリズムや実装は含まれていません（将来のリリースで実装予定）。
- quality モジュール参照があるが、コード本体（品質チェックの個別実装）は本スナップショットに含まれていない可能性があります（パイプラインは品質チェックを呼ぶ設計になっている）。
- run_prices_etl のファイル末尾が切れているため（戻り値の構成など）、ETL の最後の仕様（戻り値の完全なタプル構成）は今後の修正で確定される見込みです。
- J-Quants の認証情報や Slack 連携等の外部連携は環境変数依存のため、運用環境での設定が必要です。

Authors
- KabuSys 開発チーム（コードベースのコメント・実装に基づき推定）

---

注: 本 CHANGELOG は提供されたコードスナップショットの内容から推測して作成したものであり、実際の変更履歴やリリースノートはリポジトリのコミット履歴・リリース管理情報に基づいて作成することを推奨します。