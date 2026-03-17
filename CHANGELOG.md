# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠します。  

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームの基礎モジュールを実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0、公開モジュール指定）。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env ファイルの行パーサ（export KEY=val、クォート対応、インラインコメント処理）を実装。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - 必須設定を取得する _require()、Settings クラスを実装（J-Quants トークン、Kabu API、Slack、DB パス、環境種別・ログレベル検証等）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得するフェッチ関数を実装（ページネーション対応）。
  - レート制限管理（固定間隔スロットリングで 120 req/min を保証する RateLimiter）。
  - リトライロジック（指数バックオフ、最大リトライ回数、HTTP 408/429/5xx を対象）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回限定）とモジュールレベルの ID トークンキャッシュ。
  - DuckDB へ冪等に保存する save_* 関数群（ON CONFLICT DO UPDATE を使用）と型変換ユーティリティ（_to_float/_to_int）。
  - 取得タイミングを UTC で記録する fetched_at を付与（Look-ahead Bias 防止目的のトレーサビリティ）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news に保存する機能を実装。
  - セキュリティ・堅牢性強化：
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策：URL スキーム検証、プライベートアドレス判定、リダイレクト時の検査（専用 RedirectHandler）。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック。
    - 受信ヘッダ（Content-Length）を活用した早期スキップ。
  - URL 正規化（クエリのトラッキングパラメータ除去、ソート、フラグメント除去）と SHA‑256（先頭32文字）による記事ID生成で冪等性を確保。
  - テキスト前処理（URL除去・空白正規化）と pubDate の UTC パース。
  - DuckDB への保存はトランザクション単位でチャンク挿入し、INSERT ... RETURNING により実際に挿入されたレコードを返却。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン）と news_symbols への紐付けをバルク挿入する機能。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 制約（PK/FOREIGN KEY/チェック制約）とインデックスを予め定義。
  - init_schema(db_path) による初期化（親ディレクトリ自動作成）と get_connection() を提供。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス（品質情報・エラー情報含む）を実装。
  - 差分取得ヘルパー（テーブル最終取得日の取得）、営業日調整ロジック（market_calendar を利用）を追加。
  - run_prices_etl を含む株価差分 ETL の骨子を実装（差分判定、backfill_days による再取得範囲、jquants_client の fetch/save 呼び出し）。
  - 設計方針として「差分更新」「後出し修正吸収のためのバックフィル」「品質チェックは収集継続」などを採用。

### Security
- ニュース収集での SSRF 対応、XML インジェクション対策、受信サイズ制限、http/https スキーム強制など、外部入力に起因するリスクを複数箇所で低減。
- 環境変数読み込み時に OS 環境変数を保護するための protected キー処理を実装。

### Changed
- 初期設計段階のため、ログ出力や警告メッセージが各所に整備されており、運用時のトラブルシュートを容易にするよう調整。

### Fixed
- —（初回リリースのため修正履歴なし）

### Notes / ドキュメント
- コード内ドキュメント（モジュールトップの設計方針、関数 docstring）を多く記載し、動作意図と制約を明示しています（DataPlatform.md / DataSchema.md を想定した実装）。
- settings は環境変数に依存するため、.env.example を用意して環境構築を行うことを推奨します。

### 既知の問題 / 今後の改善予定
- run_prices_etl の戻り値や pipeline の一部実装が発展途上（コードの一部が未完／続きが必要）であり、ETLResult との統合やファイル末尾の処理完了の有無は今後の実装で補完予定です。
- 単体テスト・統合テストは未実装。特にネットワーク依存部分（jquants_client、news_collector）のモックテストケースを追加予定。
- エラーハンドリングやメトリクス収集（失敗率、API レート統計、処理時間等）の強化を予定。
- ドキュメント（README、運用手順、DB スキーマ説明）の整備を進める予定。

---

開発・運用に関する質問や、CHANGELOG の補足項目追加要望があれば教えてください。