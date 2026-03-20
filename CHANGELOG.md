# Changelog

すべての重要な変更点をこのファイルに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

全ての日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]
（次回リリースに向けた変更はここに記載します）

---

## [0.1.0] - 2026-03-20

初回リリース。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring を public API として定義。

- 環境設定モジュール (kabusys.config)
  - .env ファイルと環境変数を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパース実装:
    - コメント行 / 空行のスキップ、`export KEY=val` 形式の対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしでの `#` コメント判定（直前が空白/タブの場合のみ）。
  - .env 読み込み時の上書き制御:
    - override フラグと protected キー集合により OS 環境変数の保護を実現。
  - Settings クラスを提供（settings インスタンスをモジュールレベルで公開）。
    - J-Quants / kabuステーション / Slack / データベース（DuckDB, SQLite）関連などのプロパティを定義。
    - バリデーション: KABUSYS_ENV の許容値検証（development / paper_trading / live）、LOG_LEVEL の許容値検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter を導入（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に含む。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止のため allow_refresh 制御）。
    - ページネーション対応（pagination_key を用いたページネーション取得）。
    - 取得時の fetched_at を UTC で記録し、Look-ahead バイアス対策をサポート。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - ON CONFLICT DO UPDATE による冪等保存（重複更新を回避）。
    - PK 欠損行のスキップとログ出力。
    - 型変換ユーティリティ _to_float / _to_int（堅牢な変換ルール）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する処理を実装。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリパラメータのソート。
    - defusedxml を利用して XML Bomb 等の攻撃を防ぐ。
    - HTTP レスポンスの最大読み取りバイト数制限（10 MB）を導入してメモリ DoS を防止。
    - URL のスキーム検証やホワイトリスト化により SSRF リスク低減（実装方針として明記）。
    - バルク INSERT のチャンク処理（チャンクサイズ上限）によるパフォーマンス最適化。
    - INSERT RETURNING を利用して実際に挿入された件数を正確に返す（設計）。

- ストラテジ関連 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research で計算した生ファクターを正規化・合成して features テーブルへ保存する一連処理を実装。
    - フロー: calc_momentum / calc_volatility / calc_value を統合 → ユニバースフィルタ（株価・流動性）適用 → Z スコア正規化 → ±3 でクリップ → features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ユニバースフィルタの閾値: 最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）。
    - 正規化対象カラムとクリップの適用。
    - DuckDB クエリで target_date 以前の最新価格を参照する設計（休場日/欠損対応）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。重み辞書を受け取り妥当性検査と合計の再スケールを実施。
    - デフォルト BUY 閾値: 0.60。
    - ストップロス: -8%（_STOP_LOSS_RATE）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつ十分なサンプル数（デフォルト最小サンプル 3）で BUY を抑制。
    - コンポーネントスコア計算:
      - momentum: momentum_20/momentum_60/ma200_dev をシグモイド→平均。
      - value: PER に基づく逆関数（PER=20 で 0.5）を実装。
      - volatility: atr_pct の Z スコアを反転してシグモイド。
      - liquidity: volume_ratio をシグモイド。
      - news: ai_score をシグモイド（未登録は中立 0.5）。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - 保有ポジションに対するエグジット判定を実装（positions / prices を参照）。
      - SELL 生成は STOP LOSS 優先、その後スコア低下によるエグジット。
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ロギングによる判定状況や警告出力。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。必要なウィンドウ不足時は None を返す。
    - calc_volatility: 20 日 ATR, atr_pct, 20 日平均売買代金, volume_ratio を計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算。EPS が 0 または欠損の場合は PER を None にする。
    - DuckDB を使った SQL ベースの実装（prices_daily / raw_financials のみ参照）。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト 1,5,21 営業日）先までの将来リターンを計算。ホライズンの妥当性検査あり。
    - calc_ic: factor_records と forward_records を code で結合し、Spearman のランク相関（IC）を計算。有効レコードが 3 件未満なら None。
    - rank / factor_summary: 同順位の平均ランク付与、各ファクター列の count/mean/std/min/max/median を計算するユーティリティを提供。
    - 外部依存を持たない（pandas など非依存）実装方針。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Notes / Design decisions
- ルックアヘッドバイアス対策が各所に組み込まれている（取得時の fetched_at、target_date 以前の最新価格を使う等）。
- DuckDB を主要なデータストアとして採用し、SQL で集計・窓関数を活用する設計。
- 発注/Execution 層（kabusys.execution）はパッケージ構成上のプレースホルダとして用意されているが、今回のコードベースでは主に data/research/strategy にフォーカスしている。
- 安全性（XML の defusedxml、HTTP レスポンス読み取り制限、SSRF・メモリ DoS 対策）を考慮した実装が各所に反映されている。

---

（以降のリリースでは、互換性に関する情報や破壊的変更があれば Breaking Changes セクションで明示します。）