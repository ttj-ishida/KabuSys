CHANGELOG
=========

すべての重要な変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初期リリース。モジュール構成:
  - kabusys.config: 環境変数 / 設定管理
    - .env, .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロード
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメント等に対応
    - settings オブジェクトを公開（J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル 等）
    - env/log_level のバリデーションと is_live/is_paper/is_dev のユーティリティプロパティ

  - kabusys.data.schema: DuckDB スキーマ定義と初期化
    - Raw / Processed / Feature / Execution の各レイヤー用テーブル定義
    - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを定義
    - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成（冪等）
    - get_connection(db_path) で既存 DB へ接続

  - kabusys.data.jquants_client: J-Quants API クライアント
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用 fetch_* 関数（ページネーション対応）
    - HTTP レート制御（固定間隔スロットリング: 120 req/min 相当の RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ
    - モジュールレベルのトークンキャッシュ（ページネーションや複数呼び出し間で共有）
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar は ON CONFLICT DO UPDATE による冪等実装
    - データ取得時に fetched_at を UTC で記録（Look-ahead bias 対策）

  - kabusys.data.news_collector: RSS ニュース収集
    - RSS フィード取得（デフォルトに Yahoo Finance のビジネス RSS を設定）と raw_news への保存フロー
    - defusedxml を使った安全な XML パース、XML Bomb 等への対策
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルであれば拒否
      - リダイレクト時にもスキーム・ホスト検査を行うカスタムハンドラを実装
      - テスト用に _urlopen を差し替え可能（モック対応）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）
    - トラッキングパラメータ除去（utm_* 等）、URL 正規化、SHA-256 ハッシュ（先頭32文字）による記事ID生成で冪等性を確保
    - テキスト前処理（URL 除去、空白正規化）
    - DuckDB への保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事IDを返却。チャンク化して 1 トランザクションで実行。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... ON CONFLICT DO NOTHING RETURNING で保存
    - 銘柄コード抽出ロジック（4桁数字の抽出、known_codes によるフィルタ、重複排除）
    - run_news_collection: 複数ソースを順次処理。各ソース単位でエラーを隔離して継続処理。新規保存件数を返却

  - kabusys.data.pipeline: ETL パイプライン（骨組み）
    - 差分更新のためのユーティリティ（テーブル存在チェック、最終日取得）
    - 市場カレンダーを用いた日付調整ヘルパー（非営業日の場合に直近の営業日に補正）
    - run_prices_etl（骨組み）:
      - 最終取得日に基づく差分再取得（デフォルト backfill_days=3 で後出し修正を吸収）
      - fetch → save の流れとロギング、ETLResult データクラスによる結果集計（品質問題・エラーの集約）
    - ETLResult: 実行結果（取得数/保存数/品質問題/エラー 等）を保持し、辞書化可能

  - パッケージ初期化情報
    - kabusys.__init__ にて __version__ = "0.1.0"、__all__ を設定

Security
- 複数箇所でセキュリティ配慮を実装:
  - defusedxml による XML パース（ニュース収集）
  - SSRF 対策（スキーム検証、プライベートホスト検査、リダイレクト検査）
  - レスポンスサイズ上限、gzip 解凍後のサイズチェック（DoS 対策）
  - .env 読み込みでは OS 環境変数保護（protected set）を考慮した上書き制御

Notes / Implementation details
- DuckDB をデータストアに採用。スキーマには厳密な型・CHECK 制約を付与してデータ品質を担保
- jquants_client の HTTP レイヤは urllib を直接使用し、JSON デコードエラー時は明確なエラーを発生させる
- news_collector では記事IDを URL 正規化 → SHA-256 で生成しているため、クライアント側で重複チェックが容易
- テスト容易性のために外部呼び出し部（URL オープン、トークン取得の注入など）は差し替え可能に設計

Known limitations / TODO（将来的な改善候補）
- ETL パイプラインの完全なワークフロー（品質チェックモジュールの詳細実装やスケジューリング）は本版では骨格の実装に留まる
- execution / strategy / monitoring パッケージの実体はこのリリースで最小化（__init__ のみ）。発注ロジック・戦略実装は今後追加予定
- 一部の例外メッセージやログは英語/日本語混在の可能性があるため整備検討

--- 

（注）本 CHANGELOG は現行コードベースの内容から推測して作成したもので、実際のリリースノートは開発者の公式記録を優先してください。