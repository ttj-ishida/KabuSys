CHANGELOG
=========

このファイルは Keep a Changelog のフォーマットに準拠しています。
許容されるバージョン語彙: 変更履歴は機能追加(Added)、変更(Changed)、修正(Fixed)、破壊的変更(Breaking Changes)、セキュリティ(Security) 等で整理します。

[0.1.0] - 2026-03-19
-------------------

初回公開リリース。パッケージ名: kabusys (バージョン 0.1.0)

Added
- パッケージ基本構成
  - モジュール公開インターフェースを定義 (src/kabusys/__init__.py)。
- 設定管理
  - 環境変数と .env ファイルを自動読み込みする設定モジュールを追加 (src/kabusys/config.py)。
    - プロジェクトルートを .git または pyproject.toml から自律的に検出して .env / .env.local を読み込む。
    - .env のパースは export 形式、引用符つき値、インラインコメント等に対応。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得時に未設定だと明示的な例外を投げる _require() を提供。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証と convenience プロパティ (is_live / is_paper / is_dev) を提供。
- データ取得 / 永続化
  - J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装。
    - 指数バックオフによる自動リトライ（最大 3 回）と 401 発生時のトークン自動リフレッシュ。
    - ページネーションに対応した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements 等）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar 等）。ON CONFLICT による更新で重複を排除。
    - 入力データの型安全なパースユーティリティ (_to_float, _to_int) を提供。
- ニュース収集（RSS）
  - RSS 収集・前処理・DB 保存機能を実装 (src/kabusys/data/news_collector.py)。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url / _make_article_id）。
    - defusedxml を用いた安全な XML パース。
    - SSRF 対策: 許可スキームの検証（http/https のみ）、リダイレクト先の検証、プライベートアドレス検出によるブロック。
    - レスポンスサイズ制限 (MAX_RESPONSE_BYTES) と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - 記事IDは正規化 URL の SHA-256 の先頭32文字で冪等性を確保。
    - raw_news へのバルク INSERT（チャンク単位）および INSERT ... RETURNING による挿入済みIDの取得。
    - 記事テキスト前処理（URL 除去、空白正規化）および本文からの銘柄コード抽出機能（extract_stock_codes）。
    - run_news_collection により複数 RSS ソースの統合収集を実行可能。
- DuckDB スキーマ定義
  - Raw 層のテーブル DDL を定義するスキーマモジュールを追加 (src/kabusys/data/schema.py)。
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（DataSchema.md に準拠）。
- リサーチ用機能（特徴量・因子）
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関、欠損/非有限値の除外）。
    - ファクター統計サマリー factor_summary と汎用の rank 実装。
  - 因子計算モジュール (src/kabusys/research/factor_research.py)
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200日移動平均乖離率。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR、相対 ATR、平均売買代金、出来高比率。
    - バリュー (calc_value): raw_financials から最新財務を取得して PER/ROE を計算。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照し本番 API にはアクセスしない設計。
  - research パッケージ初期エクスポートを提供 (src/kabusys/research/__init__.py)。
- ロギングと診断
  - 各モジュールで詳細ログ出力（info/warning/debug/exception）を追加し、運用時のトラブルシュートを支援。
- テスト＆拡張性を意識した設計
  - ニュース収集で _urlopen を切り替え可能にしてテスト時のモックが容易。
  - jquants_client のトークンキャッシュや rate limiter はページネーションや並列実行を想定した設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサに defusedxml を採用し XXE や XML 関連の脆弱性を軽減。
- RSS/HTTP の SSRF 対策を導入（スキーム検証、プライベートアドレス検査、リダイレクト時の検査）。
- レスポンスサイズ制限と gzip 解凍後の検査によりメモリ DoS / Gzip bomb を軽減。
- .env パーサは引用符内のバックスラッシュエスケープに対応し、不正な文字解釈を抑制。

Performance
- J-Quants API クライアントで固定間隔レートリミッターを導入しレート制限順守を保証。
- fetch_* 系はページネーションを処理し、一時的なページネーションキー共有のためのトークンキャッシュを設置。
- DB への保存はバルク実行（executemany / チャンク INSERT）を採用しオーバーヘッドを低減。
- news_collector の銘柄紐付けは重複除去後にチャンク化して一括挿入。

Documentation
- 各モジュールに docstring と設計方針・使用上の注意を記載（Research / DataPlatform / Strategy 等の参照ドキュメントを想定）。

Breaking Changes
- なし（初回リリース）。

Migration notes / 運用上の注意
- .env 自動ロードはデフォルトで有効。CI/テストで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は settings によりアクセス時にエラーが発生します。デプロイ前に .env を整備してください。
- DuckDB スキーマは src/kabusys/data/schema.py の DDL に基づき初期化する必要があります（schema 初期化ユーティリティを別途呼び出すことを想定）。
- news_collector の extract_stock_codes は日本株の 4 桁コードを想定しています。別フォーマットを扱う場合は正規表現を調整してください。

今後の予定（例）
- Strategy / execution / monitoring の具体的実装（発注ロジック・ポジション管理・監視アラート）。
- 追加のファクター（PBR、配当利回り等）の実装。
- Unit テストと CI の整備（外部 API モック、ネットワーク失敗ケース等）。
- ドキュメント（利用手順、DB マイグレーション、運用ガイド）の充実。

注記
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際の変更履歴（コミットログ等）がある場合はそれに合わせて更新してください。