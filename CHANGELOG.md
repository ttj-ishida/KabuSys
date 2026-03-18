CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のコードから推測して作成したものであり、実際のコミット履歴とは異なる可能性があります。

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ: src/kabusys/__init__.py にバージョンと公開モジュール定義を追加。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数自動ロード機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env の行パーサ（コメント、export プレフィックス、シングル/ダブルクォート、インラインコメントの考慮）。
    - .env.local を優先的に上書きロード。OS 環境変数の保護（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを提供（J-Quants トークン、kabu API、Slack トークン、DB パス、環境/ログレベルの検証等）。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - レート制限実装（固定間隔スロットリング、120 req/min を守る RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回。対象: 408/429/5xx、ネットワークエラー）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルでの ID トークンキャッシュ。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（冪等性: ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ: _to_float, _to_int（安全に None を返す挙動）。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードの取得・パース・前処理・DB 保存ワークフローを実装。
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 予防）。
      - URL スキーム検証（http/https のみ許可）とプライベートIP/ループバック判定による SSRF 対策。
      - リダイレクト時にもスキーム・ホストを検証するカスタムリダイレクトハンドラ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - 受信ヘッダの Content-Length を事前チェック。
    - 記事ID生成: URL 正規化（トラッキングパラメータ除去）→ SHA-256 先頭32文字で冪等性確保。
    - テキスト前処理（URL 除去、空白正規化）、pubDate の RFC2822 パース（UTC 揃え）。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id（挿入されたIDのみ返す）。
      - save_news_symbols / _save_news_symbols_bulk: article と銘柄コードの紐付けをトランザクションで保存（RETURNING を利用して実挿入数を取得）。
    - 銘柄抽出ユーティリティ: extract_stock_codes（4桁コード抽出・既知コードフィルタリング）。
    - 統合ジョブ: run_news_collection（複数ソースを独立して処理し、既知コードが与えられれば紐付けを一括挿入）。
- スキーマ & DB 初期化
  - src/kabusys/data/schema.py
    - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義と整合性チェック（CHECK / PRIMARY KEY）。
    - processed レイヤー（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、
      feature レイヤー（features, ai_scores）、
      execution レイヤー（signals, signal_queue, orders, trades, positions, portfolio_performance）。
    - インデックス群（頻出クエリを想定した複数の CREATE INDEX）。
    - init_schema(db_path) によるディレクトリ作成・DDL 実行、get_connection の提供。
- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass（処理結果、品質チェック結果、エラー一覧を保持）。
    - テーブル存在確認、最大日付取得ユーティリティ、営業日調整ロジック。
    - 差分取得方針（最小データ開始日、バックフィル日数、カレンダー先読みの考慮）。
    - 個別 ETL ジョブ実装の骨組み（例: run_prices_etl: 差分取得・backfill ロジック・jquants_client 呼び出し・保存）。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- ニュース収集における多層防御を実装:
  - defusedxml による安全な XML パース
  - SSRF 防止（スキーム検証、プライベートIPフィルタ、リダイレクト検査）
  - 大きすぎるレスポンスや gzip 解凍後のサイズチェックによるメモリ DoS 対策
- 環境変数読み込み時に OS 環境変数を保護する protected set を導入（.env による上書きを制御）

Performance
- API 呼び出しに対する固定間隔 RateLimiter（API レート制限厳守）。
- 冪等かつ効率的な DB 操作:
  - DuckDB へのバルク挿入でチャンク化（_INSERT_CHUNK_SIZE）を採用。
  - INSERT ... RETURNING を利用して実際に挿入された件数を正確に取得。
  - 単一トランザクションで複数チャンクをコミットすることで整合性とオーバーヘッド削減。

Notes / Known issues
- run_prices_etl の戻り値について:
  - 実装中の run_prices_etl は現在 fetch 件数を取得し jq.save_daily_quotes を呼び出しているが、ソース上は return 文が "return len(records)," のように見え、(fetched_count,) の 1 要素タプルを返している可能性があります（expected: (fetched, saved) のタプル）。パイプライン呼び出し側で期待される戻り値に合わせて修正する必要があります。
- quality モジュールの呼び出しや price/fundamentals の後続処理は設計に含まれるが、ファイル内では品質チェックロジックの詳細が別モジュール（kabusys.data.quality）に依存している想定です。統合テストでの確認が推奨されます。
- 一部のモジュール（strategy, execution, monitoring 等）はパッケージに含まれるが実装は空（プレースホルダ）。今後の拡張点です。

開発者向けメモ
- 環境: 自動 .env ロードはプロジェクトルートが検出できない場合スキップされます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト容易性: jquants_client の id_token は注入可能（引数で渡せる）ためモックが容易です。news_collector の URL オープン処理は _urlopen をモックして差し替えられます。
- DB 初期化: 初回は init_schema() を必ず呼び、以降は get_connection() を使用して接続してください。

参考
- この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴として使用する場合は、コミットログや PR 説明に基づいて適宜調整してください。