# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このリポジトリの初回公開バージョンは 0.1.0 です。

# [Unreleased]
- （なし）

# [0.1.0] - 2026-03-18
初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加しました。以下は主な追加点・設計上の特徴です。

## Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - __version__ = "0.1.0"
    - パッケージ構成: data, strategy, execution, monitoring をエクスポート対象に設定。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および環境変数から設定を自動で読み込む仕組みを実装。
    - プロジェクトルート判定は __file__ を基点に .git / pyproject.toml を検索するため、CWD に依存しない自動ロード。
    - .env のパースは以下をサポート/考慮:
      - コメント行、export キーワード、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 環境変数を保護する protected 機構（.env.local は既存の OS 環境変数を上書きしない）。
    - Settings クラスを提供（settings インスタンス経由で使用）:
      - J-Quants / kabuステーション / Slack の必須トークン取得（未設定時は ValueError）。
      - DB パス（DUCKDB_PATH, SQLITE_PATH）のデフォルト設定と Path 返却。
      - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL のバリデーション。is_live/is_paper/is_dev プロパティ。

- データ層: J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しユーティリティ（_request）を実装。
      - レート制限制御（固定間隔スロットリング）: 120 req/min に合わせた RateLimiter。
      - リトライロジック（指数バックオフ、最大3回）。408/429/5xx をリトライ対象。
      - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh 制御）。
      - ページネーションを考慮した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - JSON デコード失敗時に明確なエラーを投げる。
    - 認証: get_id_token(refresh_token=None) を提供（settings.jquants_refresh_token を使用）。
    - DuckDB への保存関数（冪等性を考慮）:
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。fetched_at を UTC で記録。
      - save_financial_statements: raw_financials テーブルへ保存（ON CONFLICT DO UPDATE）。
      - save_market_calendar: market_calendar テーブルへ保存（ON CONFLICT DO UPDATE）。HolidayDivision の解釈を記載。
    - 型変換ユーティリティ: _to_float / _to_int（不正値は None を返す。_to_int は小数部が存在する場合は変換せず None を返す）。

- データ層: ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を取得し raw_news / news_symbols に保存する機能。
    - セキュリティ・堅牢性:
      - defusedxml を利用した XML パース（XML Bomb 等に対処）。
      - HTTP リダイレクト時にスキームとホストを検査するハンドラ（_SSRFBlockRedirectHandler）を導入し SSRF を防止。
      - 初期ホスト検査・リダイレクト後の最終 URL 再検証でプライベート IP へのアクセスを拒否。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
      - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去する URL 正規化。
      - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を担保。
    - フィード処理:
      - fetch_rss: RSS 取得→パース→記事リスト変換。content:encoded を優先し、description をフォールバック。
      - preprocess_text: URL 除去、空白正規化。
      - _parse_rss_datetime: pubDate を UTC naive datetime に変換（パース失敗時は現在時刻を代替）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用いて新規挿入記事IDを正確に取得。チャンク化してトランザクションで実行。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ記事-銘柄紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）。
    - 銘柄抽出:
      - extract_stock_codes: 正規表現で 4 桁数字を抽出し、known_codes に含まれるものだけ返す（重複除去）。

- データ層: DuckDB スキーマ定義/初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層の概念に基づくスキーマ定義を追加。
    - Raw layer の DDL を定義:
      - raw_prices（date, code, open, high, low, close, volume, turnover, fetched_at, PK(date, code)）
      - raw_financials（code, report_date, period_type, eps, roe, fetched_at, PK(code, report_date, period_type)）
      - raw_news（id, datetime, source, title, content, url, fetched_at, PK(id)）
      - raw_executions（execution_id, order_id, datetime, code, side, price, size ...）など（実装途中まで含む）
    - DDL は CREATE TABLE IF NOT EXISTS で記述し、型チェック・制約を含む。

- 解析・リサーチ（Research）モジュール
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None)
      - prices_daily テーブルから複数ホライズンの将来リターンを一括クエリで取得。ホライズン検証（正の整数かつ <= 252）。
      - 不足データの場合は None を返す設計。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - ファクターと将来リターンを code で結合し、スピアマンのランク相関（IC）を計算。3レコード未満は None。
      - 内部で rank を使用（同順位は平均ランク、丸め誤差対策に round(v, 12) を使用）。
    - factor_summary(records, columns)
      - 各カラムの count/mean/std/min/max/median を計算（None は除外）。標本分散ではなく母分散（n）で計算。

  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date)
      - mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。データ不足時は None。
      - SQL ウィンドウ関数を活用し LAG / AVG / COUNT を計算。
    - calc_volatility(conn, target_date)
      - atr_20（20日 ATR の単純平均）、atr_pct（ATR / close）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高 / 20日平均）を計算。
      - true_range の NULL 伝播を正確に制御し、十分なデータがない場合は None を返す。
    - calc_value(conn, target_date)
      - raw_financials から target_date 以前の最新財務データを銘柄ごとに取得し、per (price / eps)、roe を計算。EPS が 0 または欠損のときは None。
    - 設計方針:
      - DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（外部 API にはアクセスしない）。
      - 結果は (date, code) をキーとする dict のリストで返す。
      - 研究環境向けに Look-ahead を避ける設計。

  - src/kabusys/research/__init__.py
    - 主要関数をエクスポート: calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats より）、calc_forward_returns, calc_ic, factor_summary, rank。

## Security
- defusedxml を用いた XML パース、RSS fetch 時のサイズ検査、SSRF 対策（リダイレクト時の検証・プライベート IP 拒否）、URL スキーム検証などを盛り込み、外部から取り込むデータに対する防御を強化しています。

## Notes / Design decisions
- DuckDB を中核データストアとして想定し、全てのデータ取得・前処理は DuckDB テーブル（raw_* / prices_daily / raw_financials 等）を参照・更新する設計になっています。
- 本番口座や発注 API へのアクセスはデータ/研究系モジュールでは行わないよう分離（安全・テスト容易性の向上）。
- 外部依存は必要最小限（defusedxml, duckdb）に留め、標準ライブラリで実装できる部分は自前の実装を行っています。
- ニュース収集では記事IDの正規化とハッシュ化により重複登録を防止。news_symbols の紐付けは known_codes を用いて行うため、事前に有効銘柄リストを用意する必要があります。

## Known / TODO
- schema.py の execution 層（raw_executions）の定義は途中まで記述されています。Execution / Strategy 層の実装（発注ロジック、約定管理、ポジション管理など）は今後追加予定です。
- 単体テスト・統合テストの追加（外部 API 呼び出し箇所のモックなど）が必要。
- パフォーマンス改善（大規模データにおける DuckDB クエリ最適化、ニュース抽出時の並列化等）が今後の課題。

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴や設計仕様書に基づく追加情報があれば、より正確な履歴に更新してください。）