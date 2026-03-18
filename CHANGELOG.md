Keep a Changelog 準拠の CHANGELOG.md

All notable changes to this project will be documented in this file.

フォーマット:
- 本ファイルは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

[0.1.0] - 2026-03-18
Added
- 初期リリース（基本アーキテクチャと主要モジュールを追加）
  - パッケージ定義
    - kabusys パッケージの公開インターフェイスを定義（data, strategy, execution, monitoring）。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local からの自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパースロジックを独自実装（export プレフィックス、クォート、インラインコメント処理、保護キーによる上書き制御）。
    - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。
  - データアクセス / クライアント (src/kabusys/data/jquants_client.py)
    - J-Quants API クライアントを実装：
      - 日足 (OHLCV)、財務データ（四半期 BS/PL）、マーケットカレンダーの取得関数を提供（ページネーション対応）。
      - API レート制限 (120 req/min) に基づく固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 時は Retry-After ヘッダを優先。
      - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライ（無限再帰を防止）。
      - レスポンスの JSON デコードエラー処理、例外ラップ。
      - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices, raw_financials, market_calendar）。
      - データ型安全な変換ユーティリティ（_to_float, _to_int）。
      - fetched_at に UTC タイムスタンプを記録して Look-ahead Bias の追跡を容易にする設計。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードからの記事収集パイプラインを実装：
      - RSS 取得（fetch_rss）、前処理（URL 除去・空白正規化）、記事IDは正規化 URL の SHA-256（先頭32文字）を採用して冪等性を保証。
      - defusedxml を使用した XML パースで XML Bomb 等を防御。
      - SSRF 対策：
        - fetch 前のホスト検査（プライベート/ループバック/リンクローカル検知）。
        - リダイレクト時にもスキーム/ホストを検証する独自の RedirectHandler を採用。
        - http/https 以外のスキーム拒否。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、事前チェック・読み込み上限・gzip 解凍後の再検査を実施（メモリ DoS / Gzip bomb 対策）。
      - トラッキングパラメータ（utm_*, fbclid 等）を除去する正規化実装。
      - DuckDB への保存 API：
        - save_raw_news: チャンク化してトランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING 1）して挿入数を正確に返す。
      - 銘柄コード抽出関数 extract_stock_codes（4桁の数字パターン + known_codes フィルタ）。
      - デフォルト RSS ソースに Yahoo Finance を登録。
  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution レイヤー）:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 適切なチェック制約（CHECK, NOT NULL）や外部キー、インデックスを定義。
    - init_schema(db_path) で DB ファイルの親ディレクトリ作成とテーブル/インデックス作成を行い、接続を返す。
    - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーリストなど）。
    - 差分更新用ユーティリティを実装（テーブル存在確認、最大日付取得）。
    - 市場カレンダーに基づく営業日調整ロジック（_adjust_to_trading_day）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパー。
    - run_prices_etl の骨格を実装（差分取得、バックフィル日数対応、jq.fetch_daily_quotes と jq.save_daily_quotes の呼び出し）。※処理の一部は未完（下記「既知の制限」参照）。
  - セキュリティ・耐障害性の考慮
    - ネットワーク/HTTP エラーに対するリトライやログ出力。
    - RSS 周りで SSRF/サイズ攻撃/XML 攻撃を考慮した堅牢な実装。
  - ロギング
    - 各主要処理で logger.info/warning/exception を使用し実行状況を記録。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- defusedxml を用いた XML パース（XML Bomb 対策）。
- RSS フェッチ時の SSRF 対策（ホスト/IP のプライベート判定、リダイレクト先検査、スキーム制限）。
- レスポンスサイズ制限と gzip 解凍後の再チェックによるメモリ DoS / Gzip bomb 対策。
- .env ローダーは OS 環境変数を保護する（protected keys）仕組みを採用。

注意 / 既知の制限
- run_prices_etl の返り値処理（pipeline モジュールの末尾）が途中で切れているように見える（提供されたコード片では関数末尾が不完全）。本番利用前に ETL の結合フローと戻り値の整備が必要。
- strategy, execution, monitoring のパッケージ __init__ は存在するが、具体的な実装は含まれていない（今後の追加予定）。
- quality モジュールの詳細実装は本コードベースに含まれていない（ETL は quality 結果を想定する設計になっている）。
- 単体テストや統合テストは付属していない。ネットワーク/I/O を伴う箇所はモック可能な設計（例: news_collector._urlopen を差し替え）になっているが、テスト追加を推奨。

開発者向けメモ
- 環境設定は settings オブジェクトを通して取得すること（例: from kabusys.config import settings）。
- DuckDB 初期化は init_schema() を使用してから get_connection() を利用すること。
- J-Quants API 呼び出しは id_token を引数で注入できるため、テストでは明示的なトークン注入や _get_cached_token のモックが利用可能。
- news_collector の関数は外部からのネットワーク制御・リダイレクト制御が重要なため、CI では外部アクセスを行わないようにモックやローカルサーバを用いること。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的実装。
- ETL の品質チェック (quality モジュール) と fail-policy の洗練。
- 単体テスト・CI ワークフローの追加。
- ドキュメント（DataPlatform.md / DataSchema.md 等）との整合性チェックと追加の例示。

-----