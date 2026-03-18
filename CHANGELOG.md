CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット方針:
- バージョンは semver を想定
- 日付はリリース日（YYYY-MM-DD）
- 各項目はなるべく簡潔に記載

[Unreleased]
------------

0.1.0 - 2026-03-18
------------------

Added
- パッケージ基盤
  - 初期バージョン 0.1.0 を追加。パッケージ名: kabusys。
  - 公開 API: kabusys.__all__ に data, strategy, execution, monitoring を定義。

- 環境設定 (kabusys.config)
  - .env/.env.local を自動読み込みする設定管理を追加。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して自動検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
  - .env パーサーは以下をサポート/配慮:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントや # の扱い（クォート有無での違いを考慮）
    - 読み込み失敗時は警告を出力
    - override/protected オプションで OS 環境変数の保護を実装
  - Settings クラスを提供（settings インスタンス）
    - J-Quants / kabu API / Slack / DB パス等の取得メソッドを提供
    - 必須環境変数未設定時は ValueError を送出
    - KABUSYS_ENV / LOG_LEVEL の値検証（許可値セットを限定）
    - duckdb/sqlite のパスを Path 型で取得
    - is_live / is_paper / is_dev のプロパティを追加

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装
    - 固定間隔スロットリングによるレート制限制御（120 req/min）
    - ページネーション対応で全件取得
    - リトライロジック（指数バックオフ、最大3回）。HTTP 408/429/5xx をリトライ対象に設定
    - 401 発生時は ID トークンを自動リフレッシュして 1 回再試行（無限再帰防止）
    - ID トークンのモジュールレベルキャッシュを実装しページネーション間で共有
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供
    - JSON デコードエラーやネットワークエラーを適切に扱う
  - DuckDB への保存関数を実装（冪等保存）
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による上書き挿入
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
    - saved 件数ログ出力や PK 欠損によるスキップ警告を実装
  - ユーティリティ関数
    - _to_float / _to_int: 安全な型変換（不正値は None）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得して raw_news / news_symbols に保存するパイプラインを実装
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）およびバッファ越え検出
    - gzip 圧縮対応（解凍後もサイズ検査）
    - SSRF 対策:
      - URL スキームは http/https のみ許可
      - リダイレクト時にスキームとホストを検査するカスタム HTTPRedirectHandler を導入
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否（DNS 解決した全 A/AAAA レコードを検査）
    - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - テキスト前処理: URL 除去、空白正規化
    - RSS の pubDate をパースして UTC naive datetime に正規化（失敗時は現在時刻で代替）
    - save_raw_news: INSERT ... RETURNING id を用い、実際に挿入された記事 ID のリストを返す（チャンク & 1 トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols をチャンクで INSERT ... RETURNING により保存（重複は ON CONFLICT でスキップ）
    - 銘柄コード抽出: 4 桁数字パターン (\b\d{4}\b) を用い、known_codes によるフィルタで有効コードのみ抽出
    - run_news_collection: 複数ソースを順次取得し、個別にエラーハンドリングして継続する設計

- データスキーマ (kabusys.data.schema)
  - DuckDB 用 DDL を定義（Raw Layer の主要テーブル）
    - raw_prices: 日次株価（PK: date, code）、非負チェック制約等
    - raw_financials: 財務データ（PK: code, report_date, period_type）
    - raw_news: ニュース記事（PK: id）
    - raw_executions: 発注/約定系テーブル定義の断片を含む（CHECK 制約等）
  - Data 層の 3 層構造（Raw / Processed / Feature / Execution）の方針コメントを追加

- リサーチ機能 (kabusys.research)
  - feature_exploration.py を実装
    - calc_forward_returns: LEAD を用いて将来リターン（複数ホライズン）を一括取得
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3 レコード）や分散ゼロは None を返す
    - rank: 同順位は平均ランクにする実装。丸め誤差対策で round(v, 12) を採用
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算（None は除外）
    - いずれも外部ライブラリに依存せず標準ライブラリのみで実装（duckdb コネクションを受け取る設計）
  - factor_research.py を実装
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。データ不足時は None
    - calc_volatility: 20日 ATR / ATR/price（atr_pct） / 20日平均売買代金 / 出来高比率を計算
    - calc_value: 最新の財務データ（raw_financials）と当日の株価を組み合わせて PER / ROE を計算（EPS が 0 または欠損のときは None）
    - 各ファクターは prices_daily / raw_financials テーブルのみ参照する設計（発注 API 等にはアクセスしない）
    - 各種窓関数・LAG/AVG/COUNT を用いた SQL 実装とスキャン範囲バッファ（カレンダー日数の余裕）を導入

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集における SSRF 対策、defusedxml の利用、レスポンスサイズ制限などセキュリティ上の配慮を多数導入。

Notes / Known limitations
- calc_value: PBR・配当利回りは現バージョン未実装（コメントあり）。
- 一部テーブル定義（raw_executions など）はファイル断片のため、実運用ではスキーマの完全確認が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装のため、大規模データでの最適化は今後の課題。
- J-Quants クライアントは _BASE_URL が固定（https://api.jquants.com/v1）。設定のカスタマイズが必要な場合は拡張を検討。

開発者向けメモ
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト時に便利）。
- news_collector._urlopen はテスト時にモック可能（注釈あり）。
- J-Quants API のレート制御は _RateLimiter で単純な固定間隔スロットリングを採用（今後トークンバケット等への変更余地あり）。

以上。