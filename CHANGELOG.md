# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを導入。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョン情報を `__version__ = "0.1.0"` に設定。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を起点）。
  - 自動で .env / .env.local を読み込む機構を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、行末コメントの取り扱い等に対応。
    - 無効行（コメント行や不正行）はスキップ。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト時に便利）。
  - 環境変数取得ユーティリティ `Settings` を提供:
    - 必須変数の取得 (`_require`): 未設定時は ValueError を発生。
    - J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを提供。
    - `KABUSYS_ENV` の許容値チェック（development / paper_trading / live）。
    - `LOG_LEVEL` の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DB パスはデフォルトで `data/kabusys.duckdb`（DuckDB）および `data/monitoring.db`（SQLite）を使用。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔の RateLimiter（120 req/min）を導入。
    - HTTP リクエストの共通処理 `_request` を実装。JSON デコードエラー処理、最大リトライ（指数バックオフ）を実装。
    - 401 受信時にリフレッシュトークンから ID トークンを自動更新して 1 回リトライするロジック。
    - リトライ対象ステータス（408, 429, 5xx）に対する指数バックオフ、429 の場合は Retry-After ヘッダを優先。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務諸表）
      - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 挿入は冪等性を保つ（ON CONFLICT DO UPDATE / DO NOTHING を使用）。
    - fetched_at を UTC ISO8601 で記録し、取得タイムスタンプを保存（Look-ahead バイアス追跡用）。
    - 型変換ユーティリティ `_to_float` / `_to_int` を提供（不正値は None）。
    - PK 欠損行のスキップとログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを導入（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリDoSを軽減。
    - URL の正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート）。
    - HTTP/HTTPS 以外のスキーム拒否、SSRF を考慮した安全性設計（注: 実装済みのユーティリティを含む）。
  - DB 保存はトランザクションでまとめ、チャンク化してバルク挿入（_INSERT_CHUNK_SIZE）を実施。挿入数の正確なカウントを念頭に実装。

- 研究用ファクター計算（kabusys.research）
  - ファクター計算モジュールを追加（prices_daily / raw_financials を参照する純粋関数群）。
  - calc_momentum:
    - mom_1m / mom_3m / mom_6m / ma200_dev を計算。200日データ不足時は None。
  - calc_volatility:
    - 20日 ATR（atr_20）・相対 ATR（atr_pct）・20日平均売買代金（avg_turnover）・出来高比率（volume_ratio）を計算。
    - true_range の NULL 伝播制御により過大評価を防止。
  - calc_value:
    - target_date 以前の最新財務データと当日の株価を組み合わせて PER / ROE を計算。
    - EPS が 0/欠損のとき PER は None。
  - これら関数は list[dict] を返し、外部依存なしで研究環境で利用可能。

- 特徴量探索（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズン検証: 1〜252）。
  - IC（Information Coefficient）計算 calc_ic（スピアマン ρ、サンプル不足時は None を返す）。
  - ランク関数 rank（同順位は平均ランク。丸め誤差対策に round(v, 12) を使用）。
  - factor_summary による統計サマリー（count/mean/std/min/max/median）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 関数を実装:
    - research の calc_momentum / calc_volatility / calc_value を組み合わせて特徴量を作成。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定列（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）することで冪等性と原子性を担保（トランザクション使用）。
    - 欠損値および非有限値の取り扱いを明示。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 関数を実装:
    - features と ai_scores を組み合わせて、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネント計算にはシグモイド変換（Z スコア → [0,1]）や PER の特殊処理を利用。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と閾値（default 0.60）をサポート。ユーザ渡しの weights は検証・補完・再スケールされる。
    - Bear レジーム判定（AI レジームスコア平均が負、十分なサンプル数がある場合）で BUY シグナル抑制。
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が threshold 未満の場合に SELL。
      - 価格欠損時は SELL 判定全体をスキップして誤クローズを防止。
    - BUY / SELL の signals テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクション）して冪等性を確保。
    - SELL 優先ポリシー（SELL 対象は BUY から除外、ランク再付与）を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- XML 外部実行攻撃（XML Bomb 等）対策に defusedxml を採用。
- RSS の URL 正規化でトラッキングパラメータを除去し、記事 ID を安定的に生成できる設計（重複挿入防止に寄与）。
- ニュース収集で受信サイズを制限しメモリ DoS を軽減。
- J-Quants クライアントは認証トークンの自動更新とレート制御、リトライを導入して堅牢化。

### Notes / Usage hints
- 自動 .env 読み込みはデフォルトで有効。CI やテストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings のプロパティ経由で取得すると ValueError で早期に検出できます。
- DuckDB 側スキーマ（raw_prices / raw_financials / features / ai_scores / signals / positions / market_calendar 等）は本リリースの関数が期待するカラム構成に従って事前に準備してください。
- research 系関数は本番の発注処理や外部 API とは無関係に動作する設計です（データベースの prices_daily / raw_financials のみ参照）。

## Deprecated
- （該当なし）

## Removed
- （該当なし）

## Closed issues / Known limitations
- ニュース → 銘柄の自動紐付け（news_symbols）や一部のエグジット条件（トレーリングストップ、時間決済）は実装で未対応。positions テーブルに peak_price / entry_date が必要となるため、将来的に拡張予定。
- 一部の入力検証・エラー処理は改善の余地あり（例: 外部 API の細かな失敗原因の取り扱いログ等）。

その他、細かなロギングや入力検証が各モジュールに実装されています。今後のリリースではテストケース追加、欠損データ処理の堅牢化、実行層（execution）やモニタリング（monitoring）の機能追加を予定しています。