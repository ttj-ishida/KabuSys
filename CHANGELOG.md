CHANGELOG
=========

すべての重要な変更履歴をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Security, etc.）ごとに記載します。
- 版は semver を採用します。

[Unreleased]
------------

（現時点では未リリースの変更はありません。）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回公開: KabuSys 0.1.0 を追加。
- パッケージ初期化:
  - pakage __init__ に __version__ = "0.1.0" と主要サブパッケージの公開宣言を追加。
- 設定管理:
  - kabusys.config モジュールを追加。
  - .env ファイル自動読み込み機能を実装（読み込み順: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス、クォート処理、インラインコメント処理等に対応）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / ログレベル等のプロパティ（必須環境変数の検査とバリデーション含む）を追加。
  - 有効な KABUSYS_ENV 値（development, paper_trading, live）と LOG_LEVEL の検証を実装。
- データ取得・保存（J-Quants）:
  - kabusys.data.jquants_client モジュールを追加。
  - API 呼び出し共通処理: 固定間隔レートリミッタ（120 req/min）、リトライ（指数バックオフ、最大3回）、401 発生時のトークン自動リフレッシュ、ページネーション対応。
  - get_id_token によるリフレッシュトークン → ID トークン取得。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装（ページネーション対応）。
  - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 入出力ユーティリティ（_to_float, _to_int）を追加し、不正データに対する安全な変換を提供。
- ニュース収集:
  - kabusys.data.news_collector モジュールを追加。
  - RSS フィード取得（fetch_rss）、記事前処理（URL 除去・空白正規化）、URL 正規化（トラッキングパラメータ除去）、記事 ID 生成（正規化 URL の SHA-256 部分）を実装。
  - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト検査用ハンドラ、ホストのプライベートアドレス判定）、許容スキームの制限（http/https のみ）、レスポンスサイズ上限（MAX_RESPONSE_BYTES）、gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - DB 保存: raw_news へのチャンク挿入（INSERT ... RETURNING で新規挿入 ID を返す）と news_symbols への紐付けバルク保存（トランザクションまとめ、チャンク処理）を実装。
  - 銘柄コード抽出: 正規表現ベースで 4 桁コード抽出し known_codes によるフィルタリングを実装。
  - run_news_collection により複数ソースを安全に収集・保存・銘柄紐付けする統合処理を提供。
- Research（特徴量・ファクター解析）:
  - kabusys.research パッケージ公開を追加（__init__ で主要関数を再エクスポート）。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: DuckDB の prices_daily を参照して指定日の将来リターン（任意ホライズン）を一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（少数レコード時は None）。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - factor_research モジュールを追加:
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離率を DuckDB の window 関数で計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を慎重に扱う。
    - calc_value: raw_financials と prices_daily を結合して PER（EPS 有効時）・ROE を計算。最新の報告日を銘柄毎に取得するロジックを実装。
  - いずれの research 関数も本番発注 API にアクセスせず DuckDB のテーブルのみを参照する設計。
- DuckDB スキーマ:
  - kabusys.data.schema モジュールを追加し、Raw Layer（raw_prices, raw_financials, raw_news, raw_executions 等）の DDL 定義を含む（raw_executions の定義はファイル末尾で継続）。
  - スキーマは DataSchema.md 想定仕様に基づく 3 層アーキテクチャ（Raw / Processed / Feature / Execution）を念頭に構築。

Changed
- （初版）パッケージ構成をプロジェクト基準で整理（config, data, research, strategy, execution, monitoring などのモジュール分割）。

Fixed
- （初版）複数の入力データ（RSS, API）での不正値や欠損に対する堅牢化を実装（PK 欠損行のスキップ、値変換関数の堅牢化、XML パース失敗時のログとスキップ等）。

Security
- NewsCollector に SSRF 向けの多層防御を実装:
  - リダイレクト先検査（スキーム検証、プライベートアドレス検出）。
  - ホストのプライベートアドレス判定（DNS 解決した A/AAAA レコードも検査）。
  - URL スキーム制限（http/https のみ）。
  - defusedxml を利用して XML ベース攻撃を緩和。
  - 最大受信バイト数・gzip 解凍後サイズチェック（メモリ DoS / Gzip bomb 対策）。
- J-Quants クライアント:
  - レート制限（固定間隔）とリトライロジックにより API 制限・過負荷を回避。
  - 401 時の安全なトークンリフレッシュ（allow_refresh フラグで無限再帰を防止）。

Notable internal behavior / limitations
- .env パーサは一般的な shell 形式に対応するが、すべての edge case を網羅するわけではありません。
- Research / factor 計算は prices_daily / raw_financials テーブルのみ参照する設計で、本番注文や kabu API へのアクセスは行いません。
- jquants_client は標準ライブラリの urllib を利用しており、外部 HTTP クライアント（requests 等）には依存していません。
- DuckDB の一部スキーマ定義（raw_executions など）はファイル末尾で続く実装を想定しています（このスナップショットでは一部が続きます）。
- NewsCollector の銘柄抽出は簡易な 4 桁数字検出（\b\d{4}\b）に基づくため、文脈に依存する誤検出や見落としがあり得ます。known_codes を与えてフィルタリングすることを推奨します。

Required environment variables
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか

Acknowledgements / Notes
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は、コミットログやリリース目的に応じて追記・修正してください。