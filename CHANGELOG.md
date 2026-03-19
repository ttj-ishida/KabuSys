Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記録しています。

変更履歴
-------

### Unreleased
- （なし）

### [0.1.0] - 2026-03-19
初回リリース。日本株の自動売買基盤に必要なデータ収集・ファクター計算・特徴量生成・シグナル生成・設定管理のコア機能を実装。

Added
- パッケージ基本情報
  - kabusys パッケージ初期化。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に公開。

- 設定管理（kabusys.config）
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込み。
    - プロジェクトルートはこのファイルから起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - OS 環境変数を上書きしないための protected キー保護を実装。
  - .env パーサーは export 形式・シングル/ダブルクォート・エスケープ・インラインコメントなどに対応。
  - Settings クラスを提供し、主要設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして取得。DUCKDB/SQLite パスや環境モード（development / paper_trading / live）、ログレベルの検証あり。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔（120 req/min）レート制御（RateLimiter）。
    - リトライ（最大 3 回）、指数バックオフ、HTTP 408/429/5xx に対する再試行。
    - 401 Unauthorized を受けた際にリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応（pagination_key を使用）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスの追跡を容易にする設計。
  - データ保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装し、DuckDB テーブルへ冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
    - 入力値の型安全な変換ユーティリティ _to_float / _to_int を実装。
    - PK 欠損行はスキップし警告ログを出力。
  - モジュールレベルの ID トークンキャッシュ実装（ページネーション間で共有）。

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する仕組みを実装。
    - デフォルト RSS ソース（Yahoo Finance ビジネス等）。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保（トラッキングパラメータ除去、クエリソート等の正規化を実施）。
    - defusedxml を用いて XML による攻撃（XML Bomb 等）を防止。
    - 受信最大バイト数制限（10 MB）によりメモリ DoS を緩和。
    - HTTP/HTTPS スキーム以外の URL を拒否して SSRF リスクを低減。
    - バルク INSERT のチャンク処理で SQL 長・パラメータ数の上限に配慮。
    - DB 側は ON CONFLICT DO NOTHING を想定して挿入件数の正確把握を行う設計。
  - テキスト前処理（URL 除去・空白正規化）等のユーティリティを提供。

- 研究モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 約1ヶ月/3ヶ月/6ヶ月のリターン、200日移動平均乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を注意深く扱う。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS=0 などは None）。
  - feature_exploration:
    - calc_forward_returns: LEAD を用いた将来リターン（デフォルト horizons = [1,5,21]）の計算。ホライズン検証（1..252）あり。
    - calc_ic: スピアマンのランク相関（IC）を実装。ペアが 3 件未満なら None。ties を平均ランクで扱う。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランク（round(v,12) による tie 検出安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research モジュールで計算した生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z-score 正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップして外れ値を抑制。
    - 日付単位での置換（DELETE + bulk INSERT）で冪等性と原子性を確保（トランザクション実行、ROLLBACK 対応、ログ出力）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features / ai_scores / positions を参照して銘柄別のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - Z スコアはシグモイド変換で [0,1] にマッピング。欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum:0.4, value:0.2, volatility:0.15, liquidity:0.15, news:0.1）を実装。ユーザー指定の weights を検証・マージ・再スケールするロジックを持つ（負値・NaN/Inf や未知キーは無視）。
    - AI の regime_score を集計し、サンプル数が最小要件（3）以上でかつ平均が負なら Bear レジームと判定し BUY を抑制。
    - BUY は threshold（デフォルト 0.60）以上の銘柄をスコア順に採用。SELL は以下のエグジット条件を実施:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
    - positions に関するデータ欠損（avg_price<=0, price 欠損）時は適切にスキップまたは警告を出力。
    - BUY/SELL を signals テーブルへ日付単位で置換して保存（トランザクションで原子性確保）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーシングで defusedxml を使用し XML 関連攻撃を軽減。
- ニュース収集における応答サイズ制限、URL 正規化、スキームチェックにより SSRF / DoS リスクを低減。
- J-Quants API クライアントで認証トークンの自動リフレッシュを実装し、不正な 401 ループを避けるための allow_refresh 制御を導入。

Known issues / TODO
- execution / monitoring サブパッケージは __all__ に含まれているが、execution/__init__.py は空であり、監視周りの実装は未着手または別ファイルで管理予定。
- signal_generator の一部のエグジット条件（トレーリングストップ・時間決済など）は positions テーブルに peak_price / entry_date 等の情報が必要であり、現時点では未実装（記載の通り将来拡張予定）。
- news_collector のコードは URL 正規化等の実装を含むが、RSS のダウンロードやデータベースへの実際のマッピング処理の細部（例: news_symbols への紐付けや INSERT RETURNING の具体的な SQL）は利用環境によって調整が必要な可能性あり。
- 外部依存を最小限にする方針のため、統計処理は標準ライブラリ / duckdb のみで実装。大規模データ処理では pandas 等を使った高速化を検討する余地あり。

注記
- DuckDB を主要なデータストアとして想定しているため、実行環境に duckdb が必要です。
- J-Quants API を利用するには JQUANTS_REFRESH_TOKEN 環境変数の設定が必須です（Settings.jquants_refresh_token が未設定時は ValueError を送出）。
- ログや例外時の振る舞いは各モジュールで logger を使用しており、運用時は適切なログレベル設定（LOG_LEVEL）を推奨します。

---