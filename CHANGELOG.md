# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルは日本語での要約です。

全般:
- バージョン情報はパッケージトップレベルの __version__ = "0.1.0" に準拠しています。
- 多くの操作は DuckDB を前提としたテーブル（prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals 等）を参照/更新します。
- 日付単位の置換（target_date に対する DELETE → バルク INSERT をトランザクション内で行う）により、操作の冪等性と原子性を確保する設計が一貫して採用されています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ構成
  - kabusys パッケージ（サブモジュール: data, strategy, execution, monitoring）。
  - __all__ による公開 API の定義。

- 設定管理（kabusys.config）
  - Settings クラスを提供し、環境変数から設定値を取得する API を公開（例: settings.jquants_refresh_token）。
  - .env / .env.local の自動読み込み実装：
    - プロジェクトルート判定: .git または pyproject.toml を起点に検索（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みの無効化が可能。
    - .env の読み込みロジックは override / protected の概念を持ち、OS 環境変数の保護を実現。
  - .env 行パーサー（_parse_env_line）:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等、多くの実用ケースに対応。
  - 環境変数必須チェック（_require）とバリデーション:
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... などの検証）
  - デフォルト値:
    - KABU_API_BASE_URL のデフォルト、DUCKDB_PATH / SQLITE_PATH のデフォルトパス。

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - HTTP リトライ（指数バックオフ、最大 3 回）。408/429/5xx 系をリトライ対象に設定。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行ロジック。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
    - ユーティリティ型変換関数：_to_float / _to_int（堅牢な変換ルール）

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事収集し raw_news へ冪等保存するための処理方針を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリキーソート）を実装するユーティリティ（_normalize_url の実装開始）。
    - defusedxml を用いた XML パース（安全対策）、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP スキーム検証、記事 ID を正規化 URL の SHA-256 ハッシュ先頭で生成する方針など、安全・冪等性を重視した設計。
    - バルク INSERT 用チャンク処理を導入。

- Research 層（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。MA200 のデータ不足時は None を返す。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算。TRUE RANGE の NULL 伝播を明示的に制御。
    - calc_value: 最新財務データ（raw_financials の target_date 以前の最新）と prices_daily を組み合わせて per / roe を計算。
    - SQL とウィンドウ関数を活用した効率的な実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数が不足（<3）なら None を返す。
    - rank, factor_summary: ランク計算（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - research パッケージの __all__ に主要関数を公開。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features(conn, target_date):
      - research の calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得。
      - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
      - 指定数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
      - features テーブルへ日付単位で置換挿入（トランザクションによる原子性）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores（存在しない場合は空）を組み合わせ、複数のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
      - Z スコア → シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
      - 重みのマージ・検証（負値・NaN・未知キーは無視）、合計が 1.0 でなければ再スケール。
      - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数が閾値以上）により BUY を抑制。
      - BUY: final_score >= threshold の銘柄（Bear レジーム時は抑制）。
      - SELL: ポジションに対するエグジット判定（ストップロス -8% 優先、score_drop など）。
      - SELL を優先して BUY から除外し、signals テーブルへ日付単位で置換挿入（トランザクション）。
    - ロジックの多くは StrategyModel.md の仕様（コメント）に従って実装。

### Changed
- （初版のため変更履歴はありません）

### Fixed
- （初版のため修正履歴はありません）

### Deprecated
- なし

### Removed
- なし

### Security
- ニュース XML のパースに defusedxml を利用し、XML Bomb 等に対する安全対策を導入。
- news_collector は受信サイズ上限や URL スキーム検査を行い、メモリ DoS / SSRF 対策を考慮。

### Notes / Known limitations / TODO
- signal_generator 内の一部のエグジット条件（トレーリングストップ、保有期間による時間決済）は未実装（コード中に TODO としてコメントあり）。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の _normalize_url は実装されている一部の振る舞いが存在しますが、フィード取得/パース周りの運用検証が必要。
- calc_momentum の ma200_dev はウィンドウ内データが 200 行未満の場合 None を返す点に注意（過去データ不足銘柄の取り扱い）。
- J-Quants クライアントのリトライ対象ステータスや最大リトライ回数は今後の運用状況に応じて調整が必要になる可能性があります。
- DB スキーマ（テーブル名・カラム名）に依存するため、既存データベースとの互換性維持に注意が必要です。

---

もし CHANGELOG に追記したい詳細（リリース日を変える、Unreleased に今後の変更を書く、あるいは項目を分割してより細かく記載する等）があれば教えてください。必要に応じて英語版や短縮版も作成します。