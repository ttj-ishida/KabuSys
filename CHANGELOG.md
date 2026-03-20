# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（現時点のリポジトリ状態は最初の公開バージョンとして 0.1.0 に相当します。将来の変更はここに記載します。）

---

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システムのコアライブラリを実装します。主な追加点は以下のとおりです。

### Added
- パッケージのエントリポイント
  - `kabusys` パッケージを追加。__version__ = "0.1.0"、公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を導出。

- 環境設定管理
  - `kabusys.config.Settings` を追加。環境変数から設定値を取得するプロパティを提供（J-Quants / kabuステーション / Slack / DB パス / システム設定など）。
  - 自動 `.env` ロード機構を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルートは `.git` または `pyproject.toml` を基準に検出。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用）。
  - `.env` ファイルパーサーの実装（コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い等に対応）。
  - `.env` 読み込み時の上書き制御（`override`）と OS 環境変数の保護（`protected`）。

- Data 層: J-Quants クライアント
  - `kabusys.data.jquants_client` を追加。J-Quants API から日次株価 / 財務データ / マーケットカレンダーの取得と DuckDB への保存機能を実装。
  - API レート制限対応（固定間隔スロットリング）とモジュールレベルのトークンキャッシュ実装（ページネーション間で共有）。
  - リトライロジック（指数バックオフ、最大 3 回）と 401 受信時のトークン自動リフレッシュ（1 回のみリトライ）を実装。
  - ページネーション対応の `fetch_*` 系関数と、冪等保存のための `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を追加（DuckDB に対して ON CONFLICT DO UPDATE を使用）。
  - データ変換ユーティリティ `_to_float`, `_to_int` を提供。
  - ログ出力で取得件数や警告を適切に記録。

- Data 層: ニュース収集
  - `kabusys.data.news_collector` を追加。RSS フィードから記事を取得し raw_news への冪等保存を想定。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）と記事 ID の SHA-256 による生成方針を採用。
  - defusedxml による XML パースでセキュリティ対策（XML Bomb 等）を実装。HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）など DoS 対策も盛り込む。
  - デフォルト RSS ソースの定義（例: Yahoo ビジネス RSS）。
  - バルク INSERT のチャンク処理と、挿入数の正確な取得を行う設計。

- Research 層: ファクター計算・解析
  - `kabusys.research.factor_research`
    - モメンタム、ボラティリティ、バリュー関連のファクター計算を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
      - calc_value: per, roe（raw_financials と prices_daily の組合せ）
    - 営業日不連続性を考慮したスキャン範囲のバッファ、データ不足時の None 処理などを含む。
  - `kabusys.research.feature_exploration`
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。サンプル不足時の None 返却。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリ。
    - rank: 同順位は平均ランクを付与するランク関数（浮動小数丸めで ties 検出を安定化）。
  - `kabusys.research.__init__` で必要関数をエクスポート。

- Strategy 層
  - `kabusys.strategy.feature_engineering`
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）および ±3でクリップして `features` テーブルへ日付単位の置換（トランザクションで原子性を担保）する `build_features` を実装。
    - ルックアヘッドバイアス回避の設計に基づく実装。
  - `kabusys.strategy.signal_generator`
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算する `generate_signals` を実装。
    - デフォルト重みや閾値を定義（デフォルト BUY 閾値 = 0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制。サンプル数不足時は Bear とみなさない）。
    - SELL シグナル（ストップロス：-8% など、スコア低下）生成ロジックと、positions / prices を参照するエグジット判定を実装。
    - weights の入力検証・合成・リスケール、欠損コンポーネントの中立補完（0.5）など堅牢性を考慮。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を確保。

- Data/Utils
  - `kabusys.data` からのユーティリティ（zscore_normalize など）を research / strategy が利用する形で連携。

### Security / Robustness
- API クライアントで以下を考慮:
  - レート制限順守（固定間隔スロットリング）。
  - ネットワークリトライ（408/429/5xx 等）と指数バックオフ、429 の Retry-After を尊重する実装。
  - 401 の場合にトークン自動更新を行い、無限再帰を避けるため allow_refresh フラグを制御。
- ニュース収集で defusedxml を採用、受信サイズ制限、URL/ホスト検証などで SSRF / DoS に対する配慮。

### Documentation / Design notes
- 各モジュールにモジュールレベルの docstring を追加し、設計方針（ルックアヘッドバイアス防止、発注 API への依存排除、冪等性）を明示。
- DuckDB の各テーブル参照箇所で取得クエリ／ウィンドウ関数を用いて効率的に集計する実装。

### Known limitations / TODOs
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- `execution` と `monitoring` モジュールはパッケージ配下に存在するが、実装は未提供（エントリとしては公開）。
- NewsCollector の一部処理（記事 → 銘柄マッピングなど）は高レベル設計に留まり、実装の詳細は拡張が想定される。

### Fixed
- （初版のため無し）

### Changed / Deprecated / Removed / Security
- （初版のため該当なし）

---

今後のリリースでは、execution 層（実際の発注ロジックと kabu API 連携）、monitoring（Slack 通知・メトリクス）、さらにテストや CI 設定、ドキュメント追記を予定しています。