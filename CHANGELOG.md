CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記載します。
このプロジェクトはセマンティックバージョニングを採用しています。  
https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-17
--------------------

初回リリース。以下の主要機能・設計方針を実装しています。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージの __version__ = "0.1.0" を定義。__all__ に data, strategy, execution, monitoring を公開。
- 環境設定 / config
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env, .env.local の読み込み優先度を実装（.env.local は上書き可能）。OS 環境変数は保護（protected）され、誤って上書きされない。
  - .env パーサーは export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントを考慮した堅牢な解析を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）のプロパティを定義。env と log_level の入力検証あり。
- データ取得クライアント（data/jquants_client.py）
  - J-Quants API クライアントを実装。価格（日足）、財務（四半期 BS/PL）、市場カレンダーを取得可能。
  - レート制限（固定間隔スロットリング）を実装し、デフォルトで 120 req/min を遵守。
  - リトライ戦略（指数バックオフ、最大 3 回）。HTTP 408/429 とサーバーエラー（5xx）を対象にリトライ。429 の Retry-After ヘッダを優先。
  - 401 受信時はリフレッシュトークンで自動的に ID token を更新して 1 回リトライ（無限再帰回避のため allow_refresh フラグ設計）。
  - ページネーション対応（pagination_key によるループ）を実装。
  - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。冪等性のため INSERT ... ON CONFLICT DO UPDATE を使用。
  - データ取得時刻（fetched_at）を UTC 形式で保存し、look-ahead bias 対策と監査トレースをサポート。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値を安全に扱う。
- ニュース収集モジュール（data/news_collector.py）
  - RSS フィードからニュースを取得して raw_news に保存する収集パイプラインを実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等を防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでは拒否、リダイレクト時にも事前検証を行う専用ハンドラ導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を適用しメモリDoSを防止。gzip 解凍後もサイズチェック。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）と記事ID生成（正規化URL の SHA-256 の先頭32文字）による冪等性保証。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存:
    - raw_news へのチャンク化されたバルク INSERT をトランザクション内で実行（チャンクサイズ 1000）。
    - INSERT ... RETURNING id を使って新規挿入された記事IDのリストを正確に取得。
    - news_symbols への銘柄紐付けをバルク挿入（重複除去＆トランザクション）で効率化。ON CONFLICT DO NOTHING を採用。
  - 銘柄コード抽出機能（4桁数値パターン）と既知銘柄セットによるフィルタリングを提供。
  - run_news_collection により複数ソースを順次取得し、例外はソース単位で処理して他ソースへ影響を与えない設計。
- DuckDB スキーマ（data/schema.py）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance などを定義。
  - 主キー・外部キー・チェック制約を適切に設定（数値の非負チェック、列値の列挙チェック等）。
  - 検索頻度の高いカラムに対するインデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行でスキーマ初期化を実現。get_connection() で既存 DB へ接続可能。
- ETL パイプライン（data/pipeline.py）
  - ETLResult dataclass を導入し、ETL 実行結果・品質問題・エラー情報を集約・辞書化可能に実装。
  - 差分更新ユーティリティ: テーブル最終取得日の取得、営業日調整（market_calendar に基づいて過去最終営業日に調整）を提供。
  - run_prices_etl の基礎実装:
    - 差分更新ロジック（最終取得日から backfill_days 前を date_from として再取得）を実装。デフォルト backfill_days = 3。
    - J-Quants クライアントを利用して fetch → save の流れを実行し、取得数と保存数を返す設計（差分ETLの一部機能を実装）。
  - 市場カレンダーは先読み（デフォルト 90 日）して将来の営業日判定に利用する設計方針を明記。
- その他
  - data パッケージ内の主要モジュール構成を整理（jquants_client, news_collector, schema, pipeline）。
  - strategy/ execution パッケージのプレースホルダを用意（現段階では __init__ が空）。

Security
- ニュース収集で SSRF 対策、defusedxml による XML 攻撃対策、レスポンスサイズ制限を導入。
- .env 読み込みで OS 環境変数を保護する protected キーの概念を導入。

Notes / Known limitations
- strategy、execution モジュールはインターフェース定義の段階で、アルゴリズム本体は未実装（プレースホルダ）。
- ETL パイプラインは主要な差分取得ロジックを実装しているが、完全なスケジュール実行・品質チェックのフルワークフロー統合（quality モジュール呼び出し等）は外部モジュールとの連携を前提としている。
- コードの一部は今後の拡張（例: 追加の API エンドポイント、詳細な品質チェックルール、Slack 通知など）を想定して設計されています。

誤り・改善要望があれば issue を作成してください。