CHANGELOG
=========

すべての重大な変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の慣例に準拠しています。
リリース日はリポジトリ内のバージョン情報（src/kabusys/__init__.py）に基づきます。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
- パッケージエントリポイントを追加（src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブモジュール指定）。
- 環境設定管理モジュールを追加（kabusys.config）。
  - .env ファイルおよび環境変数から自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パーサを実装（export プレフィックス、シングル/ダブルクォート、インラインコメントなどに対応）。
  - 設定読み取り用 Settings クラスを提供（J-Quants / kabuAPI / Slack / DBパス / 環境/ログレベル検証など）。
  - 環境値検証: KABUSYS_ENV, LOG_LEVEL の有効値チェック。

- J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - 株価日足、財務データ、JPX マーケットカレンダー取得の実装。
  - API レート制御（固定間隔スロットリング）: 120 req/min に準拠する RateLimiter を実装。
  - 再試行付き HTTP 呼び出し: 指数バックオフ、最大リトライ回数、408/429/5xx の再試行処理。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ。
  - ページネーション対応（pagination_key の追跡）。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス対策。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE を使用）。
  - 値変換ユーティリティ: _to_float / _to_int（空値・不正値を安全に扱うロジック）。

- ニュース収集モジュールを追加（kabusys.data.news_collector）。
  - RSS フィードから記事を取得し raw_news に保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト時の検査用ハンドラ。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - 記事 ID を正規化 URL の SHA-256 の先頭32文字で生成し冪等性を保証。
  - テキスト前処理: URL 除去、空白正規化。
  - DuckDB への保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用、新規挿入 ID を返す（トランザクションで実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存、INSERT ... RETURNING を利用して実際に挿入された件数を返す。
  - 銘柄コード抽出: 正規表現による 4桁コード抽出と既知コードセットでのフィルタリング。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを設定。

- DuckDB スキーマ定義・初期化モジュールを追加（kabusys.data.schema）。
  - Data Lake の 3 層（Raw / Processed / Feature）ならびに Execution 層テーブルを定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けにインデックスを作成。
  - init_schema(db_path) でディレクトリ作成、DDL 実行による初期化を行う（冪等）。

- ETL パイプラインを追加（kabusys.data.pipeline）。
  - 差分更新ロジック: DB の最終取得日を参照して必要範囲のみ取得。
  - バックフィル（デフォルト backfill_days = 3）により後出し修正を吸収。
  - 市場カレンダー先読み（日数: 90日）などの設定を反映。
  - ETLResult データクラスを導入（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
  - 品質チェック（quality モジュールとの連携）により欠損・スパイク等を検出するが、重大度に応じて ETL を続行する設計。
  - run_prices_etl 実装（差分算出、fetch/save の連携）。最小データ開始日として 2017-01-01 を使用。

Changed
- （該当なし: 初期リリース）

Fixed
- （該当なし: 初期リリース）

Security
- ニュース取得で defusedxml、SSRF ブロックハンドラ、レスポンスサイズ制限を導入し外部入力に対する堅牢性を確保。
- .env 読み込み時に OS 環境変数保護（protected set）を導入し、明示的上書き時のみ .env.local で上書き可能とした。

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / 実装上の留意点
- J-Quants API 呼び出しは urllib を使用しており、外部 HTTP ライブラリ依存を最小化しているため、必要に応じてモックや差し替えが可能。
- news_collector のネットワーク処理は内部的に _urlopen を使用しており、テスト時にモック差し替え可能。
- DuckDB の INSERT ... RETURNING を多用して実際に挿入された件数を正確に返す仕様のため、将来的に他 DB へ移行する場合は互換性に注意が必要。
- settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出するため、運用前に .env を整備してください。

今後の予定（候補）
- strategy / execution / monitoring の実装（現在はパッケージ構成のみ）。
- 品質チェックモジュールの拡充と自動アラート連携（Slack 通知など）。
- 単体テスト・統合テストの充実と CI ワークフロー追加。
- 外部 API 呼び出しの回線監視・メトリクス収集の追加。

-----------------------------------------------------------------------------