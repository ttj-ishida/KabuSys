CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初回リリース（v0.1.0）に含まれる主要な機能・設計上の決定・注意点を日本語でまとめます。

v0.1.0 - 2026-03-19
-------------------

Added
- 基本パッケージ構成
  - パッケージ名: kabusys, バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring（__all__）

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（OS 環境変数 > .env.local > .env の優先度）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメントの扱い（インラインコメント条件付き）
  - 必須値チェック用の _require ヘルパーと Settings クラスを提供
  - 設定プロパティ（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のみ許容）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）

- Data 層: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3（408/429/5xx を対象）
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみリトライ）
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存する save_* 関数:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE（date, code をキー）
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE（code, report_date, period_type をキー）
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE (date をキー)
  - データ変換ユーティリティ: _to_float / _to_int（変換失敗は None）

- Data 層: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード読み取りをベースに原則を実装
  - セキュリティ / 安全対策:
    - defusedxml を利用して XML/Bomb 攻撃を防止
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ(utm_*, fbclid, gclid 等)除去、フラグメント削除、クエリパラメータソート
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ）
  - DB 挿入はチャンク化（_INSERT_CHUNK_SIZE）して性能と SQL 長制限に配慮

- Research 層 (src/kabusys/research/*.py)
  - factor_research: prices_daily / raw_financials を元に主要ファクターを計算
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日ベース）
    - calc_value: per, roe（raw_financials の最新財務データを参照）
    - 設計で「営業日ベースの窓」「スキャン範囲のバッファ」を用い、休日等の欠損に対応
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト: 1, 5, 21 日）の将来リターンを一括で取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効サンプル < 3 の場合は None）
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ
  - これらの関数は外部ライブラリに依存せず、duckdb 接続を受け取って SQL と純 Python 処理で実装

- Strategy 層 (src/kabusys/strategy/*.py)
  - feature_engineering.build_features:
    - research のファクター計算（calc_momentum/calc_volatility/calc_value）を統合
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 数値ファクターを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位で置換アップサート（トランザクション + バルク挿入で原子性を保証）
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）
    - default weights を定義（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）、ユーザー提供 weights は検証・正規化してマージ
    - final_score に対してデフォルト閾値 0.60 で BUY シグナルを生成
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合は BUY を抑制
    - エグジット条件（SELL）:
      - ストップロス（終値/avg_price - 1 <= -8%）
      - final_score が閾値未満
      - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - 保持ポジションが SELL 対象なら BUY から除外（SELL 優先ポリシー）

Changed
- （初回リリースのため「Changed」はなし）

Fixed
- （初回リリースのため「Fixed」はなし）

Security
- ニュース処理に defusedxml を導入して XML による攻撃を防止
- ニュース取得で受信サイズ上限を設け、メモリ DoS を軽減
- J-Quants クライアントで認証トークンの適切なリフレッシュと例外ハンドリングを実装

Notes / Migration / Requirements
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意だが重要な環境変数（デフォルトあり）:
  - KABU_API_BASE_URL, DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
  - KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env ロードを無効化)
- 期待される DuckDB / DB スキーマ（本リリースの関数が参照・更新する主なテーブル）:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news
  - 各関数の SQL コメントや INSERT の ON CONFLICT キーに基づきスキーマを作成してください
- 依存ライブラリ:
  - duckdb, defusedxml（ニュースパーシングで使用）
- J-Quants API に対するレート制御（120 req/min）やリトライポリシーが実装されているため、運用時はローカルでの大量並列化に注意してください。

Known limitations / TODO
- signal_generator の一部のエグジット条件（トレイリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の追加カラムが必要で未実装
- news_collector の SSRF/IP フィルタ等は設計コメントにあり実装の余地がある（将来的な強化ポイント）
- 一部の設計方針（例: INSERT RETURNING を使った正確な挿入件数の算出）はコメントに示されているが、DB 実装環境依存のため追加検証が必要

開発者向け補足
- 各モジュールは発注 API（kabu ステーション等）や execution 層への直接依存を避ける設計になっており、戦略ロジックと実際の発注ロジックを分離しています。
- 研究用ユーティリティ（research/）は外部ライブラリに依存しない実装を方針としており、検証環境での再利用を想定しています。
- ロギングが各モジュールに組み込まれているため、運用時は LOG_LEVEL とログハンドラの設定を行ってください。

以上が v0.1.0 の主な内容です。次のリリースでは未実装のエグジット条件、news_collector の追加セキュリティ検証、より詳細な DB マイグレーションスクリプトなどを予定しています。