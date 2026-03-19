Keep a Changelog
=================
すべての変更はセマンティックバージョニングに従い記録します。  
このファイルは Keep a Changelog の形式に準拠します。

フォーマット
----------
各リリースには以下のカテゴリを含めます: Added, Changed, Fixed, Security, Breaking Changes（該当する場合）。

[Unreleased]
------------

v0.1.0 - 2026-03-19
-------------------

Added
- パッケージの初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境設定/読み込み (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - コメント行、export プレフィックス、引用符あり/なしの値、インラインコメント処理等に対応。
    - 上書き保護（protected）機構により OS 環境変数を保持可能。
  - Settings クラスを導入し、環境変数経由で設定値を提供:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）
    - デフォルト値: KABUSYS_ENV=development、LOG_LEVEL=INFO、KABU_API_BASE_URL=http://localhost:18080/kabusapi
    - DUCKDB_PATH / SQLITE_PATH の既定パスを提供
    - env/log_level の妥当性検証（有効な値の集合を定義）
    - is_live / is_paper / is_dev ユーティリティプロパティ

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - API レート制御: 固定間隔スロットリング（デフォルト 120 req/min）を _RateLimiter で実装
    - リトライ戦略: 指数バックオフ、最大リトライ3回、408/429/5xx を再試行対象
    - 401 応答時の自動トークンリフレッシュ（1回まで）とトークンキャッシュ共有
    - JSON デコードエラーの検出と明示的エラーメッセージ
    - ページネーション対応の fetch_...() 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への冪等保存関数:
      - save_daily_quotes: raw_prices テーブルへ挿入（ON CONFLICT DO UPDATE）
      - save_financial_statements: raw_financials テーブルへ挿入（ON CONFLICT DO UPDATE）
      - save_market_calendar: market_calendar テーブルへ挿入（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float, _to_int（文字列や小数表現の安全な変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプライン実装:
    - フィード取得 (fetch_rss)：
      - defusedxml を利用した安全な XML パース（XML BOM/攻撃対策）
      - 最終 URL のスキーム/ホスト検証、リダイレクト時の事前検査用ハンドラ（SSRF対策）
      - Content-Length および実際のレスポンス長に基づく受信サイズチェック（MAX_RESPONSE_BYTES = 10MB）
      - gzip 圧縮対応と解凍後サイズ再チェック（Gzip bomb 対策）
      - タイトル/本文の前処理: URL 除去、空白正規化
      - 記事IDは正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を確保
      - tracking パラメータ (utm_*, fbclid 等) の除去とクエリソートによる URL 正規化
      - 出力は NewsArticle 型（id, datetime, source, title, content, url）
    - DB保存:
      - save_raw_news: INSERT ... RETURNING id を用いたチャンク挿入（トランザクション）で新規挿入IDを返す
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンクで保存（重複排除, RETURNING による正確な挿入数取得）
    - 銘柄抽出:
      - テキストから4桁数字（日本株銘柄コード）を抽出する extract_stock_codes 実装（known_codes によるフィルタ、重複除去）
    - 集約ジョブ run_news_collection を提供（各ソースを独立に処理、既知銘柄があれば紐付け実行）

- 研究用ファクター処理（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一度のクエリで取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（欠損・非有限値を除外、サンプル数3未満で None）
    - rank: 同位の平均ランク処理（round(..., 12)で丸めて ties の検出精度向上）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
    - 設計ポリシー: pandas 等外部ライブラリに依存せず標準ライブラリのみで実装
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離（ma200_dev）を計算（データ不足時は None）
    - calc_volatility: 20日 ATR（atr_20）, 相対ATR（atr_pct）, 20日平均売買代金 (avg_turnover), 出来高比 (volume_ratio) を計算（トゥルーレンジの NULL 伝播制御）
    - calc_value: raw_financials と当日の株価を組み合わせて PER と ROE を算出（EPS が 0/欠損時は None）
    - 設計ポリシー: DuckDB の prices_daily / raw_financials のみ参照、外部発注APIにはアクセスしない

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw Layer の DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（主キー・制約付き）
  - スキーマ初期化用モジュールの基盤を提供

Security
- RSS ニュース収集における脆弱性対策:
  - defusedxml による安全な XML パース
  - SSRF 対策:
    - リダイレクト先のスキーム/ホスト検証を行う _SSRFBlockRedirectHandler
    - ホスト名→IP の解決結果に基づきプライベート/ループバック/リンクローカル/マルチキャストアドレスをブロック
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）と Gzip 解凍後のチェックで DoS（大容量応答/圧縮爆弾）を緩和
  - URL 正規化とトラッキングパラメータ除去により同一記事の冪等性を担保

Breaking Changes
- なし（初期リリース）

Notes / Migration
- 必須環境変数を必ず設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は起動時に ValueError を送出します。
- 自動 .env 読み込みはプロジェクトルートの検出に __file__ を使用しているため、パッケージ配布後の挙動に配慮しています。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- DuckDB スキーマは初期化処理（schema モジュール）で作成してください。既存データとの互換性やマイグレーションは将来的に追加する予定です。

開発メモ（実装上の設計方針）
- Research / Factor 計算モジュールは外部 API に依存せず、DuckDB のテーブルのみを参照することで本番発注系機能から分離。
- J-Quants クライアントはレート制御とリトライを厳密に実装し、トークンの自動リフレッシュとページネーションをサポート。
- News Collector は安全性（SSRF、XML攻撃、メモリDoS）を重視した実装。
- DB への保存処理は可能な限り冪等にし、ON CONFLICT / INSERT ... RETURNING を活用して正確な更新情報を得る。

お問い合わせ
- 本リリースに関する問題報告や改善提案はリポジトリの Issue にお願いします。