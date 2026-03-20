# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。  

- リリース日付はコミットベースで推測しています。
- 各項目はコードベース（src/kabusys 以下）の実装内容から推測して記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。  
主にデータ収集、因子計算、特徴量生成、シグナル生成、設定管理、ニュース収集に関するコアロジックを提供します。

### Added
- パッケージ基本設定
  - パッケージメタ情報と公開モジュールを定義（src/kabusys/__init__.py）。
  - settings オブジェクト経由の環境変数アクセスを提供（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルートの検出、.env → .env.local の順で読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
    - .env 行パーサは export 形式、クォート、インラインコメントなどに対応。
    - 必須環境変数のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - 環境（KABUSYS_ENV: development / paper_trading / live）およびログレベル検証。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアント実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）、HTTP 408/429/5xx へのリトライ対応。
    - 401 受信時はリフレッシュトークンで自動的に ID トークンを再取得して1回リトライ。
    - ページネーション対応の fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
    - データ型変換ユーティリティ（_to_float / _to_int）を提供。
    - fetched_at を UTC ISO8601 で記録し、データ取得時刻をトレース可能に。

- ニュース収集
  - RSS ベースのニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリ）を定義。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）を想定して冪等性を確保。
    - defusedxml を用いた XML パース、安全性考慮（XML Bomb 等への対策）。
    - レスポンスサイズ上限、チャンク化バルク挿入、ON CONFLICT DO NOTHING による冪等保存戦略。

- 研究用因子計算（Research）
  - 因子計算群（src/kabusys/research/factor_research.py）を実装:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - calc_value: PER、ROE（raw_financials の最新レコードを使用）。
    - DuckDB の SQL を駆使し、営業日ベースのウィンドウ集計で実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を使用）。
    - calc_ic: ファクターと将来リターン間の Spearman ランク相関（IC）を計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: タイの処理（平均ランク）に対応するランク関数。
  - これらは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリで完結する設計。

- 特徴量エンジニアリング（Strategy）
  - build_features（src/kabusys/strategy/feature_engineering.py）を実装:
    - research の calc_momentum / calc_volatility / calc_value から生ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し原子性を保証）。
    - 冪等性を意識した実装。

- シグナル生成（Strategy）
  - generate_signals（src/kabusys/strategy/signal_generator.py）を実装:
    - features / ai_scores / positions テーブルを用いて最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを提供。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.4 等）、ユーザ指定 weights の検証と正規化を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制）。
    - BUY 閾値デフォルト 0.60、SELL はストップロス（終値/avg_price - 1 < -0.08）とスコア低下を判定。
    - BUY / SELL シグナルを signals テーブルへ日付単位で置換（原子処理）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）を採用。

- DuckDB を中心とした設計
  - 多くのモジュールが DuckDB 接続を受け取り、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar といったテーブルを参照・更新する前提の実装。

### Security
- ニュース収集で defusedxml を利用して XML 関連の脆弱性対策を実装。
- RSS URL 正規化と受信時のスキームチェック、受信サイズ制限により SSRF / メモリ DoS 対策を考慮（実装箇所に該当ロジックあり）。
- 環境変数の保護: .env 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）を用意。

### Notes / Implementation details
- トランザクション処理: features / signals 等の置換処理で BEGIN/COMMIT/ROLLBACK を明示的に使用して原子性を確保。
- ロギング: 各モジュールに logger を配置し、警告・情報ログを適切に出力する設計。
- 入力検証: weights の妥当性確認、horizons の範囲チェック（<=252）、文字列→数値変換の堅牢化など多数のバリデーションを実装。
- 一部未実装・将来の拡張余地:
  - signal_generator の SELL 条件でトレーリングストップや時間決済は positions に peak_price / entry_date が必要なため未実装としてコメントあり。
  - news_collector の完全な SSRF/IP検査・ソケット解決の実装はモジュールにそのためのインポート/定数があり、実装が継続される想定。

### Breaking Changes
- 初回リリースのため該当なし。

---

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のプロジェクト運用では実コミット/チケット履歴に基づく正確な変更履歴を併記してください。）