# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニングに従います。

## [Unreleased]


## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装しました。
以下はコードベースから推測される追加機能・設計上の要点です。

### Added
- パッケージ基盤
  - パッケージ宣言とバージョン情報を追加（kabusys v0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / config
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサー（コメント、export プレフィックス、クォートおよびエスケープ対応、インラインコメント処理）を実装。
  - .env と .env.local の優先度ルール（OS 環境変数 > .env.local > .env）を実装。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定取得とバリデーション（KABUSYS_ENV, LOG_LEVEL の検証）を実装。

- データ取得・保存（data）
  - J-Quants API クライアント（jquants_client）を実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 408/429/5xx の再試行処理。
    - 401 レスポンス時にリフレッシュトークンで ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等的に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による更新・スキップ処理、PK欠損行のスキップログ。
    - 型安全な変換ユーティリティ（_to_float, _to_int）。
  - ニュース収集モジュール（news_collector）の基礎を実装。
    - RSS フィード取得と記事正規化（URL 正規化、トラッキングパラメータ除去、本文正規化）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保する設計方針。
    - 受信サイズ上限（10 MB）、XML パーサに defusedxml を利用する方針、SSRF/不正 URL の防御、バルク INSERT チャンク処理など。

- リサーチ（research）
  - ファクター計算モジュール（factor_research）を実装。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算。true_range 計算時の NULL 伝播制御。
    - Value（per, roe）計算。raw_financials から target_date 以前の最新財務データを取得。
  - 特徴量探索モジュール（feature_exploration）を実装。
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、ホライズンバリデーション）。
    - IC（Information Coefficient）計算（Spearman の ρ の実装、結合・欠損処理、必要最小サンプル判定）。
    - 基本統計量要約（factor_summary）とランク付けユーティリティ（rank）。
  - research パッケージの公開 API を定義（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- 戦略（strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research の生ファクター（calc_momentum / calc_volatility / calc_value）を統合し、
      ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列の Z スコア正規化（zscore_normalize を利用）と ±3 クリップ、features テーブルへ日付単位で置換（冪等）して保存。
    - DuckDB 結合クエリで target_date 以前の最新終値を参照して休場日対応。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算し重み付き合算で final_score を算出（デフォルト重みは StrategyModel.md 相当の値を使用）。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）。
    - BUY 閾値（デフォルト 0.60）超で BUY シグナル、保有ポジションに対するエグジット判定（ストップロス -8% やスコア低下）で SELL シグナルを生成。
    - SELL 優先ポリシーにより SELL 対象は BUY から除外、signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。

- データ処理ユーティリティ
  - zscore_normalize（data.stats に実装されている想定）を利用する設計。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース解析で defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）に対処。
- ニュース URL の正規化でトラッキングパラメータを除去し、クエリ/フラグメント処理を実施。HTTP/HTTPS スキーム以外の URL を拒否する方針（SSRF 緩和）。
- J-Quants クライアントでタイムアウトやネットワークエラー時の再試行を明示的に実装し、429 の Retry-After を尊重。

### Notes / Implementation details
- 多くの処理は DuckDB のウィンドウ関数や SQL で実装されており、prices_daily / raw_financials / features / ai_scores / positions / signals 等のテーブルスキーマに依存します（テーブル定義は別途必要）。
- ルックアヘッドバイアス防止のため、ほとんどの関数は target_date 時点までにシステムが「利用可能な」データのみを参照する設計になっています。
- 冪等性を重視（DB への日付単位置換、ON CONFLICT、PK 欠損スキップログなど）。
- 一部機能（例: strategy のトレーリングストップや時間決済）は positions テーブルに追加情報（peak_price, entry_date 等）が必要で未実装として設計メモに残されています。
- news_collector モジュールは主要なユーティリティ（URL 正規化、XML 安全化、受信サイズ制限、チャンク INSERT 等）を備えていますが、RSS フィードの取得パイプライン全体（フルパーサ・DB保存ラッパー等）は引き続き実装が想定されます。

### Breaking Changes
- （初版のため該当なし）

---

作業内容や API の細かな仕様、DB スキーマや実運用時の設定例（.env.example 等）は別ドキュメントにまとめることを推奨します。必要であれば CHANGELOG の項目を英語版や将来のマイナーバージョン向けに追記します。