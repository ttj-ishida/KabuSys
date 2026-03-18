CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初版リリースを記録します。

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージを公開。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない設計。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードは無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理、コメント行スキップ等に対応。
  - 必須設定の検証ユーティリティ _require を提供。
  - Settings クラスにより以下の主要設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev の簡易プロパティ
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足・財務データ・マーケットカレンダー等を取得するクライアント機能を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
  - 再試行ロジック（最大 3 回・指数バックオフ）を実装。HTTP 408/429 と 5xx 系に対してリトライ。
  - 401 Unauthorized（トークン期限切れ）を検出した場合に自動で ID トークンをリフレッシュして 1 回リトライする機構を実装（無限再帰防止あり）。
  - ページネーション対応の fetch_* 関数群を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。fetched_at を UTC で記録して Look‑ahead bias のトレースを容易に。
  - 型変換ユーティリティ _to_float / _to_int を実装。_to_int は "1.0" 形式の文字列を正しく int に変換し、小数部が存在する場合は None を返す保守的な動作。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存するワークフローを実装。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML bomb 対策）。
    - SSRF 対策: リダイレクト時のスキームチェック、ホストのプライベートアドレス検査、初回 URL の事前検査、専用リダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を超えるレスポンスはスキップ、gzip 解凍後もサイズ検査を実施。
    - URL スキーム制限（http/https のみ）。
  - 記事ID生成: URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント削除）した後 SHA-256 ハッシュの先頭 32 文字を採用して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4 桁数字、known_codes によるフィルタ）を提供。
  - DB 保存はチャンク化してトランザクションで実行し、INSERT ... RETURNING により実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- DuckDB スキーマ初期化（src/kabusys/data/schema.py）
  - DataSchema に基づく 3 層（Raw / Processed / Feature）設計を想定したスキーマ定義モジュールを追加。
  - raw_prices, raw_financials, raw_news, raw_executions（部分定義）等の DDL を定義。各テーブルに制約（NOT NULL、CHECK、PRIMARY KEY）や fetched_at カラムを含む。
- 研究（Research）用モジュール（src/kabusys/research/）
  - ファクター計算: src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）を計算。過去データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。report_date <= target_date の最新レコードを選択。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API を叩かない設計。
  - 特徴量探索ユーティリティ: src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト 1,5,21）までの将来リターンを一括 SQL で計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関を計算（ties は平均ランク処理）。有効レコードが 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク付けユーティリティ（丸め誤差対策に round(v,12) を採用）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する簡易統計サマリー。
  - research パッケージ初期エクスポートを定義（__all__ に calc_momentum 等を追加）。zscore_normalize は kabusys.data.stats から利用する想定でインポートされる（外部参照）。
- その他ユーティリティ
  - 抽出用正規表現や定数（銘柄コード 4 桁パターン、RSS 関連定数等）を実装。

Security
- RSS パーサに defusedxml を利用し XML 関連の脆弱性（XML Bomb 等）に対処。
- ニュース収集で SSRF 対策（ホストプライベート検査、リダイレクト検査、スキーム制限）を実装。
- J-Quants クライアントで認証トークン取り扱いと自動リフレッシュの仕組みを安全に実装（無限再帰防止）。

Notes / Known issues
- data.stats.zscore_normalize は research.__init__ から参照されているが、このスナップショットには該当実装ファイルの内容が含まれないため、外部に実装が存在することを前提としています。
- schema.py は複数のテーブル DDL を含むが、このスナップショットでは raw_executions の定義が途中で終わっています。完全なスキーマ定義は今後整備される想定です。
- 一部モジュールは外部ライブラリ（duckdb, defusedxml）に依存します。デプロイ時に依存関係を解決してください。

マイグレーション
- 初版のため互換性変更はなし。環境変数（JQUANTS_REFRESH_TOKEN 等）の設定が必要です。

opyright
- 本 CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノート作成時は各機能追加の責任者による確認を推奨します。