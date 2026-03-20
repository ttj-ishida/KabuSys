# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース方針: セマンティックバージョニングを採用しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring（execution は空の初期モジュール）。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env 行パーサを実装（コメント行 / export KEY=val / シングル/ダブルクォート / エスケープ対応 / インラインコメント処理）。
  - Settings クラスを提供し、アプリ固有の必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV）を取得可能に。
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）と LOG_LEVEL の検証を追加。環境判定プロパティ（is_live / is_paper / is_dev）を提供。

- データ収集（data/jquants_client）
  - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）・HTTP 状態コードに基づくリトライ制御（408, 429, 5xx 等）。
    - 401 受信時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュ共有。
    - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装（ページネーション対応）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等性を確保。
    - データ変換ユーティリティ（_to_float, _to_int）、UTC での fetched_at 記録など Look-ahead バイアス対策の考慮。

- ニュース収集（data/news_collector）
  - RSS からニュースを収集して raw_news へ保存するための基盤実装（RSS パース・前処理・正規化・冪等保存の方針を実装）。
    - デフォルト RSS ソース設定（例: Yahoo Finance）。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によりメモリ DoS を防止。
    - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）を緩和。
    - DB バルク挿入チャンク化（チャンクサイズ制限）や ON CONFLICT ベースの冪等保存方針を明記。

- リサーチ / ファクター計算（research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日移動平均乖離率）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）などの計算を実装。prices_daily / raw_financials のみを参照。
    - 欠損や窓不足時の None ハンドリングを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、デフォルトホライズン [1,5,21]）を実装。1 クエリでまとめて取得する実装。
    - IC（Spearman の ρ）計算（calc_ic）を実装。ランク付け（rank）関数は同順位を平均ランクで処理。
    - factor_summary による基本統計量（count/mean/std/min/max/median）集計を実装。
  - research パッケージの __all__ を整備し、zscore_normalize（data.stats 由来）を再エクスポート。

- 特徴量生成（strategy/feature_engineering）
  - research 側で算出した生ファクターを正規化・合成して features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへの日付単位置換（トランザクション + バルク挿入で原子性確保）。冪等性を担保。

- シグナル生成（strategy/signal_generator）
  - features テーブルと ai_scores を統合し、final_score を計算してシグナル（BUY/SELL）を生成する処理を実装（generate_signals）。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、デフォルト閾値 0.60。
    - スコア変換ユーティリティ（シグモイド、欠損補完ルール、平均化処理）。
    - Bear レジーム検出（ai_scores の regime_score 平均が負、ただしサンプル数 >= 3 の場合のみ Bear と判定）による BUY 抑制。
    - エグジット（SELL）判定: ストップロス（終値/avg_price - 1 <= -8%）および final_score の閾値未満判定を実装。保有銘柄の価格欠損時は SELL 判定をスキップして安全性を優先。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性確保）。SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。

### Security
- 外部入力（RSS/XML）のパースに defusedxml を使用し、XML に起因する攻撃リスクを低減。
- ニュース収集での URL 正規化により SSRF やトラッキングパラメータ依存のリスクを軽減する設計方針を採用。

### Database / Reliability
- DuckDB を前提とした設計。データ保存は ON CONFLICT によるアップサート戦略で冪等性を確保。
- 重要な DB 操作（features / signals の置換など）はトランザクションで原子性を担保し、ROLLBACK 失敗時のログ出力を実装。

### Notes / Known limitations
- execution 層（発注 API）への直接的な依存は現行実装には含まれていない（戦略モジュールは発注層と独立している設計）。
- 一部の戦略的条件（例: トレーリングストップや時間決済）は positions テーブルに追加のメタ情報（peak_price / entry_date など）が必要で、現バージョンでは未実装。
- news_collector の完全な一覧取得・URL の厳格なセキュリティチェック（IP レンジ拒否など）は実運用での追加検討が必要。
- 外部 API 呼び出し（J-Quants）での詳細なエラー処理・監視は実運用に応じてチューニングが必要。

---

今後のリリースでの予定（一例）
- execution 層の実装（kabu API 連携、注文管理）
- monitoring モジュールの実装（監視アラート・Slack 通知の具体化）
- ニュース記事の銘柄紐付け（NLP ベースのシンボル抽出・マッチング）
- 性能改善（DuckDB クエリチューニング、並列取得・処理）

もし CHANGELOG に追記してほしい項目（例えばリリース日や追加の実装詳細）があれば教えてください。