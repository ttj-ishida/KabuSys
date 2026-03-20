# Keep a Changelog

すべての変更はセマンティック バージョニングに従って記載します。
このファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回公開リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。
主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API を定義（data / strategy / execution / monitoring を __all__ に含む）。

- 設定・環境管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み。
  - export KEY=val 形式やクォート/エスケープ/インラインコメントに対応した .env パーサを実装。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - settings オブジェクトを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境 (development/paper_trading/live) 等の設定プロパティを公開。
  - 環境変数の必須チェック（未設定時は ValueError を送出）および LOG_LEVEL / KABUSYS_ENV の入力検証を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装する RateLimiter。
    - 再試行ロジック（指数バックオフ、最大 3 回）および 408/429/5xx をリトライ対象に設定。
    - 401 レスポンス受信時の自動トークンリフレッシュ（1 回）をサポート。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT による更新処理を採用。
    - データ変換ユーティリティ _to_float / _to_int を提供（安全な型変換と不正値のスキップ処理）。
    - fetched_at を UTC ISO8601 で記録し、look-ahead bias 対策のため取得時刻を追跡可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news に保存するための基礎実装。
    - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリ）を定義。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリソート）を実装。
    - XML パースに defusedxml を利用してセキュリティ（XML Bomb 等）を考慮。
    - 受信サイズ上限（10MB）によるメモリ DoS 対策、HTTP スキームチェック等の安全対策。
    - 挿入はバルクでチャンク化し、ON CONFLICT / INSERT RETURNING 等で冪等性と挿入数の正確な把握を意図。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）。
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR, atr_pct, 20日平均売買代金, volume_ratio。
    - バリュー (calc_value): PER, ROE（target_date 以前の最新財務データを使用）。
  - DuckDB 上のウィンドウ関数を活用し、営業日不連続性に対応したスキャン範囲を限定。

- 研究支援・解析ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）に対応。返却は fwd_?d カラム。
  - IC 計算 (calc_ic): factor と将来リターンの Spearman ランク相関を実装。サンプル不足や分散0 の取り扱いを考慮。
  - ランク変換ユーティリティ (rank): 同順位は平均ランクで処理（丸めで ties の誤検出を回避）。
  - 統計要約 (factor_summary): count/mean/std/min/max/median を計算。

- 特徴量生成 (kabusys.strategy.feature_engineering)
  - research モジュールの生ファクターを合成・正規化し features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円。
    - 指定列の Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ。
    - 日付単位の置換（DELETE + bulk INSERT）で冪等性を確保。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI スコア）を計算。
    - デフォルト重みは StrategyModel.md に準拠（momentum 0.40 等）。ユーザ指定 weights の検証と正規化を実装。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完する仕様。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）により BUY を抑制。
    - エグジット条件（STOP LOSS -8% / final_score が閾値未満）による SELL シグナル生成（_generate_sell_signals）。
    - signals テーブルへの日付単位置換で冪等性を確保。
    - ロギングで処理状況を出力。

- 研究パッケージ公開 (kabusys.research.__init__)
  - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をトップレベルで公開。

### 既知の制限 / 注意点
- トレーリングストップや保有期間による時間決済等、一部のエグジット条件は未実装（signal_generator 内に TODO 記載）。positions テーブルに peak_price / entry_date 等のフィールドが必要。
- news_collector の詳細な RSS パース/記事抽出ロジックは基礎実装に留まり、追加のフィルタリングや銘柄紐付けロジック（news_symbols への紐付け等）は今後実装予定。
- execution モジュールはパッケージに含まれる名前空間のみを定義（src/kabusys/execution/__init__.py が空）。発注 API 連携の実装は別途必要。
- settings._require は未設定環境変数で ValueError を送出するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化するか必要な環境変数を設定してください。
- DuckDB スキーマ（テーブル定義）はこのリリースには含まれていないため、実行前に適切なスキーマを準備する必要があります（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）。

### セキュリティ関連
- XML パースに defusedxml を使用し XML 関連の攻撃を軽減。
- news_collector で受信サイズの上限設定、URL 正規化、スキームチェック、IP/SSRF への配慮を実装する設計方針を採用。
- J-Quants クライアントはトークン管理・自動リフレッシュ・リトライで堅牢性を高めています。

### 破壊的変更
- なし（初回リリース）

### 参考ドキュメント
- StrategyModel.md / DataPlatform.md 等の設計書に基づく実装方針を各モジュールの docstring に記載。

---

今後の予定（例）
- execution モジュールで実際の発注ロジックと kabuステーション API 統合を実装。
- news_collector の記事→銘柄紐付け（NER／ルールベース）、および Slack 通知等の監視機能を追加。
- テストカバレッジ拡充、CI/CD とパッケージ配布設定の整備。