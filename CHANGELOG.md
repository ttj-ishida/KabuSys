CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog のガイドラインに準拠します。

0.1.0 - 2026-03-20
-----------------

Added
- 初期リリース: 日本株自動売買システム "KabuSys" の基礎機能を追加。
- パッケージ初期化
  - パッケージバージョン: 0.1.0
  - __all__ に data/strategy/execution/monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱い等を考慮）。
  - 環境変数保護機能（OS 環境変数を protected として上書き防止）。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / システム設定などのプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live/is_paper/is_dev ヘルパー。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
  - レート制限制御（固定間隔スロットリング、120 req/min を想定する RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行および Retry-After の考慮）。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の fetch_*/save_* 関数:
    - fetch_daily_quotes / save_daily_quotes（raw_prices へ冪等保存、ON CONFLICT DO UPDATE）
    - fetch_financial_statements / save_financial_statements（raw_financials へ冪等保存）
    - fetch_market_calendar / save_market_calendar（market_calendar へ冪等保存）
  - JSON パース・エラー・ネットワークエラーの適切なハンドリングとログ出力。
  - 受信データからの型変換ユーティリティ _to_float / _to_int を提供（安全な変換と不正値の None 化）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基礎実装。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保する方針。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - HTTP/HTTPS 以外のスキーム拒否・SSRF 緩和（ホスト解析等を実装想定）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES、デフォルト 10 MB）でメモリ DoS を緩和。
  - バルク INSERT チャンク化、トランザクションで保存、INSERT RETURNING による実際に挿入された件数計測（方針）。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を登録。

- 研究モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算（ウィンドウ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播制御）。
    - calc_value: raw_financials から最新の財務データを取得し per / roe を計算。
    - DuckDB 上の prices_daily / raw_financials を参照する設計（外部 API へはアクセスしない）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（単一クエリで取得）。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算（サンプル不足時は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties の検出漏れを低減）。

  - 研究ユーティリティ zscore_normalize をデータ層から再公開。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールの calc_momentum/calc_volatility/calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列の Z スコア正規化と ±3 でのクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで実行し冪等性を保証）。
    - 休場日や当日欠損に対応するため、target_date 以前の最新価格を参照。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features / ai_scores / positions を参照し最終スコア final_score を計算。
    - コンポーネント: momentum/value/volatility/liquidity/news（AI スコア）を個別に計算し重み付き合算。
    - 重みの入力検証・フォールバック・正規化（未知キーや負値/非数は無視、合計 1.0 にスケーリング）。
    - AI レジーム平均で Bear 判定し（サンプル数閾値あり）BUY シグナル抑制。
    - BUY シグナル閾値デフォルト 0.60。SELL シグナルはストップロス（-8%）やスコア低下を判定。
    - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクションで原子性）。
    - 各所でログ出力と欠損データへの寛容な扱い（欠損コンポーネントは中立 0.5 で補完）。

- トランザクションと冪等性
  - DuckDB への書き込みは可能な限りトランザクション（BEGIN/COMMIT/ROLLBACK）でまとめ、原子性と冪等性（DELETE→INSERT、ON CONFLICT）を確保。
  - ロールバック失敗時は警告ログを出力する保護処理を追加。

Changed
- （初回リリースのため特になし）

Fixed
- （初回リリースのため特になし）

Security
- defusedxml の採用、RSS パースにおける XML 攻撃対策を明記。
- ニュース収集での URL/スキーム制限、受信サイズ制限等により SSRF / DoS のリスクを低減。

Notes / Known limitations
- 一部のエグジット条件（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の情報が必要で未実装。
- news_collector モジュールは RSS の取得やホスト検証等の詳細実装（例: IP ブロック回避やソケットレベルの検査）が必要となる可能性がある。
- 外部接続（J-Quants, RSS など）の本番挙動は実運用環境での検証が必要（レート制限や API 仕様変更へ対応）。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は別途定義が必要。

Acknowledgements
- 本 CHANGELOG はソースコードの現状（コメント・実装）から推測して作成しています。実際のリリースノートとして使用する際は各機能のテスト結果やリリース日付、著作者情報などを適宜追記してください。