KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回公開（ベース実装）。日本株の自動売買システム KabuSys のコア機能を実装しています。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化と公開 API を定義（kabusys/__init__.py）。
  - strategy、execution、data、monitoring などの主要サブパッケージを想定した公開インターフェースを提供。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動 .env ロードを実装。
  - .env パーサを堅牢に実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数取得時に未設定なら明示的にエラーを出す _require() を提供。
  - env 値の検証（development, paper_trading, live）およびログレベル検証（DEBUG..CRITICAL）。
  - データベースパス（DuckDB / SQLite）等のデフォルトパス設定。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装：
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ（指数バックオフ、最大3回）、HTTP 状態コードに応じたリトライ制御（408,429,5xx）、429 の Retry-After ハンドリング。
    - 401 を受けた際のトークン自動リフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュを実装。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - 取得データを DuckDB に冪等保存する save_* 関数（raw_prices, raw_financials, market_calendar）。ON CONFLICT による upsert を使用。
    - データ整形ユーティリティ（_to_float / _to_int）を実装し、安全な型変換を行う。
    - 取得時刻を UTC ISO8601（fetched_at）で記録することで Look-ahead バイアス対策。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを追加：
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - RSS から記事抽出し raw_news へ冪等に保存する設計。
    - 記事ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を担保。
    - URL 正規化でトラッキングパラメータ除去、フラグメント削除、クエリキーソートなどを実施。
    - defusedxml を用いた XML パース（XML Bomb 対策）、最大受信サイズ制限（10MB）、HTTP スキーム制限等の安全対策。
    - DB バルク挿入用チャンク処理を備える。

- 研究・ファクター計算（kabusys.research, kabusys.research.factor_research）
  - ファクター計算関数を実装（DuckDB を直接参照する設計、外部 API にはアクセスしない）：
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
  - 計算は営業日ベース（連続レコード数）を意識した実装。データ不足時は None を返す。

- 研究用解析ツール（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns、複数ホライズン対応、1クエリで取得）。
  - IC（Information Coefficient）計算（Spearman の ρ、同順位は平均ランクで処理）。
  - ランク関数 rank（同順位は平均ランク、丸めで ties の検出漏れを抑制）。
  - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - すべて標準ライブラリ＋DuckDBのみ依存の実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を用いて生ファクター収集。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで行い原子性を保証）。
    - 冪等操作で繰り返し実行可能。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みと閾値（デフォルト threshold=0.60）を採用。ユーザー指定の weights は検証・正規化して合計が 1.0 になるようスケール。
    - Bear レジーム判定（AI の regime_score の平均が負でかつサンプル数 >= 3 の場合）で BUY シグナルを抑制。
    - BUY は final_score >= threshold（Bear 時は抑制）、SELL はストップロス（終値ベースで -8%）または final_score < threshold。
    - positions / prices_daily 参照により既存ポジションのエグジット判定。SELL は優先され BUY から除外。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 実装済み / 未実装のエグジット条件をドキュメント化（トレーリングストップ・時間決済は未実装）。

### Security
- RSS パーシングで defusedxml を利用し XML 脆弱性を緩和。
- news_collector で受信サイズ制限、スキームチェック（http/https のみ）など SSRF / DoS の防止策を導入。
- jquants_client で API レート制御、リトライ・バックオフ、トークン安全リフレッシュを実装。

### Notes / Limitations
- execution レイヤー（実際の発注 API 連携）や monitoring 層の具体的な実装は含まれていません（パッケージ構造は想定済み）。
- 一部のエグジット条件（トレーリングストップ、時間決済）は設計に記載されているが未実装。
- research モジュールおよび strategy の設計は「ルックアヘッドバイアス防止」を重視しており、target_date 時点の情報のみを使用する前提です。
- DB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news など）は利用者が事前に用意することを想定しています。

### Removed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### 概要
この 0.1.0 リリースは、データ収集（J-Quants / RSS）からファクター計算、特徴量の正規化、シグナル生成までのワークフローのコア部分を提供します。実際の発注・モニタリング部分は別レイヤーとして切り分けられており、本リリースは研究・バックテスト・シグナル生成パイプラインの基盤実装を目的としています。