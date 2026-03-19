CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このドキュメントはコードベースの内容（ソース内コメントや実装）から推測して作成した初版の変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
-------------------

初回リリース。日本株自動売買システム "KabuSys" のコア機能を含む初期実装を追加。

Added
- パッケージ基本情報
  - パッケージバージョン: 0.1.0
  - パッケージトップレベル: kabusys（submodules: data, strategy, execution, monitoring）

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - OS 環境変数は保護され、.env.local による上書きが可能（ただし保護済みキーは上書きされない）。
  - 自動読み込みの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ: export 形式対応、シングル/ダブルクォート内のエスケープ処理、コメント処理等を実装。
  - 必須環境変数チェック（_require）と Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などをプロパティで取得
    - デフォルト値: KABUSYS_ENV=development、KABU_API_BASE_URL=http://localhost:18080/kabusapi、LOG_LEVEL=INFO 等
    - env/log_level の値検証（有効な値集合をチェック）
    - データベースパスプロパティ: duckdb_path / sqlite_path

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を固定間隔スロットリングで強制（RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回）。408/429/5xx を対象に再試行。
    - 401 受信時は自動でリフレッシュトークンを用いて ID トークンを再取得し1回リトライ。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - JSON デコードエラーやネットワークエラーのハンドリング。
  - データ保存ユーティリティ（DuckDB 向け、冪等性を考慮した実装）
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE（date, code を PK と想定）
    - save_financial_statements: raw_financials テーブルへ冪等保存（code, report_date, period_type PK 想定）
    - save_market_calendar: market_calendar テーブルへ冪等保存
  - 入力変換ユーティリティ _to_float / _to_int（堅牢なパース）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得して raw_news テーブルへ保存する機能（設計に基づく実装部分）。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防ぐ
    - 受信最大バイト数の制限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、キーソート）
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保
    - HTTP/HTTPS 以外のスキーム拒否や SSRF 対策の考慮
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）
    - Volatility: 20日 ATR / atr_pct、avg_turnover、volume_ratio
    - Value: per（price / eps）、roe（最新財務データ）
    - DuckDB の window/lead/lag 等を活用した SQL ベース実装
  - 特徴量探索・解析（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（horizons デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ 相当をランクで算出）
    - factor_summary（count/mean/std/min/max/median）と rank（同順位は平均ランク）
    - 標準ライブラリのみでの実装方針（pandas 等に依存しない）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research モジュールの calc_momentum/calc_volatility/calc_value を組み合わせて features を生成
    - ユニバースフィルタ: 最低株価 (_MIN_PRICE = 300 円)、20日平均売買代金 >= 5e8 円
    - 正規化: kabusys.data.stats.zscore_normalize を利用、対象カラムを Z スコア化し ±3 でクリップ
    - features テーブルへ日付単位の置換（BEGIN / DELETE / INSERT / COMMIT）で原子性を確保
    - 冪等性を意識した実装（target_date の既存行を削除してから挿入）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - スコア変換ユーティリティ: シグモイド、平均化（欠損値は中立 0.5 で補完）
    - デフォルト重み (_DEFAULT_WEIGHTS) を持ち、ユーザ指定 weights を検証・マージ・再スケール
    - Bear レジーム判定: ai_scores の regime_score 平均が負でかつサンプル数が閾値以上の場合に BUY を抑制
    - BUY シグナル: final_score >= threshold（Bear レジーム時は BUY 抑制）
    - SELL シグナル（エグジット判定）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - 価格欠損や position 情報欠落時の扱いに注意（ログ出力）
    - signals テーブルへ日付単位の置換（トランザクションで原子性確保）
    - SELL 優先ポリシー: SELL 対象を BUY から除外してランクを再付与
  - ロギングと警告を多用し、無効な weight 値やデータ欠損を明示

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- J-Quants クライアントおよびニュース収集処理において再試行/トークンリフレッシュ/XML パース対策/レスポンスサイズ制限など安全性を考慮した実装を導入。

Notes / Known limitations / TODOs（コード内コメントより推測）
- signal_generator のエグジット条件で未実装の項目:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- calc_value: PBR や配当利回りは未実装
- news_collector: RSS 取得や記事→銘柄の紐付け（news_symbols）等の周辺処理は実装想定だが、ここに含まれていない追加実装が必要
- execution 層（kabusys.execution）はパッケージに含まれているが実装内容は提示されていない
- 外部統計ユーティリティ（kabusys.data.stats.zscore_normalize）は参照されているがソースはここに含まれていない（別モジュールで提供）

補足
- 本 CHANGELOG はソースコード内のコメント・設計文書的説明・実装から推測して作成したもので、実際のコミット履歴に基づくものではありません。実際のリリースに合わせて日付・詳細・カテゴリを更新してください。