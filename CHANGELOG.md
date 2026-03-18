KEEP A CHANGELOG
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
参照: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

（現在なし）

0.1.0 - 2026-03-18
-----------------

初回リリース。パッケージ "KabuSys" の基本機能を実装しました。以下の主要な機能・モジュールが追加されています。

Added
- パッケージ基本情報
  - kabusys.__version__ = "0.1.0"
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: export 形式、クォート文字列、インラインコメント等に対応する堅牢なパース処理。
  - Settings クラスによる型付きプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証。
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）や環境判定ユーティリティ（is_live 等）。

- データ取得 / 保存 (kabusys.data)
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API レート制限管理: 固定間隔スロットリング（120 req/min を尊守する RateLimiter）。
    - リトライロジック: 指数バックオフ、最大再試行回数、HTTP ステータスに応じた再試行制御（408/429/5xx を考慮）。
    - 401 レスポンス時のトークン自動リフレッシュ（1 回だけ試行）。モジュールレベルでの ID トークンキャッシュを実装。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ変換ユーティリティ: _to_float, _to_int（不正値や空文字に堅牢）
    - Look-ahead-bias を避けるために fetched_at を UTC で記録。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィード取得と前処理パイプラインの実装。
    - セキュリティ対策:
      - defusedxml を使用して XML Bomb 等に対処。
      - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム・ホスト検査、プライベート IP への接続拒否。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_, fbclid 等）除去、クエリソート、フラグメント削除。
    - 記事ID 生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字で冪等性を保つ。
    - テキスト前処理: URL 除去・空白正規化。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id をチャンク単位で実行し、新規に挿入された記事IDを正確に返す。トランザクション単位でまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク INSERT で冪等に保存（RETURNING を利用）。
    - 銘柄コード抽出: 4 桁数字の正規表現抽出と既知コードフィルタリング（extract_stock_codes）。
    - 統合ジョブ: run_news_collection で複数 RSS ソースを順次処理し、エラーをソース単位で分離して他ソースは継続。

- 研究用・特徴量計算 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から各ホライズン（デフォルト: 1,5,21 営業日）までの将来リターンを DuckDB の prices_daily から一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時の安全ハンドリング（有効レコード < 3 → None）。
    - rank: 同順位は平均ランクを返す安定したランク関数（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出（None 値除外）。
    - 設計方針: pandas 等の外部ライブラリに依存せず、DuckDB のみを参照して Research 環境で動作。
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ行不足時は None を返す。
    - calc_volatility: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を正確に扱う実装。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し、per（株価/EPS）と roe を算出。EPS が 0・NULL の場合は per を None に。
    - 設計方針: prices_daily / raw_financials のみ参照。本番発注 API にはアクセスしない。結果は (date, code) をキーとする辞書リストとして返す。
  - research パッケージの __all__ に主要関数をエクスポート（zscore_normalize は kabusys.data.stats から提供）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema に基づく DDL を追加（Raw / Processed / Feature / Execution 層を意識）。
  - raw_prices, raw_financials, raw_news などのテーブル定義を含む DDL を実装（制約・型・PRIMARY KEY を定義）。
  - 初期化用モジュールとしての土台を提供。

Security
- ニュース収集における SSRF 防止、XML パースの安全化（defusedxml）、受信データサイズの制限、URL スキーム検証など多層的な防御を実装。
- J-Quants クライアントは認証トークンの安全な取り扱いと自動リフレッシュ、レート制限を実装。

Notes / Implementation details
- DuckDB への保存処理は可能な限り冪等に設計（ON CONFLICT 句）しており、重複データ挿入や再実行に耐える。
- RSS 記事 ID はトラッキングパラメータを除去した正規化 URL を基にハッシュ生成しているため、同一記事の重複登録を抑制可能。
- Research モジュールは外部ライブラリに依存せず、軽量でテストしやすい形で実装。
- 設定に必須の環境変数が不足している場合は明確な ValueError を送出して早期に検出できる。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- 上記 "Security" の節を参照。

Acknowledgments
- 本リリースはデータ収集、研究用ファクター計算、環境設定、及び基本的なデータスキーマをカバーする土台実装です。今後、strategy・execution・monitoring モジュールの実装拡充や単体テスト・統合テストの追加を予定しています。