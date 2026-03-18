# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

※ 日付は初回リリース日を示します。

## [Unreleased]


## [0.1.0] - 2026-03-18

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ を設定し、data/strategy/execution/monitoring を公開。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git / pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサは export KEY=val 形式、クォート文字列、インラインコメントの扱いを考慮した堅牢な実装。
  - Settings クラスを提供し、必須値取得時は未設定で ValueError を送出。環境 (development/paper_trading/live) やログレベルの検証ロジックを含む。
  - デフォルトの DB パス（DuckDB/SQLite）など便利なプロパティを提供。
- Data モジュール: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証: get_id_token によるリフレッシュトークンからの idToken 取得、モジュールレベルのトークンキャッシュを実装。
  - リトライ/バックオフ: ネットワーク/一部 HTTP ステータスに対する指数バックオフおよび最大リトライ試行を実装。
  - 401 受信時は id_token を自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を RateLimiter で実装。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE で保存。
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE で保存。
  - データ型変換ユーティリティ (_to_float/_to_int) を提供。変換ポリシー（空値は None、"1.0" を int に変換する等）を明示。
- Data モジュール: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news/raw_news_symbols への保存処理を実装。
  - フィード取得: XML を defusedxml で安全にパースし、gzip に対応。最大受信バイト数制限（10MB）や gzip 解凍後サイズチェックを行い DoS 対策を実装。
  - SSRF 対策:
    - フェッチ前にホストがプライベートアドレスでないか検証。
    - リダイレクト検査用のカスタム HTTPRedirectHandler を導入してリダイレクト先も検証。
    - 許可されるスキームは http / https のみ。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を保証。URL 正規化ではトラッキングパラメータ（utm_* 等）を削除、クエリをソート、フラグメント除去を行う。
  - テキスト前処理: URL 除去・空白正規化を行う preprocess_text を提供。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id をチャンク単位で実行し、実際に挿入された記事IDを返却。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT RETURNING を使用）。
  - 銘柄抽出ユーティリティ: 4桁数字パターンに基づく extract_stock_codes（known_codes によりフィルタ、重複除去）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。
  - run_news_collection: 全ソースを個別に処理し、ソース単位でエラーハンドリング。known_codes を渡すと自動で銘柄紐付けを実行。
- Research モジュール (src/kabusys/research/*.py)
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank を実装（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト 1/5/21 日）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが3未満なら None を返す。
    - rank: 同順位は平均ランクを返す実装。浮動小数点丸め（round(v,12)）で ties 検出の精度を改善。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
    - feature_exploration は標準ライブラリのみで実装（pandas等に依存しない）。
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr / close）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials より target_date 以前の最新財務を取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - いずれも DuckDB の prices_daily / raw_financials のみ参照し、外部 API や発注 API にはアクセスしない設計。
  - research パッケージの __init__ で主要関数をエクスポート。
- DuckDB スキーマ定義・初期化ヘルパ (src/kabusys/data/schema.py)
  - Raw レイヤ（raw_prices, raw_financials, raw_news, raw_executions など）の DDL を定義。
  - テーブル定義には制約（CHECK / PRIMARY KEY）やデフォルトタイムスタンプを設定。

### Security
- ニュース収集における SSRF 対策を導入（ホストプライベート判定、リダイレクト検査、許可スキーム制限）。
- XML パースに defusedxml を使用して XML-Bomb 等の攻撃を軽減。
- RSS レスポンスの受信上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェックでメモリ DoS を防止。
- .env 読み込みでは OS 環境変数を保護する protected 機構を導入。

### Performance / Reliability
- J-Quants クライアントに固定間隔レートリミッタを実装し API レート(120 req/min)を厳守。
- API リクエストはページネーションを考慮し、ページ間でトークンを共有するため一貫して動作。
- 大量挿入処理はチャンク化して一括 INSERT を行い、トランザクションでまとめて処理。INSERT ... RETURNING により実際に挿入された件数を正確に取得。
- DuckDB への保存は冪等性を確保（ON CONFLICT DO UPDATE / DO NOTHING）。

### Notes / Limitations
- research/feature_exploration は標準ライブラリのみで実装しているため、pandas 等の利便性は利用していない（軽量で依存を減らす設計）。
- 一部のテーブル定義や機能は今後拡張予定（例: Strategy / Execution / Monitoring 周りの公開パッケージは存在するが詳細実装は今後）。
- calc_forward_returns の horizons は最大 252 を上限とするバリデーションを実施。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

---

今後のリリースでは、戦略実行 (execution)、モニタリング、より高度なファクター群や UI/運用ツール連携等を追加予定です。必要であれば、各モジュールの詳細な設計ドキュメントや使用例（コードスニペット）を追記します。