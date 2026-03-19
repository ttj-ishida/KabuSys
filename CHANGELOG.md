# Changelog

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の方針に従っており、セマンティックバージョニングを採用しています。

## [Unreleased]
- （現時点のコードベースは初回リリース向けの機能群が含まれています。新規変更はここに記載します）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点をモジュール別にまとめます。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py にてバージョン（0.1.0）と公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 設定管理
  - kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索）。
    - ロード順は OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行解析器を実装（export プレフィックス対応、クォート内部のエスケープ、インラインコメント処理）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等をプロパティで取得。値検証あり（KABUSYS_ENV, LOG_LEVEL）。
    - 必須環境変数未設定時は明確な ValueError を投げるヘルパーを用意。
- Data モジュール（DuckDB / 外部 API 連携）
  - kabusys/data/schema.py
    - DuckDB 用のスキーマ定義（Raw Layer）を追加（raw_prices, raw_financials, raw_news 等の DDL）。（注: raw_executions 定義はファイル内に続きがあるが本CHANGELOGでは現状の定義を反映）
  - kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - レート制限（デフォルト 120 req/min）を守る固定間隔スロットリング（内部 RateLimiter）。
    - リトライロジック（最大3回、指数バックオフ、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は ID トークンを自動リフレッシュして1回だけ再試行する仕組み（無限再帰防止）。
    - ページネーション対応の fetch_XXX 関数を追加:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB への冪等保存関数を追加:
      - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存（fetched_at を UTC の ISO 形式で記録）。
      - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE。
      - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE（HolidayDivision を解釈して is_trading_day/is_half_day/is_sq_day を設定）。
    - 文字列→数値変換ユーティリティ (_to_float, _to_int) を実装（安全な変換、空値や不正フォーマットは None を返す。_to_int は "1.0" など小数表現を許容するが非整数は None）。
    - トークンキャッシュをモジュールレベルで保持し、ページネーション中でも共有。
  - kabusys/data/news_collector.py
    - RSS フィードからニュースを収集して raw_news / news_symbols に保存する一連の処理を実装。
    - セキュリティ・堅牢性:
      - defusedxml を使用して XML Bomb 等の攻撃を防止。
      - SSRF 対策: リダイレクト時のスキーム/ホスト検査を行う _SSRFBlockRedirectHandler、事前のホストプライベート判定、許可スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の上限検査（Gzip Bomb 対策）。
      - URL 正規化でトラッキングパラメータ（utm_* 等）を除去し、記事ID を SHA-256 の先頭32文字で生成して冪等性を確保。
    - フィード処理機能:
      - fetch_rss: RSS 取得・パース（エラーハンドリング、名前空間・content:encoded の扱い、pubDate のパース）を実装。
      - preprocess_text: URL 除去・空白正規化を実装。
      - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事ID一覧を返す（チャンク/トランザクション処理）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンクで保存（ON CONFLICT で重複排除、INSERT ... RETURNING により実際の挿入数を取得）。
      - extract_stock_codes: 正規表現 \b(\d{4})\b で 4 桁銘柄コード候補を抽出し、known_codes でフィルタリング。重複除去を行う。
      - run_news_collection: 複数ソースを順に処理し、ソース単位でのエラーハンドリング（1ソース失敗でも他は継続）、銘柄紐付けは新規挿入記事に対して一括処理。
- Research モジュール（特徴量・因子計算）
  - kabusys/research/feature_exploration.py
    - calc_forward_returns: DuckDB の prices_daily を参照して、指定基準日から複数ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括クエリで取得。ホライズンの妥当性チェック（1〜252）を実施。
    - calc_ic: ファクター値と将来リターンの結合による Spearman ランク相関（IC）を計算。None・非有限値を除外し、有効レコード数が3未満なら None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（round(v,12) により丸めて ties 検出の安定化）。
    - factor_summary: 指定カラムについて count/mean/std/min/max/median を計算（None 値除外）。外部ライブラリに依存せず標準ライブラリのみで実装。
    - 設計方針として DuckDB の prices_daily のみ参照し、本番発注 API 等にはアクセスしないことを明記。
  - kabusys/research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率（ma200_dev）を DuckDB クエリで計算。過去データが不足する銘柄は None を返す。ウィンドウスキャン範囲をバッファ付きで限定。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を適切に制御し、十分なデータがない場合は None を返す。
    - calc_value: raw_financials の target_date 以前の最新財務データと prices_daily を組み合わせ、PER（eps が 0/欠損なら None）と ROE を計算。DuckDB の ROW_NUMBER による最新財務選択を使用。
    - 定数（期間・スキャン幅）と設計方針（外部 API 非依存、結果は (date, code) キーの dict リスト）を明確化。
  - kabusys/research/__init__.py
    - 重要なユーティリティとファクター計算関数をパッケージ外へ公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Security
- ニュース収集における SSRF 対策を実装（ホストプライベート判定、リダイレクト前後での検査、許可スキームの制限）。
- XML パースに defusedxml を使用して XML 関連攻撃を軽減。
- RSS レスポンスサイズの上限チェックおよび gzip 解凍後のサイズ検査を実装（DoS 対策）。
- J-Quants API クライアントは Authorization トークンの自動刷新を実装し、不正なリクエストやトークン失効時の適切な処理を行う。

### Notes / Known limitations
- schema.py 内の raw_executions テーブル定義はファイル末尾で途切れており、実装が未完了の可能性がある。実際に使用する場合はスキーマの完全性を確認してください。
- research モジュールは外部ライブラリ（pandas など）に依存しない実装を目指しているため、大規模データ処理時のパフォーマンスや機能面で最適化の余地がある。
- jquants_client の RateLimiter は固定間隔スロットリング（最小間隔）を用いるため、API のバースト許容設定やより複雑なレート制御を必要とする場合は拡張が必要。
- news_collector の extract_stock_codes は単純に4桁数字を抽出する実装であり、文脈誤検出やコード形式の特殊ケース（銘柄コード以外の数字列）については追加フィルタが望まれる。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

---
プロジェクトの今後:
- schema の続き（execution/position 系テーブル）、strategy および execution モジュールの実装拡張、テスト・ドキュメント整備、パフォーマンス改善、外部依存（必要に応じて pandas 等）検討を予定しています。ご要望や不具合報告は issue を立ててください。