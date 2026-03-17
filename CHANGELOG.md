# Changelog

すべての注記は Keep a Changelog の標準に従います。  
安定したリリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース。日本株向け自動売買プラットフォームの基盤機能を実装しました。主な機能・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理
  - src/kabusys/config.py を追加。
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - `.env` 行パーサを実装（export 対応、クォートとコメント処理、エスケープ対応）。
  - settings オブジェクト実装（J-Quants / kabu / Slack / DB パスなどの取得、バリデーション、env 切替ヘルパー is_live/is_paper/is_dev）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証トークン取得/リフレッシュ機能（get_id_token, モジュールレベルのトークンキャッシュ）。
  - レート制御（固定間隔スロットリング: 120 req/min を想定する RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回、対象: 408/429/5xx、429 の Retry-After 優先）。
  - 401 時はトークン自動リフレッシュを1回のみ行って再試行（allow_refresh フラグで再帰を防止）。
  - DuckDB へ冪等に保存する save_* 関数群（ON CONFLICT DO UPDATE を利用した重複排除）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias のトレースが可能。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィードから記事を収集して raw_news テーブルに冪等保存する機能（fetch_rss, save_raw_news）。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性確保（utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - URL/SSRF/セキュリティ対策:
    - スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキームとホストの事前検証を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかどうかを判定して拒否（DNS 解決・IP 検査）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - URL 正規化・本文前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）。
  - DB 側はチャンク挿入、トランザクション/ロールバック、INSERT ... RETURNING を用いて実際に挿入された件数を正確に返す。
  - 新規記事と銘柄の紐付け機能（save_news_symbols / _save_news_symbols_bulk）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py を追加。
  - DataPlatform.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - 検索効率のためのインデックス定義群。
  - init_schema(db_path) によりディレクトリ自動作成と冪等的なテーブル作成を行う。get_connection() で既存 DB に接続。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py を追加（差分更新・バックフィル・品質チェックの統合設計）。
  - ETLResult データクラスを提供（取得/保存件数、品質問題リスト、エラー一覧、ヘルパーメソッド）。
  - 差分更新ユーティリティ（テーブル存在確認、最大日付取得）と市場カレンダーを参照した営業日調整ロジックを実装。
  - run_prices_etl の差分ロジック（最終取得日から backfill_days 前を date_from にする等）や J-Quants からの取得と保存のフローを用意。
  - id_token の注入可能性、テスト容易性を考慮した設計。

- テスト/拡張を想定した設計
  - news_collector._urlopen をモック可能にしてテストで差し替え可能。
  - jquants_client の id_token 注入や allow_refresh により単体テストでの挙動制御が可能。

### Security
- 外部データ処理に対するセキュリティ対策を多数実装:
  - defusedxml による XML パース（XML基盤攻撃対策）。
  - SSRF 防止（スキーム検証、プライベートIP 判定、リダイレクト時の検査）。
  - HTTP レスポンスサイズ上限と gzip 解凍後サイズチェック（メモリ DoS / Gzip bomb 対策）。
  - URL 正規化によるトラッキングパラメータ除去。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

Notes:
- 本リリースは基盤実装にフォーカスしており、strategy / execution / monitoring サブパッケージはモジュールのエントリを提供していますが、具体的なアルゴリズムや実行ロジックは今後のリリースで拡張予定です。
- DB スキーマや API 仕様はドキュメント（DataPlatform.md 等）に基づいて設計されています。実運用に入る前に接続設定（.env）や権限・バックアップポリシーの確認を推奨します。

---

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/