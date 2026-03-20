# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。さらに詳しくは https://keepachangelog.com/ja/ を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。本リリースで実装された主な機能・モジュールは以下のとおりです。

### Added
- パッケージ基盤
  - パッケージバージョン `kabusys.__version__ = "0.1.0"` を導入。パッケージ公開時の基本 API (`data`, `strategy`, `execution`, `monitoring`) を __all__ で公開。
- 環境設定 / 設定管理 (`kabusys.config`)
  - `.env` / `.env.local` ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート検出は `.git` または `pyproject.toml` を基準）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを独自実装：`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - 保護された OS 環境変数を上書きしないための `protected` 機構を用意し、`.env.local` は `.env` を上書き可能。
  - 必須設定を取得する `_require()`、および `Settings` クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性検査（許容値チェック）を実装。
- Data レイヤー
  - J-Quants API クライアント (`kabusys.data.jquants_client`)
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（内部 RateLimiter）。
    - 冪等性を保つためのページネーション対応および DuckDB への upsert/save 関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を提供。`fetched_at` を UTC で記録。
    - 再試行（指数バックオフ）ロジック、対象ステータスコード (408, 429, 5xx) に対するリトライ、429 の `Retry-After` 優先処理を実装。
    - 401 受信時のトークン自動リフレッシュ（`get_id_token` 呼び出し）を 1 回だけ行い再試行する仕組みを実装。
    - ページネーション・レスポンスの統合処理（重複防止のための pagination_key キャッシュ）。
    - 入力値変換ユーティリティ `_to_float`, `_to_int` を実装（堅牢な型変換）。
  - ニュース収集モジュール (`kabusys.data.news_collector`)
    - RSS フィードから記事を取得し `raw_news` 等へ冪等保存する処理を実装。デフォルトで Yahoo Finance のビジネス RSS を参照。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を保証。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリをソート、フラグメント除去を実装。
    - XML パースに `defusedxml` を使用して XML BOM 等の攻撃を防止。
    - 受信サイズ上限（10MB）・HTTP スキーム制限などの安全対策を実装。
    - 大量挿入時のチャンク化（バルク INSERT のチャンクサイズ管理）を実装。
- Research レイヤー
  - ファクター計算・研究モジュール群を実装 (`kabusys.research`)
    - `factor_research`:
      - Momentum ファクター（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する `calc_momentum` を実装。200 日移動平均やラグ計算に対応。
      - Volatility / Liquidity ファクター（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する `calc_volatility` を実装。true_range の NULL 伝播を制御。
      - Value ファクター（per, roe）を計算する `calc_value` を実装。`raw_financials` の最新公開データを使用。
    - `feature_exploration`:
      - 将来リターン計算 `calc_forward_returns`（任意ホライズン、1/5/21 日がデフォルト）を実装。
      - スピアマンランク相関（IC）計算 `calc_ic`、ランク化ユーティリティ `rank`、ファクター統計要約 `factor_summary` を実装。
    - 研究用ユーティリティ `zscore_normalize` を `kabusys.data.stats` 経由で利用可能（エクスポート済み）。
- Strategy レイヤー
  - 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
    - 研究環境で計算した raw ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（Z スコア）→ ±3 でクリップ → `features` テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を確保）する `build_features` を実装。
    - ルックアヘッドバイアス防止の設計（target_date 時点のデータのみ参照）。
  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - `features` と `ai_scores` を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で `final_score` を計算する `generate_signals` を実装。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完、ユーザー指定 weights の妥当性検査と正規化（合計 1.0 に再スケール）を実装。
    - Bear レジーム判定（AI の regime_score 平均 < 0 かつ十分なサンプル数）により BUY シグナルを抑制。
    - BUY 条件（閾値デフォルト 0.60）と SELL 条件（ストップロス -8%、スコア低下）を実装。
    - positions / prices_daily 参照によるエグジット判定（価格欠損時のスキップ、保有銘柄が features にない場合の扱い等）を実装。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を確保）。
- DuckDB を中心としたデータ永続化設計
  - 各保存処理は冪等性を重視（ON CONFLICT / DO UPDATE / DO NOTHING を活用）。
  - build_features / generate_signals など日付単位の「置換」操作はトランザクションとバルク挿入により原子性を担保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- データ取り込みの堅牢化
  - raw レコードで PK 欠損行はスキップして警告を出力するようにした（save_* 関数）。
  - news_collector: XML パース例外や不正入力に対する防御を追加。
  - jquants_client: JSON デコード失敗時に詳細を示すエラーを返すよう改善。

### Security
- news_collector で defusedxml を利用して XML 関連の脆弱性（XML Bomb 等）に対処。
- RSS の URL 正規化・スキーム検査・受信サイズ制限などで SSRF / メモリ DoS を軽減。
- J-Quants クライアントは認証トークンを安全に扱い（キャッシュ・リフレッシュ制御）、HTTP エラー処理を慎重に実装。

### Notes / Design decisions
- ルックアヘッドバイアス回避を重視し、すべての戦略・研究コードは target_date 時点で利用可能なデータのみを参照する設計になっています。
- 外部依存は最小化（pandas 等の重たいライブラリは使用しない方針）し、DuckDB + 標準ライブラリで多くの処理を実装しました。
- 実取引（execution 層）への依存は strategy 層で持たない方針（signals テーブルを経由して実行される想定）。

## 既知の未実装 / 今後の課題
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- PBR・配当利回り等のバリューメトリクスは現バージョンでは未実装。
- news_collector の記事→銘柄マッピング（news_symbols）の自動紐付けは実装予定。

以上。