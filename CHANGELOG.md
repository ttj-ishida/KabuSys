# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

なお以下の変更履歴は、提供されたコードベースの内容から推測して作成した初期リリースのまとめです。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース（初期実装）。主要なモジュール群と基本機能を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - パッケージの公開 API（__all__）に data, strategy, execution, monitoring を設定（strategy / execution のサブパッケージはプレースホルダとして存在）。

- 環境 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を探索して読み込み。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env.local は .env を上書きする優先度設定。
  - .env ファイルのパースを堅牢に実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント判定等に対応）。
  - Settings クラスを提供し、必須環境変数取得（_require）、各種設定プロパティを定義:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの必須値。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）の Path オブジェクト返却。
    - is_live / is_paper / is_dev の便宜プロパティ。

- データ取得 / 永続化（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
    - レート制限（_RateLimiter、120 req/min 固定間隔スロットリング）を実装。
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx を再試行対象）。
    - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1回まで）を実装。
    - ページネーション対応（pagination_key）で全件取得。
    - 取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（冪等性のため ON CONFLICT / DO UPDATE を使用）。
    - 型変換ユーティリティ: _to_float, _to_int（入力の堅牢なパース処理を提供）。
    - fetched_at を UTC ISO8601 形式で記録し、look-ahead bias のトレースを容易に。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集・前処理・DB 保存パイプラインを実装。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - RSS 取得: fetch_rss（gzip 対応、最大受信バイト数制限、XML パースの堅牢化）。
    - defusedxml を使用して XML 攻撃を軽減。
    - SSRF対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先のスキーム / ホストを事前検証するカスタムリダイレクトハンドラ。
      - ホストがプライベートアドレスかチェックしてアクセス禁止。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事 ID の生成（正規化 URL の SHA-256 先頭 32 文字）。
    - テキスト前処理（URL 除去、空白正規化）を提供。
    - DB 保存:
      - save_raw_news: チャンク分割 + トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入 ID リストを返す。
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けをチャンク & トランザクションで保存し、実際に挿入された件数を返す。
    - 銘柄コード抽出: 4桁数字パターンによる抽出および known_codes によるフィルタ（重複除去）。

- データスキーマ (`kabusys.data.schema`)
  - DuckDB 用の DDL を定義・初期化するスクリプト（Raw Layer のテーブル定義を含む）。
    - raw_prices（生の株価データ）: (date, code) 主キー、各種型・制約付き。
    - raw_financials（生の財務データ）: (code, report_date, period_type) 主キー。
    - raw_news（ニュース記事）: id 主キー、datetime NOT NULL。
    - raw_executions（発注/約定）テーブル定義の雛形（ファイル末尾に断片あり）。
  - トランザクション整合性や型制約を考慮した設計。

- リサーチ / 特徴量計算 (`kabusys.research`)
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリーを実装。
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）への将来リターンを DuckDB の prices_daily テーブルから計算。SQL の LEAD を用いた一括取得。ホライズンの検証（1〜252 日）。
    - calc_ic: factor と forward リターンを code で結合し Spearman のランク相関（ρ）を計算。データ不足（有効レコード < 3）では None を返す。ランク計算は ties を平均ランクで処理。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算（None 値除外）。
    - rank: ランク変換ユーティリティ（丸め処理を行い ties を平均ランク化）。
    - 設計上、pandas 等外部ライブラリには依存せず標準ライブラリで実装。
  - factor_research: StrategyModel に基づく定量ファクター計算を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を prices_daily から計算。LAG / moving average を SQL ウィンドウ関数で実装。データ不足時は None を返す設計。
    - calc_volatility: atr_20（20日 ATR の単純平均）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日 / 20日平均）を計算。true_range の NULL 伝播制御や cnt による欠損判定を実装。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し、per（株価/EPS）、roe を計算。EPS が 0/NULL の場合は per を None とする。ROW_NUMBER を用いた最新レコード選択。
  - research パッケージの __init__ で主要関数群をエクスポート（zscore_normalize を含む外部ユーティリティへの参照も提供）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS 収集において SSRF 緩和策を実装（スキーム検証、プライベートホスト判定、リダイレクト検査）。
- XML パースに defusedxml を利用して XML 攻撃や XML Bomb に対処。
- レスポンスサイズ制限と gzip 解凍後のチェックでリソース消費攻撃を軽減。

### 既知の制限 / 注意点 (Known issues / Notes)
- strategy / execution パッケージはプレースホルダのみで、発注ロジックや実行エンジンの実装は含まれていない。
- schema.py の raw_executions テーブル定義はファイル切れのため断片的（提供コードから推測される部分実装あり）。実運用前に完全な DDL 確認が必要。
- research モジュールは標準ライブラリのみで実装されているため、pandas 等に慣れた開発者は初期実装の操作性に違和感がある可能性あり。
- 単体テストや統合テストはコードからは見えないため、実行前に十分なテストの追加を推奨。

### 互換性 (Compatibility)
- まだ初期リリースのため後方互換性に関する変更履歴は無し。

---

この CHANGELOG はコードから推測して作成したものであり、実際のコミットログやリリースノートとは差異がある可能性があります。必要に応じて差分（コミットハッシュ、PR 番号、より詳しい変更点）を追記してください。