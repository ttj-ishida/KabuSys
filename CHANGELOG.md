Keep a Changelogに準拠した CHANGELOG.md（日本語）
すべての注目すべき変更はこのファイルに記録します。

フォーマット:
- 変更はセマンティックに「Added / Changed / Fixed / Security / Removed / Deprecated」などに分類しています。
- すべてのリリースは日付を付与しています。

[Unreleased]
- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-18
Added
- 初期リリース。パッケージ名: kabusys（__version__ = 0.1.0）。
- パッケージ公開インターフェースを定義:
  - kabusys.__all__ に data, strategy, execution, monitoring を含める。
  - 空のパッケージモジュール（strategy, execution）を配置し将来的な拡張に対応。
- 環境設定管理:
  - kabusys.config: .env/.env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml を基準に判定）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサ実装: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォートあり/なしの差分扱い）。
  - Settings クラスを提供し、J-Quants や kabu API、Slack、DB パス等の設定プロパティを取得。KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値チェック）。
- データ取得・永続化（DuckDB）:
  - kabusys.data.jquants_client:
    - J-Quants API クライアント実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得関数）。
    - レート制限制御: 固定間隔スロットリング（120 req/min、_RateLimiter）。
    - リトライ戦略: 指数バックオフを用いた最大 3 回リトライ（408/429/5xx を対象）、429 の場合は Retry-After を尊重。
    - 401 時の自動トークンリフレッシュ（1 回だけ）とトークンキャッシュの共有（モジュールレベル）。
    - ページネーション対応（pagination_key 利用）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE による重複排除。
    - データ整形ユーティリティ _to_float / _to_int を用意し不正値を None に変換。
    - fetched_at は UTC の ISO 時刻で記録。
  - kabusys.data.schema:
    - DuckDB スキーマ定義（Raw Layer 等）を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
- ニュース収集（RSS）:
  - kabusys.data.news_collector:
    - RSS フィードから記事を収集し raw_news テーブルへ保存する一連の機能を実装。
    - セキュリティ/堅牢性対策:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検査（SSRF 対策）。
      - ホストのプライベートアドレスチェック（DNS 解決して A/AAAA レコードを評価）。プライベート/ループバック等は拒否。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - User-Agent 指定、Accept-Encoding 対応、リダイレクトハンドラによる追加検証。
    - URL 正規化: トラッキングパラメータ（utm_, fbclid 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート。
    - 記事ID の生成: 正規化 URL の SHA-256 を用いた先頭 32 文字で冪等性を保証。
    - 記事テキストの前処理（URL 除去・空白正規化）。
    - 銘柄コード抽出: 正規表現による 4 桁数字抽出と known_codes によるフィルタリング。
    - DB 保存はチャンク単位で INSERT ... RETURNING を使用し、トランザクションでまとめて実行。ON CONFLICT DO NOTHING により重複をスキップし、実際に挿入された記事IDや紐付け数を正確に返す。
    - 外部に公開するデフォルト RSS ソース定義（例: Yahoo Finance）。
- リサーチ（特徴量・ファクター計算）:
  - kabusys.research.feature_exploration:
    - calc_forward_returns: DuckDB 上の prices_daily を参照して各ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一クエリで取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ結合は code ベース、None や非有限値を除外、有効サンプル数が 3 未満なら None を返す。
    - rank: 同順位は平均ランクで扱い、丸め（round(..., 12)）で浮動小数の ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を計算（None 除外）。
  - kabusys.research.factor_research:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。ウィンドウ内のデータ不足時は None。
    - calc_volatility: ATR(20) の単純平均、相対 ATR（atr_pct）、20日平均売買代金、当日出来高 / 平均出来高（volume_ratio）を計算。true_range の NULL 伝播を厳密に扱う（high/low/prev_close のいずれかが NULL なら true_range は NULL）。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER (close / eps)、ROE を計算。EPS が 0 または欠損なら PER は None。
    - 各関数は DuckDB の prices_daily / raw_financials のみを参照し外部 API へはアクセスしない設計。
  - kabusys.research.__init__ で主要関数を再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および kabusys.data.stats.zscore_normalize を公開する設計になっている（zscore_normalize の実装は data 側に想定）。
- ロギング・エラーハンドリング:
  - 各モジュールで logger を利用した debug/info/warning/exception ログ出力を実装。失敗時の例外伝播は適切に行い、DB 操作はトランザクションでロールバック。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- RSS 取得での SSRF 対策、XML パースの安全化、レスポンスサイズ制限、gzip 解凍後サイズチェックなど多数の防御を実装。
- .env の読み込みは OS 環境変数を保護する protected セットを用いた上書き制御をサポート。

Notes / Implementation details
- DuckDB に依存した設計（DuckDBPyConnection を引数にとる関数が多い）。
- J-Quants API クライアントは urllib を用いた同期実装。非同期版は未提供。
- 一部（例: data.stats.zscore_normalize）のユーティリティは再エクスポートされているが、実装箇所は別モジュール（data）で提供される想定。

Removed / Deprecated
- 初版のため該当なし。

Acknowledgements
- 本変更ログはソースコードの内容から推測して作成しています。実際の設計書やドキュメントと差分がある可能性があります。必要であればリリース日や細かい分類を調整します。