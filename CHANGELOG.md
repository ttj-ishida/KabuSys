CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------

- なし

0.1.0 - 2026-03-21
------------------

Added
- 初回リリース: 基本的な日本株自動売買ライブラリを提供
  - パッケージメタ情報
    - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
    - 公開 API モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを追加。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行い、CWD に依存しない実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - クォートなし値のインラインコメント判定（直前が空白/タブの場合）をサポート
  - 読み込み時に OS 環境変数（protected set）を上書きしないオプションをサポート。
  - Settings クラスを追加し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH 等にデフォルト値。
    - KABUSYS_ENV 値検証（development / paper_trading / live）、LOG_LEVEL 検証（DEBUG/INFO/...）。
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しのための HTTP ユーティリティを実装（urllib ベース）。
  - レート制限コントロール: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
  - リトライポリシー: 指数バックオフ付き最大リトライ（3 回）、408/429/5xx 系はリトライ対象、429 の場合 Retry-After を優先。
  - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして再試行（無限再帰防止フラグあり）。
  - ページネーション対応で全ページを取得するループを実装（pagination_key を利用）。
  - get_id_token: J-Quants のリフレッシュトークンから ID トークンを取得（POST）。
  - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存関数:
    - save_daily_quotes: raw_prices への冪等保存（ON CONFLICT DO UPDATE）、fetched_at を UTC (Z 表記) で記録。
    - save_financial_statements: raw_financials への冪等保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar への冪等保存（ON CONFLICT DO UPDATE）。
    - PK 欠損レコードはスキップし警告ログを出力。
  - データ型変換ユーティリティ (_to_float/_to_int) を追加し、安全な変換処理を提供。

- ニュース収集ユーティリティ（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集に必要なユーティリティを追加。
  - セキュリティ・堅牢化:
    - defusedxml を利用し XML 関連攻撃から保護。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を抑制。
    - URL 正規化関数 _normalize_url を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - トラッキングパラメータ除去のプレフィックス一覧を定義（utm_ / fbclid / gclid 等）。
  - データ保存方針や設計（記事IDは正規化 URL の SHA-256 先頭 32 文字、DB トランザクションまとめて保存、バルク挿入チャンク等）を明記（実装の一部ユーティリティを提供）。

- 研究用ファクター計算（src/kabusys/research/factor_research.py、feature_exploration.py）
  - calc_momentum / calc_volatility / calc_value を実装:
    - モメンタム: mom_1m/mom_3m/mom_6m、MA200 乖離率（cnt_200 によるデータ十分性チェック）。
    - ボラティリティ: ATR(20)・相対ATR(atr_pct)・20日平均売買代金(avg_turnover)・出来高比(volume_ratio) を計算。true_range は high/low/prev_close が揃っている場合にのみ算出。
    - バリュー: raw_financials から target_date 以前の最新財務情報を取得し PER/ROE を算出（EPS が 0 または欠損のときは None）。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から指定ホライズンに対する将来リターンを計算（まとめて1クエリで取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（同順位は平均ランクで扱う）。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを提供。
  - 実装上の設計は DuckDB の prices_daily / raw_financials を参照し、外部 API に依存しないことを明記。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の raw factors（calc_momentum/calc_volatility/calc_value）を統合して features テーブル用の特徴量を作成。
  - ユニバースフィルタを実装（最低株価 300 円、20 日平均売買代金 >= 5 億円）。
  - 正規化: zscore_normalize（kabusys.data.stats）を用いて指定カラムを Z スコア正規化し ±3 でクリップ。
  - features テーブルへの書き込みは日付単位で完全置換（DELETE + INSERT をトランザクション内で実行）し冪等性を確保。
  - ルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用する方針。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算し BUY / SELL シグナルを生成。
  - スコア計算:
    - momentum/value/volatility/liquidity/news のコンポーネントスコアを算出（シグモイド変換・逆転等）。
    - デフォルト重みを定義（momentum:0.4, value:0.2, volatility:0.15, liquidity:0.15, news:0.1）。
    - weights 引数によるオーバーライドを許容し、無効値は無視、合計が 1.0 に補正。
    - コンポーネントが欠損の場合は中立値 0.5 で補完して不当な降格を防止。
  - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（必要な最小サンプル数のチェックあり）。
  - SELL（エグジット）判定:
    - ストップロス（終値 / avg_price - 1 < -8%）優先
    - final_score が threshold 未満のとき score_drop として SELL
    - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - 将来的にトレーリングストップや時間決済を追加するための注記あり（未実装）
  - signals テーブルへの書き込みは日付単位で置換（トランザクション + バルク挿入）し冪等性を確保。
  - generate_signals は features が空の場合に BUY を生成せず SELL 判定のみ行うなどの堅牢化を実装。

- モジュール公開（src/kabusys/research/__init__.py、src/kabusys/strategy/__init__.py）
  - 主要な関数群（calc_momentum/volatility/value、zscore_normalize、calc_forward_returns、calc_ic、factor_summary、rank、build_features、generate_signals）をパッケージ公開。

Logging / Observability
- 各処理で適切に logger を利用して情報・警告・デバッグを出力。
- DuckDB 保存処理や API 呼び出しで成功件数・スキップ件数をログ出力。

Notes / Design decisions
- DuckDB をメインのストレージとして使用（関数は DuckDB 接続を受け取る）。
- ルックアヘッドバイアス対策として、各処理は target_date 時点で利用可能なデータのみを参照する設計。
- 外部依存は最小化（標準ライブラリ中心）し、セキュリティに配慮した実装（XML パーサ保護・受信サイズ制限・URL 正規化等）を行う。

Fixed
- なし（初回リリース）

Changed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- defusedxml を使用した RSS パースなど、外部入力に対する安全対策を導入。

作者注
- ソース中の docstring とコメントに設計方針や未実装の拡張ポイント（トレーリングストップ、時間決済など）が記載されており、将来的な機能追加に備えた拡張性を確保しています。