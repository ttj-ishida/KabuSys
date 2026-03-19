# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムの基盤となるモジュール群を追加しました。主な追加点と設計上の注記を以下にまとめます。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py を追加。バージョンを "0.1.0" として定義し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に登録。

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ（コメント、export プレフィックス、クォート・エスケープ、インラインコメントの扱い等）を実装し、堅牢にパース。
    - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）とログレベル検証機能を公開。
    - 必須環境変数未設定時には明示的に ValueError を送出。

- Data レイヤー（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py を追加。
    - API 呼び出し用の汎用 _request 実装（JSON パース、固定間隔レートリミッタ、再試行ロジック（指数バックオフ）、429 の Retry-After 処理、401 に対するトークン自動リフレッシュ（1 回））。
    - _RateLimiter によるレート制御（120 req/min のスロットリング）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等性確保のため ON CONFLICT DO UPDATE を使用）。
    - 型安全な変換ユーティリティ _to_float / _to_int を実装（空値・不正値の扱いを明確にし、"1.0" などの文字列変換に配慮）。

- Data レイヤー（ニュース収集）
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード収集機能（fetch_rss）を実装。defusedxml を用いた安全な XML パース、gzip 解凍処理、Content-Length / 実際読み込みサイズの上限チェック（MAX_RESPONSE_BYTES = 10MB）を実装し、Gzip bomb や大容量レスポンス対策を導入。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検査用ハンドラ、プライベートアドレス判定（IP と DNS 解決の両面）により内部ネットワークへのアクセスを防止。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事 ID 生成（正規化 URL の SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news テーブルへ冪等挿入する save_raw_news（INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING を用い、実際に挿入された ID を返す）を実装。チャンク分割、1 トランザクションでの挿入、例外時のロールバックをサポート。
    - 記事と銘柄コードの紐付け用 save_news_symbols / _save_news_symbols_bulk を実装（重複除去・チャンク挿入・RETURNING を使用して正確な挿入数を取得）。
    - テキストからの銘柄コード抽出関数 extract_stock_codes（4桁数字パターンと known_codes によるフィルタリング）を実装。
    - run_news_collection により複数 RSS ソースの収集・保存・銘柄紐付けを統合。ソース単位で例外を捕捉し、1 ソース失敗でも他ソース継続。

- Research（特徴量・ファクター）
  - src/kabusys/research/feature_exploration.py を追加。
    - calc_forward_returns: DuckDB の prices_daily を参照して指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。ホライズン検査・最大ホライズンによるスキャン範囲最適化を実装。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。None・非有限値を除外し、有効レコード数が3未満の場合は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク関数。丸め（round(v,12)）で浮動小数の誤差対策。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を計算するユーティリティ（None 値を除外）。

  - src/kabusys/research/factor_research.py を追加。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を prices_daily に基づいて計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range を正しく扱う実装）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。欠損値取り扱いと cnt による閾値判定を実装。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し、PER（EPS が 0 または欠損時は None）、ROE を計算。prices_daily との結合で日付基準の評価を行う。
    - それぞれ DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計で、本番発注 API 等にはアクセスしない方針。

  - src/kabusys/research/__init__.py を追加し、主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をエクスポート。

- DuckDB スキーマ初期定義
  - src/kabusys/data/schema.py を追加。
    - Raw Layer のスキーマ DDL を定義（raw_prices, raw_financials, raw_news, raw_executions を含む）。各テーブルに対して適切な型・チェック制約・PK を設定。DataLayer/Processed/Feature/Execution 層の設計方針を明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集時:
  - defusedxml を利用した XML パースで XXE 等の脆弱性に対策。
  - SSRF 対策（スキーム検証、プライベートアドレス検査、リダイレクト時の検証）。
  - レスポンスサイズと gzip 解凍後サイズの上限チェック（DoS / Zip bomb 対策）。
- J-Quants クライアント:
  - トークン自動リフレッシュ時の再帰防止（allow_refresh フラグ）を実装。

### Notes / Implementation details
- 設計方針として、Research や Data モジュールは本番発注 API にはアクセスしない（安全性とテスト容易性）。
- DuckDB を主要なデータストアとして利用し、冪等性のために SQL の ON CONFLICT を多用。
- 外部依存は最小限に抑え（標準ライブラリ中心）、defusedxml や duckdb といった必要最小限のライブラリを使用。
- 一部ファイルはパッケージ構成を示す __init__.py のみ（strategy / execution の初期プレースホルダ）を含む。

---

今後の予定（例）
- Strategy 層の戦略実装とバックテスト基盤の追加
- execution 層（kabuステーション連携）の実装（注文送信、約定ハンドリング、ポジション管理）
- モニタリング（Slack 通知など）の具体化

もし CHANGELOG に付記してほしい細かな点（実際のリリース日、著者、影響範囲のラベルなど）があれば教えてください。