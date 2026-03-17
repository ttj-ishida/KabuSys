Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティック バージョニングに従います。

Unreleased
----------

（現在のリリースはありません）

0.1.0 - 2026-03-17
-----------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基盤機能を追加。
- パッケージ公開情報
  - パッケージルートに __version__ = "0.1.0"、public API に data/strategy/execution/monitoring を定義。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env 読み込み時の柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - settings オブジェクトを通じた必須設定取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証（許容値チェック）。
  - DB パスの既定値（DuckDB/SQLite）と Path 型での取得を提供。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx、429 時は Retry-After を優先）。
  - 401 レスポンス時の自動トークンリフレッシュ（1 回だけ）と id_token キャッシュ共有機構。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias のトレーサビリティを確保。
  - DuckDB への保存は冪等化（INSERT ... ON CONFLICT DO UPDATE）を利用。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し不正データを安全に扱う。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事保存の実装（デフォルトソースに Yahoo Finance のカテゴリ RSS を追加）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - defusedxml による XML パースで XML Bomb 等に対する防御。
  - SSRF 対策:
    - fetch 前にホストがプライベートか検査。
    - リダイレクト先を検査するカスタム RedirectHandler を導入。
    - http/https 以外のスキームを拒否。
  - レスポンスサイズ制限（最大 10 MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）、記事保存はチャンク／トランザクション単位で行い INSERT ... RETURNING で挿入件数を正確に取得。
  - 記事と銘柄コードの紐付け機能（news_symbols）と銘柄抽出ロジック（4桁銘柄コード抽出、known_codes によるフィルタリング）。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の4層に渡るテーブル群を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, 等）。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを設計。
  - init_schema() でディレクトリ作成 → テーブル作成（冪等）を実行、get_connection() を提供。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新のためのユーティリティ（raw_* の最終日取得、取引日調整）。
  - run_prices_etl など個別 ETL ジョブを実装（差分取得、backfill 対応、保存）。
  - ETL 実行結果を表す ETLResult データクラス（品質問題やエラー一覧を保持、辞書化メソッドを提供）。
  - 市場カレンダーの先読みや品質チェックフックへの統合が可能な設計。

Security
- RSS XML のパースに defusedxml を使用し外部実行攻撃対策を実装。
- ニュース収集での SSRF 対策を導入（スキーム検証、プライベートホスト検査、リダイレクトの検証）。
- HTTP レスポンス読み込みに最大バイト数制限を設け、メモリ DoS / Gzip bomb に対処。

Changed
- （該当なし：初回リリース）

Fixed
- （該当なし：初回リリース）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / Implementation details
- .env の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御可能。
- J-Quants クライアントは内部で id_token をキャッシュするため、ページネーションや複数呼び出しでトークン取得を効率化。
- DuckDB への保存は各 save_* 関数が冪等性を担保する設計。初回ロード・追加入力いずれでも同じスキーマを利用できる。
- news_collector の記事 ID はトラッキングパラメータを除去した URL を基に生成するため、同一記事の重複登録を抑止できる。

今後の予定
- quality モジュールによる詳細な品質チェック実装と、その結果に基づくアラート/再試行ポリシーの追加。
- execution/strategy/monitoring モジュールの具体実装（現在はパッケージエントリのみ）。
- 単体テスト・統合テストの整備（ネットワーク依存箇所のモック化、外部 API のスタブ化）。