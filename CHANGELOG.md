# Changelog

すべての著名な変更はこのファイルに記載します。本ドキュメントは「Keep a Changelog」仕様に準拠します。  
現在のバージョン: 0.1.0

※ 日付はパッケージの初回リリース日です。

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース。主要コンポーネント・機能を実装。
  - kabusys
    - __init__.py によりパッケージの基本情報（__version__ = 0.1.0）を公開。
  - 環境設定管理 (kabusys.config)
    - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - .env パーサ実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート対応（バックスラッシュエスケープ処理含む）
      - インラインコメントの扱い（クォートあり/なしの差異を考慮）
    - Settings クラスを提供（環境変数からアクセスするプロパティ群）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値
      - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - Data 層 (kabusys.data)
    - jquants_client:
      - J-Quants API クライアント実装（ページネーション対応）。
      - レート制限: 固定間隔スロットリングで 120 req/min を遵守。
      - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を再試行対象。
      - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（トークン再取得の無限再帰防止あり）。
      - fetch_*/save_* 系 API:
        - fetch_daily_quotes / save_daily_quotes → raw_prices テーブルへ（ON CONFLICT DO UPDATE で冪等）
        - fetch_financial_statements / save_financial_statements → raw_financials テーブルへ（冪等）
        - fetch_market_calendar / save_market_calendar → market_calendar テーブルへ（冪等）
      - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス対策を考慮。
      - 入出力値の安全な数値変換ユーティリティ (_to_float / _to_int) を提供。
    - news_collector:
      - RSS フィード収集モジュールの実装（デフォルトに Yahoo Finance のビジネス RSS を登録）。
      - defusedxml を利用して XML 関連攻撃対策を実施。
      - URL 正規化 (_normalize_url): トラッキングパラメータ除去 (utm_*, fbclid, gclid 等)、スキーム/ホストの小文字化、フラグメント除去、クエリソート。
      - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や HTTP スキーム制限等の安全対策を実装。
      - DB へのバルク INSERT はチャンク化して実行し、挿入件数を正確に返す設計。
  - Research 層 (kabusys.research)
    - ファクター計算・探索用モジュールを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する純データ処理）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。
      - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損なら PER は None）。
      - 各ファンクションはウィンドウのデータ不足判定（必要行数未満 → None）を行う。
    - feature_exploration:
      - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用、存在しない場合は None）。
      - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル不足 (<3) は None。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
      - rank: 同順位は平均ランクで処理（丸め誤差対策に round(v, 12) を使用）。
    - research パッケージは zscore_normalize を含む外部ユーティリティと連携。
  - Strategy 層 (kabusys.strategy)
    - feature_engineering.build_features:
      - research で算出した生ファクターを統合し、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - _NORM_COLS の数値カラムを zscore 正規化し ±3 でクリップ（zscore_normalize を利用）。
      - features テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性を保証）。
      - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
    - signal_generator.generate_signals:
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - コンポーネントの補完ルール: 欠損は中立値 0.5 で補完。
      - final_score はデフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を使用。ユーザ指定 weights は検証して補完・正規化される。
      - BUY シグナル閾値デフォルト 0.60。Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3）では BUY シグナルを抑制。
      - SELL シグナル（エグジット判定）:
        - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
        - スコア低下: final_score < threshold
      - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
  - パッケージの公開 API:
    - kabusys.strategy で build_features / generate_signals を __all__ で公開。
    - kabusys.research で主要関数群を __all__ で公開。

Changed
- 初回リリースにつき、既存コードの「導入（Added）」が主。外部仕様として:
  - DuckDB を主なデータストアとして想定（関数は DuckDB 接続を引数に取る）。
  - 外部依存は最小化（research モジュールは pandas 等に依存しない実装）。
  - logging による詳細な情報・警告出力を充実。

Fixed
- 該当なし（初回リリース）。

Security
- news_collector で defusedxml を使用、RSS パース時の XML 攻撃対策を実装。
- RSS 取得時の最大応答サイズ制限、URL のスキームチェック、SSRF を抑制するためのホスト/IP 検査等を想定した安全設計（実装済みの一部ユーティリティあり）。
- J-Quants クライアントでトークン管理・自動リフレッシュ・レート制御を実装し、不正アクセス・過負荷を防ぐ措置を含む。

Notes / Known limitations
- strategy.signal_generator の SELL 条件としてコード内に未実装の項目がコメントとして残っています:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有日数判定、positions に entry_date が必要）
  これらは positions テーブル側の拡張および追加のメタデータが必要。
- calc_value は PBR・配当利回りを未実装（コメント参照）。
- news_collector は URL 正規化や記事 ID 生成等を実装しているが、実運用ではフィードごとのエッジケース（非標準フィールド、エンコーディング差異）を追加ハンドリングする可能性あり。
- 環境変数検証は基本的な型/値チェックまでを実装。追加のバリデーションが必要なケース（トークンフォーマットなど）は将来対応予定。
- jquants_client におけるリトライ対象ステータスは (408, 429, 5xx) に限定。サービスの仕様変更により調整が必要になる場合あり。
- news_collector の一部セキュリティ関連（IP ホワイトリスト/ブラックリスト、DNS rebinding 対策など）は設計方針で触れているが、現実運用環境に合わせた追加対策を推奨。

Dependencies
- 実行にあたり以下が必要/推奨:
  - duckdb
  - defusedxml
  - 標準ライブラリ（urllib, datetime, logging 等）
- 外部パッケージ（pandas 等）には依存しないことを設計方針で明記。

今後の予定 / TODO
- positions テーブルのメタデータ拡張（peak_price, entry_date 等）を行い、trailing stop / time-based exit を実装。
- feature エンジニアリングやスコア計算の単体テスト充実化。
- news_collector のフィードパース耐性強化（各ソース固有フォーマットの正規化）。
- 運用観点での監視・メトリクスの追加（SLACK 通知の利用など）。

脚注
- 本 CHANGELOG はコードコメント・設計コメントから推測して作成しています。実際のリリースノートとして使う場合は、デプロイ・実行テスト結果やリリース担当者による確認を行ってください。