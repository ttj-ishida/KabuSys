CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
バージョン番号はパッケージの __version__ = "0.1.0" に基づきます。

[Unreleased]
------------

（なし）

0.1.0 - YYYY-MM-DD
------------------

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主にデータ収集、ファクター計算、特徴量生成、シグナル生成、ならびに研究用ユーティリティを提供します。

Added
- パッケージエントリポイント
  - kabusys.__init__ を追加。公開モジュールとして data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（デフォルト有効）。
  - .env ファイルの堅牢なパース実装（コメント、export プレフィックス、クォート・エスケープ対応）。
  - OS 環境変数を保護する protected 上書き制御、override 動作のサポート。
  - 必須環境変数チェック機能（_require）。
  - settings オブジェクトを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
  - 固定間隔スロットリングによるレート制限制御（120 req/min）。
  - 再試行（指数バックオフ）、HTTP 408/429/5xx を対象に最大3回リトライ。
  - 401 を検知した場合の自動トークンリフレッシュ（1 回）と再試行。
  - ページネーション対応（pagination_key）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT による上書き）。
  - 値変換ユーティリティ（_to_float / _to_int）を実装し、入出力の堅牢性を向上。
  - レスポンスの取得タイミング（fetched_at）を UTC で記録し、Look-ahead バイアスの追跡を可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集基盤を実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - 記事ID生成ポリシー（URL 正規化後の SHA-256 ハッシュ先頭等）により冪等性を確保。
  - URL 正規化：スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリソート。
  - defusedxml を利用した XML パースによるセキュリティ対策（XML Bomb など）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や SSRF を考慮した URL ハンドリング、DB 挿入のバルク処理とチャンク化。
  - raw_news / news_symbols 等への冪等保存設計（ON CONFLICT DO NOTHING / INSERT RETURNING を想定）。

- 研究用ユーティリティ（kabusys.research）
  - factor_research: prices_daily / raw_financials を用いたファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio
    - calc_value: PER / ROE（raw_financials の最新レコードから取得）
  - feature_exploration: 研究用の解析ユーティリティを実装
    - calc_forward_returns: 任意ホライズンの将来リターン取得（ホライズン検証あり）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算
    - factor_summary: 各ファクター列の basic statistics（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返すランク関数（丸め誤差対策あり）
  - research.__init__ で主要 API を再公開（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した生ファクターを結合・ユニバースフィルタ（最低株価・平均売買代金）を適用。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへの日付単位置換（トランザクション + バルク挿入）により冪等性・原子性を担保。
  - 実行 API: build_features(conn, target_date) -> upsert 件数を返す。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - final_score を重み付き合算（デフォルト重みは StrategyModel.md Section 4.1 に準拠）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負）により BUY を抑制。
  - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）シグナルの生成。
  - positions テーブルを参照して保有ポジションのエグジット判定を行い、signals テーブルへ日付単位で置換保存（トランザクション内で DELETE -> INSERT）。
  - generate_signals(conn, target_date, threshold=..., weights=...) -> 書き込みシグナル数を返す。
  - ユーザー指定 weights のバリデーション・補完・再スケール処理を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュースパーサで defusedxml を使用し XML 関連攻撃を緩和。
- RSS URL 正規化とトラッキングパラメータ除去により不要な外部呼び出しや追跡を低減。
- J-Quants クライアントでタイムアウト、リトライ、トークンリフレッシュ制御を実装し、セキュリティ面・堅牢性を向上。

Notes / Known limitations
- 売却（エグジット）の一部条件は将来的に追加予定（コード内コメント参照）:
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
- feature_engineering / signal_generator / data コードは DuckDB の既定テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, raw_financials, market_calendar など）のスキーマに依存します。スキーマ準備が必要です。
- news_collector と jquants_client の一部はネットワーク／外部 API に依存するため、実行環境でのキーや接続設定が必須です（下記の環境変数を参照）。

Migration / Configuration
- 必須環境変数（主に settings で _require を通じて参照される）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意設定:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- 自動 .env 読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

API まとめ（主な公開関数）
- settings (kabusys.config.Settings インスタンス)
- Data / API:
  - jquants_client.get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - jquants_client.save_daily_quotes, save_financial_statements, save_market_calendar
- News:
  - news_collector の記事収集・正規化機能（関数はモジュール内で提供）
- Research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（research.__init__ 経由で公開）
- Strategy:
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

Authors
- 初回実装（KabuSys チーム／開発者）

ライセンス
- ソース内に明示的なライセンス表記はありません（配布前にライセンス表記を確認してください）。

問い合わせ / 開発ノート
- 追加の機能（トレーリングストップ・時間決済・execution 層との統合等）やテーブルスキーマ定義が必要な場合は issue を起票してください。