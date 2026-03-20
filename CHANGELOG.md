CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

（現時点のコードベースは初回リリース v0.1.0 としてまとめられています。以降の変更はここに追記してください。）

0.1.0 - 2026-03-20
------------------

初回公開リリース。日本株向け自動売買・データ基盤のコア機能を実装しています。以下はコードベースから推測される主要な追加点・設計方針・既知の前提です。

Added
- パッケージ基盤
  - kabusys パッケージ初期バージョン（__version__ = "0.1.0"）。
  - public API エクスポート: data, strategy, execution, monitoring を __all__ にて公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装。
    - プロジェクトルートの検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの取り扱い（クォート有無に応じた処理）。
  - 保護された OS 環境変数の上書き防止（protected キーセット）。
  - 必須設定取得ユーティリティ _require と Settings クラスを提供。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境モード検証: KABUSYS_ENV の有効値 (development, paper_trading, live) をチェック。
    - ログレベル検証: LOG_LEVEL の有効値 (DEBUG, INFO, WARNING, ERROR, CRITICAL) をチェック。
    - is_live / is_paper / is_dev の補助プロパティ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限: 120 req/min を固定間隔スロットリングで尊重（内部 RateLimiter）。
    - リトライロジック: 指数バックオフ、最大3回。408/429/5xx をリトライ対象。429 の場合 Retry-After を優先。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして1回だけ再試行。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (マーケットカレンダー)
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE
      - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE
    - レスポンスパース・型変換ユーティリティ (_to_float, _to_int) を提供。
    - データ取得時に fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアスのトレーサビリティを確保。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集・正規化して raw_news に保存するためのモジュール基盤を実装。
    - デフォルト RSS ソース (例: Yahoo Finance) を定義。
    - セキュリティ配慮:
      - defusedxml による XML パース（XML Bomb 等の対策）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
      - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）の削除、スキーム/ホスト小文字化、クエリソート、フラグメント削除。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保。
    - バルク INSERT のチャンク化とトランザクション単位での保存を想定（INSERT RETURNING を用いる設計）。
    - news_symbols による銘柄紐付けを想定。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算群を実装・公開:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev)
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、volume_ratio
    - calc_value: PER, ROE（raw_financials と prices_daily を組合せ）
    - zscore_normalize は外部（kabusys.data.stats）から利用（正規化ユーティリティを想定）
  - 特徴量探索ツール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）
    - calc_ic: Spearman のランク相関（Information Coefficient）を実装（ties は平均ランク）
    - factor_summary: 基本統計量（count, mean, std, min, max, median）
    - rank: 同順位は平均ランクを返すランク化ユーティリティ
  - 設計方針: DuckDB の prices_daily / raw_financials テーブルのみ参照、外部依存は最小化。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research の calc_momentum/calc_volatility/calc_value を利用してファクターを取得。
    - ユニバースフィルタを適用（最低株価 300 円、20日平均売買代金 5 億円）。
    - 指定カラム群を Z スコア正規化し ±3 でクリップ（外れ値影響抑制）。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等に保存。トランザクションで原子性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合し、以下コンポーネントスコアを計算:
      - momentum（momentum_20, momentum_60, ma200_dev の sigmoid 平均）
      - value（per に基づくスケーリング: per=20 -> 0.5、per→0 -> 1.0、per→∞ -> 0.0 の近似）
      - volatility（atr_pct の Z スコアを反転して sigmoid）
      - liquidity（volume_ratio の sigmoid）
      - news（ai_score を sigmoid、未登録は中立）
    - 欠損コンポーネントは中立値 0.5 で補完。
    - 重み (デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10)。ユーザ指定 weights は検証・正規化（未知キーや負値・非数は無視、合計が1でない場合はリスケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合（ただしサンプル数 minimum=3 未満では判定しない）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル: final_score >= threshold の銘柄を上位より選択（SELL 対象は除外しランクを付与）。
    - SELL シグナル（保有ポジションに対するエグジット判定）:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - スコア低下: final_score < threshold
      - 未実装の将来的な判定: トレーリングストップ、時間決済（コメントに記載）
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - ログ出力により欠損データや価格欠損時の挙動を明確化（例: features に存在しない保有銘柄は score=0.0 として SELL 判定）。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- news_collector で defusedxml を使用、受信バイト数上限、URL 正規化等の設計があるため、外部入力に対する基本的な防御が組み込まれている。

Database / Schema 前提（実装が依存するテーブル）
- raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
- raw_financials (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at)
- market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
- prices_daily（feature / research / signal ロジックが参照）
- features (date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev, created_at)
- ai_scores (date, code, ai_score, regime_score)
- positions (date, code, avg_price, position_size, ...)
- signals (date, code, side, score, signal_rank)
- raw_news / news_symbols（news_collector 側の想定）

Notes / Known limitations
- DuckDB のテーブル定義（カラム名・型）はコードの期待に合わせる必要があります。テーブルが存在しない／カラムが不足している場合は実行時にエラーになります。
- news_collector の RSS フェッチ本体はコードスニペット中で一部設計のみ（ユーティリティや定数）であり、完全な取得フローは今後の実装対象と思われます。
- execution / monitoring パッケージの具体的な発注・監視ロジックは現時点では未実装または省略されています（__all__ に名前が存在）。
- zscore_normalize 関数は kabusys.data.stats で提供される前提。該当モジュールの存在が必要です。

貢献・質問
- バグや改善提案があれば issue を立ててください。ドキュメント、テスト、CI の追加は歓迎します。