Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる変更・追加点、設計上の注意点をまとめています。

※バージョンはパッケージ内の __version__ = "0.1.0" に基づき初版を 0.1.0 としました。日付は本日（2026-03-19）を設定しています。適宜差し替えてください。

----------------------------------------------------------------------
CHANGELOG
----------------------------------------------------------------------

全ての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[Unreleased]
- （なし）

[0.1.0] - 2026-03-19
Added
- パッケージ初期リリース "kabusys"（kabusys 0.1.0）
  - パッケージ公開用の __init__.py を追加し、サブパッケージとして data, strategy, execution, monitoring をエクスポート。
- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索してルートを特定。
  - .env パース機能を実装（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理など）。
  - 自動ロード時の優先順位: OS環境変数 > .env.local > .env。OS環境変数を保護するための protected キーセットをサポート。
  - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応（テスト向け）。
  - Settings クラスを追加し、J-Quants / kabu / Slack / データベースパスなど主要設定をプロパティで提供。KABUSYS_ENV と LOG_LEVEL の値検証（有効値集合）を実装。
- データ取得 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min、モジュール内 RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3、対象ステータス（408, 429, 5xx）に対応。
  - 401 Unauthorized 受信時にリフレッシュトークンで ID トークンを更新して 1 回リトライする仕組みを実装（無限再帰防止のため allow_refresh フラグを使用）。
  - ページネーション対応のフェッチ関数を追加:
    - fetch_daily_quotes (株価日足、ページネーション)
    - fetch_financial_statements (四半期財務データ、ページネーション)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存ユーティリティを追加:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE で保存
  - 入力パースユーティリティ (_to_float, _to_int) を追加し、欠損値や不正入力に対する堅牢性を確保。
  - fetched_at を UTC 形式で保存し、データの「いつ知り得たか」をトレース可能に。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得する fetch_rss を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト時のスキーム検証とプライベートアドレス判定を実装（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後のサイズもチェック。
    - User-Agent と Accept-Encoding 指定、Content-Length チェック。
  - テキスト前処理機能（URL 除去、空白正規化）を実装 (preprocess_text)。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）により記事IDを SHA-256（先頭32文字）で生成し冪等性を担保。
  - DB 保存機能:
    - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事 ID リストを返す（チャンク処理、1 トランザクション）。
    - news_symbols 関連: save_news_symbols と内部バルク保存 _save_news_symbols_bulk（チャンク処理、ON CONFLICT DO NOTHING, INSERT RETURNING）。
  - 銘柄コード抽出ユーティリティ (extract_stock_codes) を実装（4桁数字パターンと既知コードによるフィルタリング）。
  - 統合ジョブ run_news_collection を実装（各ソース独立エラーハンドリング、known_codes による銘柄紐付け）。
- リサーチモジュール (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: DuckDB の prices_daily を参照して指定日から各ホライズン先の将来リターンを一括取得（1/5/21日がデフォルト）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。NaN/None/非有限値をフィルタリングし、有効レコードが3未満の場合は None を返す。
    - rank: 同順位は平均ランクとするランク付けを実装（丸めで ties 検出漏れを低減）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
    - 標準ライブラリのみでの実装方針を明記（pandas 等に依存しない）。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。必要データが不足する銘柄は None を返す。
    - calc_volatility: 20日 ATR 平均、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER（close / eps）と ROE を計算（EPS が 0/欠損の場合は None）。
  - research パッケージの __all__ に主要関数 (calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank) を公開。zscore_normalize は kabusys.data.stats から提供されるユーティリティを想定してインポート。
  - すべてのリサーチ関数は prices_daily / raw_financials テーブルのみを参照し、本番発注 API 等にはアクセスしない設計を明記（Look-ahead防止の方針）。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw Layer の主要テーブル DDL を追加:
    - raw_prices（date, code, open, high, low, close, volume, turnover, fetched_at、PRIMARY KEY (date, code)）
    - raw_financials（code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at、PRIMARY KEY (code, report_date, period_type)）
    - raw_news（id, datetime, source, title, content, url, fetched_at、PRIMARY KEY (id)）
    - raw_executions（開始定義あり、発注・約定データ向けスキーマのスケルトン）
  - スキーマは DataSchema.md に基づく 3層構造（Raw / Processed / Feature / Execution）を想定した構成。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- defusedxml による XML パース、SSRF 対策、レスポンスサイズ制限、Gzip 解凍後のサイズ検査など、外部データ取り込みに関する多数の安全対策を導入。
- ニュース取得における外部 URL 正規化とトラッキング除去により ID 決定の安定化とプライバシー配慮を実施。

Notes / 開発者向け補足
- 環境変数:
  - 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - Settings クラスは必須変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を _require により検証します。CI/デプロイ環境ではこれらを確実にセットしてください。
- J-Quants API:
  - レート制限 (120 req/min) を厳守します。大量取得時はページネーションと _RateLimiter の仕様を考慮してください。
  - 429 取得時は Retry-After ヘッダを優先してリトライ待機時間を計算します。
  - get_id_token は refresh_token を settings.jquants_refresh_token から取得します。テスト時は明示的に id_token を渡すことで自動リフレッシュを抑制できます。
- DuckDB 保存:
  - raw_news の保存はチャンク化して 1 トランザクションで行い、INSERT ... RETURNING で実際の新規挿入を正確に検出します。
  - raw_prices / raw_financials などは ON CONFLICT DO UPDATE を用いて冪等に保存します。
- ニュース収集:
  - fetch_rss は XML パース失敗やセキュリティ上の判定で空リストを返すことがあります。run_news_collection はソース単位で障害を切り離して継続処理します。
  - 銘柄抽出は単純な 4 桁数字パターンに基づきます。known_codes を与えない場合は紐付けがスキップされます。
- リサーチ:
  - feature_exploration は外部ライブラリ非依存（標準ライブラリのみ）で実装されており、軽量に組み込み可能です。
  - rank 関数は浮動小数点の丸め誤差対策として round(v, 12) を用いて ties を検出します。
- 未実装 / TODO（コードから推測）
  - strategy/ と execution/ パッケージの中身（発注ロジック、約定管理、ポジション管理）は空の __init__ のみで、実装は今後追加予定。
  - data.stats モジュール（zscore_normalize の定義）がこの差分に含まれていないため、別途実装済みであるか、今後追加が必要。

----------------------------------------------------------------------

参考:
- 各モジュール内の docstring に設計方針・制約が多く記載されています。実運用前に設定値・DB スキーマ・API トークン管理を必ず確認してください。