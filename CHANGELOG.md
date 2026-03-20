# Changelog

すべての変更は「Keep a Changelog」規約に準拠して記載しています。日付はリリース日を示します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

Initial release — 日本株自動売買システム「KabuSys」の最初の公開バージョンです。以下の主要機能・実装が含まれます。

### Added
- パッケージ基盤
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリック API エクスポート: data, strategy, execution, monitoring

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル／環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml）
  - 読み込み順序: OS 環境変数 > .env.local > .env（既存 OS 環境変数を保護）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - .env パーサ実装:
    - コメント、先頭に export が付く形式、シングル/ダブルクォート、エスケープ対応
    - インラインコメント判定の細かい扱い（クォート有無で挙動を分離）
  - 必須キー取得ヘルパ `_require`（未設定時に ValueError）
  - Settings クラスにプロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）
  - KABUSYS_ENV 値検証（development / paper_trading / live）および LOG_LEVEL 検証（DEBUG/INFO/...）

- Data 層: J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ実装（urllib ベース）
  - レート制限（固定間隔スロットリング）: 120 req/min を遵守する RateLimiter
  - リトライ戦略: 指数バックオフ、最大3回、HTTP 408/429/5xx やネットワークエラーに対処
  - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有
  - ページネーション対応（pagination_key の繰り返し取得）
  - データ保存の冪等化: DuckDB への INSERT は ON CONFLICT DO UPDATE を使用
  - 取得時刻の記録（UTC, fetched_at）により Look-ahead バイアスを追跡可能に
  - fetch/save 機能:
    - fetch_daily_quotes / save_daily_quotes（raw_prices）
    - fetch_financial_statements / save_financial_statements（raw_financials）
    - fetch_market_calendar / save_market_calendar（market_calendar）
  - 型変換ユーティリティ: _to_float, _to_int（堅牢な変換ロジック）

- Data 層: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集 → raw_news への冪等保存ワークフロー
  - セキュリティ・堅牢性:
    - defusedxml による安全な XML パース
    - 受信データ上限（MAX_RESPONSE_BYTES: 10MB）
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、ソートされたクエリ）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
    - SSRF/非 HTTP(s) スキームの拒否（設計方針）
  - バルク INSERT のチャンク化による性能対策とトランザクションまとめ保存
  - デフォルト RSS ソースとして Yahoo Finance を登録

- Research 層（src/kabusys/research/**
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio
    - calc_value: PER（price / EPS）および ROE（raw_financials から最新財務を参照）
    - データ不足時に None を返す安全設計、DuckDB SQL を用いた高速取得
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）での将来リターン計算（単一クエリ最適化）
    - calc_ic: factor と将来リターンの Spearman（ランク）相関（IC）計算、サンプル不足時は None
    - rank / factor_summary: ランク付け（同順位は平均ランク）、基本統計量サマリ（count/mean/std/min/max/median）
  - どの関数も prices_daily / raw_financials を参照し、本番口座や発注 API へアクセスしない設計

- Strategy 層（src/kabusys/strategy/**
  - feature_engineering.build_features:
    - research モジュールから生ファクターを取得し結合
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
    - Z スコアを ±3 でクリップして外れ値影響を抑制
    - features テーブルへの日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）により冪等性と原子性を確保
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - 重みのマージと正規化（デフォルト重みを提供、ユーザー重みは検証して受け入れ）
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、サンプル数が閾値以上なら BUY を抑制
    - BUY 条件: final_score >= 閾値（デフォルト 0.60）
    - SELL 条件（エグジット）:
      - ストップロス: 終値/avg_price - 1 <= -8%
      - final_score が閾値未満
      - 価格欠損時は SELL 判定をスキップし安全性を優先
    - BUY/SELL を signals テーブルへ日付単位で置換保存（冪等）
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランク再付与）

- パッケージ初期設計方針（ドキュメント化に準拠）
  - ルックアヘッドバイアス防止: target_date 時点のデータのみ参照し、fetched_at によりデータ取得時刻を追跡
  - execution 層（発注）への直接依存を持たない層構成（戦略層は signals を書き込むのみ）
  - DuckDB を中心としたローカル分析基盤（冪等性を意識した保存処理）

### Security
- RSS パースに defusedxml を採用して XML-based 攻撃を軽減
- ニュース URL 正規化・トラッキングパラメータ削除により ID 重複や追跡パラメータによるノイズを低減
- .env 自動読み込み時に OS 環境変数を保護（.env の上書き防止がデフォルト）
- J-Quants クライアントでの 401 自動リフレッシュはリフレッシュ失敗時に例外化して安全に失敗

### Known limitations / Not implemented
- 戦略の一部退出条件は未実装（コメントに明記）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- Value 系の一部（PBR・配当利回り）は現バージョンでは未実装（factor_research.calc_value に注記あり）
- news_collector の一部 SSRF 防止・URL 検査は設計方針として記載されているが、外部環境に依存する部分は運用での追加確認が必要
- features / signals のスキーマ依存（prices_daily, raw_financials, raw_prices, raw_financials, ai_scores, positions テーブル等）があるため、運用前に DuckDB スキーマを準備する必要あり

### Other notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite（monitoring）: data/monitoring.db
- 自動 .env ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

今後の予定（例）
- execution 層（kabu ステーション API 経由の発注機能）との統合
- 戦略のエグジット条件（トレーリング・時間決済）の実装
- 単体テスト・統合テストの充実、CI ワークフローの整備
- パフォーマンス改善（大規模データ処理の最適化）、およびより厳密なセキュリティチェック

[0.1.0]: 0.1.0