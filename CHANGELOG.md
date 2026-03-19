Keep a Changelog に準拠した CHANGELOG.md（日本語）
==============================================

全般
----
- この CHANGELOG はコードベースの現状（バージョン 0.1.0）から推測して作成しています。
- バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づきます。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（kabusys.__all__）
  - バージョン: 0.1.0

- 環境設定 / 自動 .env ロード機能（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索: .git または pyproject.toml を起点に検索するため、CWD に依存しない。
  - .env 解析の強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント処理（クォート外かつ '#' の直前が空白/タブの場合をコメントと扱う）
    - 無効行のスキップ
  - 上書きポリシー:
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - .env.local は .env を上書き（override=True）
    - OS 環境変数を保護する protected キーセットを導入
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを提供し、各種必須/任意設定値をプロパティとして公開（J-Quants トークン、kabu API、Slack、DB パス、環境フラグ、ログレベルなど）
  - 値検証: KABUSYS_ENV / LOG_LEVEL の有効値チェック、未設定必須変数でのエラー送出

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを追加。
  - レート制限制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象にリトライ、429 の場合は Retry-After を考慮。
  - 認証トークン処理:
    - リフレッシュトークン -> ID トークン取得 get_id_token（POST）
    - 401 受信時に自動でトークンをリフレッシュして 1 回リトライ（無限再帰防止）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
  - HTTP ユーティリティ: JSON デコードエラーやネットワークエラーの扱い、タイムアウト、ヘッダ管理等
  - ページネーション対応フェッチ関数:
    - fetch_daily_quotes（株価日足、ページネーション処理）
    - fetch_financial_statements（財務データ、ページネーション処理）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT / DO UPDATE を利用）:
    - save_daily_quotes -> raw_prices テーブルへ保存（fetched_at を UTC ISO）
    - save_financial_statements -> raw_financials テーブルへ保存
    - save_market_calendar -> market_calendar テーブルへ保存（取引日 / 半日 / SQ フラグ）
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換と None ハンドリング）
  - ロギング: 取得件数・警告の出力

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集モジュールを追加（デフォルトソースに Yahoo Finance）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）
    - HTTP/HTTPS スキーム以外拒否（SSRF 緩和）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を抑制
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去する URL 正規化
    - URL 正規化時にスキーム・ホスト小文字化、フラグメント除去、クエリソートを実施
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保
    - gzip 対応、受信コンテンツの前処理（URL 除去・空白正規化）
  - DB への保存戦略:
    - raw_news への冪等保存（ON CONFLICT DO NOTHING）を想定
    - bulk insert のチャンク化（_INSERT_CHUNK_SIZE）で SQL 長・パラメータ数の上限対策
    - トランザクションを 1 回にまとめてオーバーヘッドを削減

- 研究モジュール（kabusys.research）
  - ファクター計算 / 探索ツールを追加（外部依存を持たず標準ライブラリと DuckDB で実装）。
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の存在チェック）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（true range の NULL 伝播制御）
    - calc_value: per / roe（raw_financials の最新レコードを結合）
    - 実装方針: prices_daily / raw_financials のみ参照、欠損時は None を返す
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman ランク相関（IC）計算（有効レコード数が 3 未満なら None）
    - rank: 同順位は平均ランクに変換（round(v,12) による ties 対応）
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算
  - zscore_normalize は kabusys.data.stats から再エクスポート（インポート可能）

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features(conn, target_date): research で計算した生ファクターを統合して features テーブルへ日付単位で原子置換（BEGIN/DELETE/INSERT/COMMIT）
    - データフロー:
      1. calc_momentum / calc_volatility / calc_value で生ファクター取得
      2. ユニバースフィルタ（最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8 円）
      3. 指定カラムの Z スコア正規化（_NORM_COLS）、±3 でクリップ（外れ値抑制）
      4. features テーブルへ UPSERT（日付単位置換）で冪等性を保証
  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して signals を生成し日付単位で置換して保存
    - スコアリング:
      - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重み _DEFAULT_WEIGHTS）
      - 連結処理: sigmoid 変換、欠損コンポーネントは中立値 0.5 で補完
      - weights のバリデーション（既知キーのみ、非数値/負値は無視）、合計が 1.0 でなければ再スケール
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数が閾値を満たす場合は Bear とみなす）
      - Bear レジームでは BUY シグナルを抑制
    - SELL（エグジット）判定:
      - 実装済: ストップロス（終値/avg_price -1 <= -0.08）、スコア低下（final_score < threshold）
      - 保有銘柄の価格欠損時は SELL 判定をスキップ（誤クローズ回避）
    - トランザクションで signals の日付単位置換（DELETE + INSERT の原子実行）
    - ロギングと WARN 出力（feature 欠損・weights 無効値・ROLLBACK 失敗など）

Changed
- （初回リリースのため、変更履歴はなし）

Fixed
- （初回リリースのため、修正履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- ニュース収集で defusedxml を使用して XML 関連の攻撃に対処。
- RSS の URL 検証・スキーム制限や受信サイズ制限で SSRF / DoS リスク低減。
- J-Quants クライアントでトークン管理と HTTP エラー処理（429 の Retry-After 等）を考慮。

注意点 / 既知の制限
- Signal の一部エグジット条件は未実装（コメントに明示）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_symbols（ニュースと銘柄の紐付け）処理の実装詳細はこのスニペット内に含まれていないため、実装/運用時に追加が必要。
- DuckDB テーブル定義（スキーマ）がコードでは示されておりません。実行前にテーブル（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news など）のスキーマを用意してください。
- デフォルトのデータベースパスは Settings で指定（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）。環境に応じて調整してください。

導入・移行メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 上記が未設定の場合 Settings のプロパティ参照で ValueError を送出します。
- 自動 .env ロードをテストや CI 環境で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB にデータを保存する関数は ON CONFLICT/DO UPDATE を使って冪等性を保っていますが、事前に適切な PRIMARY KEY / UNIQUE 制約を用意してください。

問い合わせ / 貢献
- この CHANGELOG はコードスニペットから推測して作成したため、実際のリポジトリの README / ドキュメントと差分がある場合があります。正確なリリースノートは実際の Git 履歴・タグ付けに基づいて発行してください。