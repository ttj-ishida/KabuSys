# Changelog

すべての変更は Keep a Changelog の方針に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 今後の変更を記載するセクションです。

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理
  - 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装。
    - .env, .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサ（コメント・export 形式・クォート・エスケープ対応）。
    - Settings クラスで各種必須設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のチェック）とヘルパー is_live / is_paper / is_dev。

- データ取得・保存 (J-Quants)
  - J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
    - 固定間隔（スロットリング）によるレート制御（120 req/min の RateLimiter）。
    - HTTP リトライ（最大 3 回、指数バックオフ、408/429/5xx 対応）。429 の場合は Retry-After を優先。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token のモジュールローカルキャッシュ。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を使用して重複を排除。
    - 入出力変換ユーティリティ (_to_float, _to_int) を実装し、壊れた文字列データや空値に対して頑健に動作。

- ニュース収集（RSS）
  - ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（fetch_rss）、XML パース（defusedxml を使用して安全性向上）。
    - コンテンツ前処理（URL 除去、空白正規化）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - SSRF 対策: スキーム検証（http/https のみ）、プライベート IP/ホストの判定、リダイレクト時の検査用ハンドラ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後の検査（Gzip bomb 対策）。
    - DB 保存: raw_news へのチャンク INSERT（INSERT ... RETURNING id で新規挿入のみを返す）、news_symbols への銘柄紐付けをバルク挿入するユーティリティ（トランザクションを使用）。
    - 銘柄コード抽出機能（4桁数列の正規表現 + known_codes フィルタ）。
    - 統合ジョブ run_news_collection により複数ソースの収集と保存・紐付けを管理。

- リサーチ（特徴量・ファクター）
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）: DuckDB の prices_daily を参照し、指定ホライズン（既定 [1,5,21]）のリターンを一括取得。
    - IC（Spearman）計算（calc_ic）：ファクターと将来リターンのランク相関を手計算で実装。必要件数未満時は None を返す。
    - ランク化ユーティリティ（rank）とファクター統計サマリー（factor_summary）。
    - pandas など外部ライブラリに依存しない純標準ライブラリ実装。
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（calc_momentum）: 1m/3m/6m リターン、MA200 乖離（ma200_dev）を計算。過去データ不足時は None。
    - Volatility/流動性（calc_volatility）: 20日 ATR（true range の扱いに注意）、ATR の相対値、20日平均売買代金、出来高比率を計算。
    - Value（calc_value）: raw_financials から直近財務数値を取得し PER/ROE を計算（EPS が 0/欠損なら PER は None）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。prices_daily / raw_financials のみ参照し、本番発注 API 等にはアクセスしない設計。

- DuckDB スキーマ初期化
  - スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw 層テーブル DDL（raw_prices, raw_financials, raw_news, raw_executions 等）の CREATE 文を定義。
    - 3 層構造（Raw / Processed / Feature）設計の基礎を準備。

### 変更 (Changed)
- 初期リリースのため該当なし（新規追加のみ）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- XML パーサに defusedxml を採用し XML 関連攻撃を軽減（news_collector）。
- RSS フェッチの SSRF 対策:
  - URL スキーム検証（http/https のみ許可）。
  - リダイレクト先のスキーム／ホスト検証を行うカスタム RedirectHandler を導入。
  - ホストのプライベート IP 判定。プライベートアドレスへのアクセスを拒否。
- ネットワーク対策:
  - レスポンスサイズ制限、gzip 解凍後サイズチェック、タイムアウトの設定。
- API クライアント:
  - トークン自動リフレッシュの上限を設け、無限再帰を防止。

### その他（ドキュメント・設計ノート）
- 各モジュールは「本番の発注 API にはアクセスしない」「DuckDB の既存テーブルのみ参照/保存する」等の安全基準を満たすよう設計されています（特に research モジュール）。
- ロギングを多用し、処理の成功/失敗を記録する設計（各種 logger.debug/info/warning/exception を利用）。
- テスト可能性を考慮し、news_collector._urlopen はテスト時にモックで差し替えられるように実装。

---

今後の予定（例）
- strategy / execution / monitoring 実装の拡充（注文ロジック・約定処理・監視通知）。
- Processed / Feature 層の ETL 実装、特徴量パイプラインの最適化。
- 単体テスト・統合テストの追加と CI パイプラインの整備。

(必要があれば、各機能に対するマイグレーション手順や使用例を追記します。)