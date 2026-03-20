CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、リポジトリ内のコードから推測される最初のリリース内容・重要事項を日本語でまとめたものです。

フォーマット:
- Unreleased: 今後の変更予定（現時点ではなし）
- 各リリースは日付付きで記載

Unreleased
----------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring（execution は placeholder）

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定: .git または pyproject.toml を親ディレクトリから探索
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパース実装（コメント、export プレフィックス、引用符付き値、インラインコメント、エスケープ対応）
  - 環境変数必須チェック用 _require() と Settings クラスを提供
    - 必須環境変数（使用箇所から推定）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - パス等のデフォルト:
      - KABU_API_BASE_URL デフォルト "http://localhost:18080/kabusapi"
      - DUCKDB_PATH デフォルト "data/kabusys.duckdb"
      - SQLITE_PATH デフォルト "data/monitoring.db"
    - バリデーション:
      - KABUSYS_ENV は development / paper_trading / live のいずれか
      - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか

- Data 層: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API 用 HTTP ユーティリティを実装
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライ実装（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）
    - 401 受信時は id_token の自動リフレッシュを 1 回行って再試行
    - ページネーション対応（pagination_key）
    - レスポンス JSON デコードエラーハンドリング
  - 高水準 API:
    - get_id_token(refresh_token: Optional) → idToken を取得
    - fetch_daily_quotes(...) → 日足データをページネーションで取得
    - fetch_financial_statements(...) → 財務データをページネーションで取得
    - fetch_market_calendar(...) → 市場カレンダー取得
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes(conn, records): raw_prices へ冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records): raw_financials へ冪等保存
    - save_market_calendar(conn, records): market_calendar へ冪等保存
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換、Invalid は None）

- Data 層: ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news へ保存するためのユーティリティ実装（Research/DataPlatform 設計に準拠）
  - 機能:
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
    - defusedxml による XML パース（XML Bomb などへの対策）
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）
    - SSRF 対策（HTTP/HTTPS スキーム以外拒否等、ホスト検査の意図が示唆されている）
    - バルク INSERT のチャンク化で DB オーバーヘッドを抑制

- Research 層 (kabusys.research)
  - ファクター計算と評価用ツールを実装
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均の必要行数チェックを含む）
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（ATR の欠損ハンドリング）
    - calc_value(conn, target_date): per, roe（raw_financials の target_date 以前の最新レコードを使用）
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（複数ホライズン）を一度のクエリで取得
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）計算（有効サンプル < 3 は None）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
    - rank(values): 同順位は平均ランクを返す（丸めで ties を安定化）
  - 設計方針:
    - DuckDB の prices_daily / raw_financials のみ参照
    - 外部ライブラリに依存しない実装（pandas 等を使用しない）

- Strategy 層 (kabusys.strategy)
  - 特徴量生成 (kabusys.strategy.feature_engineering)
    - build_features(conn, target_date):
      - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを統合
      - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5 億円）を適用
      - 指定カラムを Z スコア正規化し ±3 でクリップ（zscore_normalize を利用）
      - features テーブルへ日付単位で置換（トランザクション + bulk insert、冪等）
    - デザイン:
      - ルックアヘッドバイアス対策として target_date 時点のデータのみ使用
  - シグナル生成 (kabusys.strategy.signal_generator)
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を組み合わせ、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - sigmoid 変換、欠損コンポーネントは中立 0.5 で補完
      - final_score を重み付き合算（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数の場合）で BUY を抑制
      - BUY: final_score >= threshold（Bear 時は抑制）
      - SELL: positions（最新）に対してストップロス（-8%）および score が閾値未満の場合にエグジット判定
      - signals テーブルへ日付単位で置換（トランザクション + bulk insert、冪等）
    - 重みの取り扱い:
      - ユーザー指定 weights は検証（未知キーや負値・非数値を無視）、既知キーのみ許容、合計が 1.0 になるよう再スケール
    - ロギングとエラーハンドリング（COMMIT/ROLLBACK 対応、ROLLBACK 失敗時は警告）

Changed
- 初版のため「Changed」はなし

Fixed
- 初版のため「Fixed」はなし

Deprecated
- なし

Removed
- なし

Security
- ニュース収集: defusedxml を使用して XML 関連の攻撃（XML Bomb 等）を防止
- ニュース収集: URL 正規化とトラッキングパラメータ除去、受信サイズ制限、HTTP スキーム検証により SSRF/DoS のリスク低減
- J-Quants クライアント: 401 発生時の自動トークンリフレッシュ処理の導入により認証切れ対策
- 環境変数ローダー: OS 環境変数を保護する protected ロジックを実装（override フラグの挙動）

注記 / マイグレーションガイド（初回セットアップ）
- 必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / SQLite の初期スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は本リリースの各モジュールの期待に合わせて作成してください。
- 自動 .env ロードを無効にしたい場合（テスト等）は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の有効値: development, paper_trading, live
- LOG_LEVEL は大文字で DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかにしてください。

今後の予定（推測）
- execution 層の実装（発注 API との統合）
- monitoring モジュールの具体的実装（Slack 通知・メトリクス収集）
- features / signals 周りのユニットテスト強化、トレードルールの追加（トレーリングストップ・時間決済など）

お問い合わせ
- この CHANGELOG はコードベースから推測して作成しています。実装の意図や仕様に齟齬がある場合は該当コードを参照してください。