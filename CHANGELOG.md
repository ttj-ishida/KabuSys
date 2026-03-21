# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

現在のバージョン: 0.1.0 — 2026-03-21

[0.1.0] - 2026-03-21
--------------------

Added
- 初期リリース: kabusys パッケージの基本機能を実装。
- パッケージメタデータ
  - __version__ を "0.1.0" に設定。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring を含める。
- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - export 形式やシングル/ダブルクォート、インラインコメントの扱いに対応する .env パーサー実装。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack トークンや DB パス（duckdb/sqlite）、KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）を実装。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライ（指数バックオフ、最大3回）と 408/429/5xx に対する再試行ロジック。
  - 401 受信時は自動的にリフレッシュトークンを用いて ID トークンを再取得し 1 回リトライ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）において冪等性を確保する ON CONFLICT DO UPDATE を使用。
  - レスポンスからの型変換用ユーティリティ（_to_float, _to_int）を実装し、不正値に対する耐性を向上。
  - 取得時刻を UTC で記録（fetched_at）し、Look-ahead バイアスのトレーサビリティを確保。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルに保存する基盤実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、スキーム・ホストの小文字化、フラグメント除去）。
  - 記事IDの冪等化のためハッシュ（SHA-256 の先頭等）を用いる設計（重複挿入を防止）。
  - defusedxml を利用した安全な XML パース、最大受信バイト数制限（MAX_RESPONSE_BYTES）などの DoS/SSRF 対策を考慮。
  - バルク INSERT のチャンク化によるパフォーマンス改善と SQL 長制限対策。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB(SQL) ベースで計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播を厳密に制御）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（EPS が 0/欠損時は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: Spearman のランク相関（IC）を実装。サンプル不足（<3）や ties の取り扱いに配慮。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位は平均ランクとする安定したランク関数（丸めで ties 判定を安定化）。
  - research 名前空間で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。
  - research 側で計算した生ファクターを結合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 指定列を zscore_normalize で正規化し ±3 でクリップ。
  - 日付単位の置換（DELETE + bulk INSERT）をトランザクションで行い冪等性と原子性を保証。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出（シグモイド変換等）。
  - 欠損コンポーネントは中立値 0.5 で補完、weights は検証・補完・リスケールを行う。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY シグナルを抑制。
  - エグジット判定（SELL）にはストップロス（-8%）とスコア低下を実装。保有ポジションの価格欠損時は判定をスキップして誤クローズを防止。
  - BUY/SELL を signals テーブルへ日付単位で置換（トランザクション + bulk insert）し冪等性を確保。
  - signals / features / ai_scores / positions / prices_daily など DuckDB テーブルを前提とした実装。
- API エクスポート
  - strategy モジュールで build_features / generate_signals をトップレベルに公開。
  - research モジュールで主要な計算ユーティリティをトップレベルに公開。

Security
- ニュース収集で defusedxml を利用して XML 関連の攻撃を緩和。
- RSS の受信上限バイト数や URL 正規化、トラッキングパラメータ除去、HTTP/HTTPS 以外のスキーム制限など、外部入力に対する複数の防御を導入。
- J-Quants クライアントにおいてトークン自動リフレッシュやリトライロジックを厳密に扱い、不正な状態での無限再試行を防止。

Notes / Known limitations
- signal_generator のエグジット条件で、トレーリングストップや保有期間に基づく時間決済は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- calc_value は現時点で PBR や配当利回りを計算していない（将来拡張予定）。
- news_collector の一部詳細（例: SSRF ホワイトリストや IP 検査の完全な適用等）は外部依存や実運用での追加が想定される。
- 外部依存を極力避ける設計（research モジュールは pandas 等を使わずに実装）だが、大規模データ処理や高度な分析では追加ライブラリ導入を検討すると良い。

Developer notes
- 主要処理は DuckDB 接続を引数に取る設計。テスト時は In-memory DuckDB を使用して単体テストが容易。
- トランザクション（BEGIN/COMMIT/ROLLBACK）を手動で扱っているため、使用する環境での例外ハンドリングに注意。
- 環境変数の必須チェックは Settings クラスのプロパティで行う（未設定時は ValueError を送出）。

今後の予定（例）
- エグジットロジックの拡張（トレーリングストップ、保有日数による決済）。
- ファクター群の拡張（PBR、配当利回りなど）。
- ニュース記事の銘柄紐付け（news_symbols）や自然言語処理による AI スコア生成の統合強化。
- 実運用向けの監視 / 実行レイヤ（execution / monitoring）実装の拡充。

--------------------------------

（初期リリースのため Breaking Changes / Fixed / Changed の履歴はありません）