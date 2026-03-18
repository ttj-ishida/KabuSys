CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記録しています。
このファイルはコードベースの現状から推測して作成しています（実装・設計方針の抜粋）。

Unreleased
---------

- なし（現時点ではリリース済みの初期実装に関する記録を以下に示します）。

0.1.0 - 2026-03-18
------------------

Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0" を設定し、サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD非依存）。
  - .env の行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート処理、インラインコメント処理）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数保護（.env の上書きを制御する protected セット）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境・ログレベル等のプロパティを取得（未設定時のエラー判定や値検証を含む）。
  - 有効な環境値、ログレベルのバリデーションを実装（development / paper_trading / live、DEBUG/INFO/...）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API エンドポイントから株価（日足）、財務（四半期 BS/PL）、マーケットカレンダーを取得する関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限対応: 固定間隔スロットリング（120 req/min 相当）の RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大リトライ回数 3 回、HTTP 408/429 と 5xx を対象に再試行。
  - 401 応答時のトークン自動リフレッシュ（1 回のみ）と再試行を実装。id_token のモジュールレベルキャッシュを導入。
  - JSON デコード失敗時のエラー処理・ログを実装。
  - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を行う。
  - データ変換ユーティリティ (_to_float, _to_int) を実装して入力値の厳格化を実施。
  - 取得時刻（fetched_at）を UTC ISO フォーマットで記録し、Look-ahead バイアス対策に配慮。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集する機能を実装（fetch_rss）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML bomb などの保護）。
    - SSRF 対策: 初回チェックとリダイレクトごとの検証を行う独自リダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルであれば拒否（DNS で A/AAAA を検証）。
    - URL スキーム制限（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後も再検査（Gzip bomb 対策）。
  - 記事ID生成: URL 正規化後の SHA-256 の先頭 32 文字を使用して冪等性を担保（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - テキスト前処理（URL除去・空白正規化）を実装（preprocess_text）。
  - DuckDB への保存関数を提供:
    - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事IDのみを返す（チャンク/1トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを効率的に保存（ON CONFLICT で重複排除、チャンク挿入、INSERT ... RETURNING による正確な挿入数取得）。
  - 銘柄コード抽出 (extract_stock_codes): 4桁数字パターンを抽出し、既知銘柄セットに基づいてフィルタ。重複排除。

- DuckDB スキーマ定義及び初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤのテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム検査（CHECK 制約）や外部キー、主キーを設定してデータ整合性を強化。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を行い、DuckDB 接続を返す。get_connection() を提供。

- ETL / データパイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を表現。
  - 差分更新ロジック、最終取得日の検出ユーティリティ（get_last_price_date 等）を実装。
  - market_calendar による非営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl を実装: 差分算出（最終取得日 + backfill）、J-Quants からの取得、DuckDB への保存フローを用意。品質チェック（quality モジュール）呼び出しの設計余地を確保する設計。

Security
- 複数のセキュリティ向上策を導入:
  - RSS/HTTP の SSRF 対策（スキーム検証、リダイレクト時のホスト検査、プライベートIPの拒否）。
  - defusedxml による XML パース。
  - レスポンスサイズ制限によるメモリ DoS 対策。
  - J-Quants クライアントでのトークン自動リフレッシュやレート制限の実装により不正なリトライや過負荷を抑止。

Notes / Known issues / TODO
- run_prices_etl を含む ETL パイプラインは差分取得や backfill の設計を含むが、外部モジュール（quality 等）との統合・テストが想定されるため、実運用前に総合テストが必要。
- コードベースは堅牢性・安全性（SSRF、XML、レスポンスサイズ）に配慮しているが、実稼働環境での負荷試験・長期運用テストを推奨。
- 将来的な改善候補:
  - HTTP クライアントを urllib から requests 等へ切替え（利便性・拡張性向上）。
  - 非同期取得の導入（大量ソースのニュース収集や API ページネーションの高速化）。
  - ログやメトリクスの充実（Prometheus 等へのエクスポート）。

リリースノートについて
- この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリース日、追加のマイナー/パッチリリースがある場合は、実際のコミット履歴やリリース管理に従って更新してください。