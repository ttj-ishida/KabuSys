CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に準拠します。  

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-17
--------------------

初回リリース。日本株自動売買プラットフォームの基盤的なコンポーネントを実装しました。
以下はコードベースから推測してまとめた主要な追加点・設計方針・重要な振る舞いの要約です。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"、主要サブパッケージを __all__ に公開）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を提供。
    - プロジェクトルート検出は .git / pyproject.toml を基準に行い、CWD に依存しない方式。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーは export 形式、クォートやエスケープ、インラインコメントなどに対応。
  - Settings クラスを公開（settings）。J-Quants / kabu API / Slack / DB パス等のプロパティを提供し、
    KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実施。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を固定間隔スロットリングで制御（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429 と 5xx は再試行対象。
    - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回のみリトライ。
    - ページネーション対応で全ページを収集（pagination_key を追跡）。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar は冪等（ON CONFLICT DO UPDATE）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し不正データを安全に扱う。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を安全に収集して DuckDB に保存する仕組みを実装。
    - デフォルトソース（Yahoo Finance のビジネスカテゴリ RSS）を定義。
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先を事前検証するカスタムリダイレクトハンドラ(_SSRFBlockRedirectHandler)。
      - ホスト/IP がプライベート/ループバック/リンクローカル等の場合は拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後も検査（Gzip bomb 対策）。
    - URL 正規化（クエリのトラッキングパラメータ除去、フラグメント除去、キーソート）、SHA-256 による記事 ID 生成（先頭 32 文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news はチャンク化して INSERT ... RETURNING を使い新規挿入 ID を返す（トランザクションを利用）。
      - save_news_symbols / _save_news_symbols_bulk は銘柄紐付けの一括挿入をサポート（重複排除・チャンク挿入）。
    - 銘柄コード抽出ロジック（4 桁数字を候補とし known_codes でフィルタリング）。
    - run_news_collection により複数 RSS ソースを独立して処理し、記事保存数と銘柄紐付けを実行。
- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマを体系的に定義（Raw / Processed / Feature / Execution の 3 層＋実行レイヤ）。
  - テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - インデックス定義（頻出クエリのための複数インデックス）。
  - init_schema(db_path) でディレクトリ自動作成も含めてスキーマ初期化を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を実装し、ETL の結果（取得数、保存数、品質問題、エラー）を集約。
  - 差分更新ユーティリティ（最終取得日の参照）や市場カレンダー調整ロジックを実装（_get_max_date, _adjust_to_trading_day 等）。
  - run_prices_etl を含む差分 ETL ロジックを実装。デフォルトで最終取得日から backfill_days（デフォルト 3 日）分を再取得して API の後出し修正を吸収する設計。
- その他
  - 各モジュールで詳細なログ出力（info/warning/exception）を追加し運用時の可観測性に配慮。

Security
- RSS XML パースに defusedxml を使用し、XML による攻撃対策を実施。
- SSRF 対策を複数レイヤーで実装（スキーム検証、リダイレクト時検査、プライベート IP/ホストの拒否）。
- .env 読み込みでは既存 OS 環境変数を保護する仕組みを用意（protected set）。

Performance
- J-Quants API へのリクエストでレートリミットを厳守するスロットリング実装（固定間隔）。
- ネットワークエラー時の指数バックオフ再試行を実装。
- DB 操作はチャンク化およびトランザクションでまとめて実行しオーバーヘッドを低減（news_collector の INSERT チャンクや DuckDB の executemany）。
- DuckDB 側に索引を作成して頻出クエリのパフォーマンスを改善。

Robustness / Data quality
- fetch 系はページネーションやトークン切れ対応を実装し、データ欠落や再取得に強い設計。
- 保存関数は冪等に設計されており、PK 欠損行はスキップして警告ログを出力。
- ETLResult は品質チェック結果（quality モジュールの QualityIssue 想定）を格納し、品質問題があっても ETL を継続する方針。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- run_prices_etl 等の ETL 関連は差分更新やバックフィル方針を実装済みですが、パイプライン全体（品質チェック呼び出しの統合やすべての ETL ジョブの完全な集約）は今後の拡張対象です。
- DuckDB の SQL 文は直接組み立てる箇所があり（プレースホルダを用いてはいるが、長大な SQL の組立てに注意）、将来的にバインド方式の統一や ORM 層追加を検討すると良いでしょう。
- news_collector の既知の RSS ソースはデフォルトで 1 件のみ定義（拡張可能）。

開発者向けメモ
- 環境変数の必須項目：
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須として取得されるため、実行前に設定が必要。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを無効化しておくとテスト環境を汚さずに済みます。
- news_collector._urlopen はテストでモックして外部ネットワークアクセスを差し替え可能な設計。

---

今後の予定（例）
- quality モジュールと ETL の統合（自動品質レポート出力、外部通知）。
- execution 層（kabu ステーション連携）および strategy 実装の追加。
- 監視・アラート（Slack 経由）やバッチスケジューリングの整備。

以上。必要であれば各ファイルごとの変更点をさらに詳細に分解して追記します。