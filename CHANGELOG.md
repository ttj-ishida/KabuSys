# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このファイルは、ソースコードから推測される実装内容に基づいて作成しています。

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - プロジェクトルート自動検出 (.git または pyproject.toml を起点) による .env 自動ロード
  - ロード優先度: OS 環境 > .env.local > .env
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 行パーサ: コメント、export プレフィックス、クォート（シングル/ダブル）とエスケープ対応、インラインコメント処理などに対応
  - 環境変数保護（既存 OS 環境変数の上書き回避）および上書き制御
  - Settings クラス: J-Quants / kabu API / Slack / データベースパス等の取得用プロパティを提供
  - 設定値のバリデーション: KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証
  - パス値は Path 型で返却（duckdb/sqlite の既定パスあり）

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装
  - レート制限対応: 固定間隔スロットリング（120 req/min）
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を再試行対象
  - 401 時の自動トークンリフレッシュ（1 回だけリフレッシュして再試行）
  - ページネーション対応（pagination_key）
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB 保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を用いた重複排除
    - fetched_at を UTC ISO 形式で記録（look-ahead bias 対策）
  - ユーティリティ: 型変換ヘルパー _to_float / _to_int、ID トークンキャッシュ

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集、前処理、DuckDB への冪等保存を実装
  - デフォルト RSS ソース（例: Yahoo Finance）
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等対策）
    - URL スキーム検証（http/https のみ許可）
    - SSRF 対策: リダイレクト先のスキーム/ホスト検証、プライベート IP 判定（DNS 解決結果も検査）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）
  - URL 正規化とトラッキングパラメータ除去（utm_ 等）
  - 記事 ID: 正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保
  - テキスト前処理: URL 除去、空白正規化
  - 銘柄コード抽出: 4 桁数字パターンから既知コード集合をフィルタ
  - DB 保存: INSERT ... RETURNING を用いて実際に挿入された新規記事 ID を返す
  - 複数記事／銘柄紐付けのバルク挿入をチャンク化してトランザクションで処理

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw 層テーブル定義の DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）
  - データレイヤー設計（Raw / Processed / Feature / Execution 層）をドキュメントに反映

- リサーチモジュール (kabusys.research)
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL LEAD を使用）
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、ties 対応）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
    - rank ユーティリティ（同順位は平均ランク、丸めて ties 検出）
    - 標準ライブラリのみで実装（pandas 等に依存しない）
  - factor_research:
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ / 流動性 calc_volatility（20 日 ATR、相対 ATR、20 日平均出来高・売買代金）
    - バリュー calc_value（raw_financials と prices_daily を組み合わせて PER/ROE を計算）
    - SQL ウィンドウ関数を多用した DuckDB での効率的な集計実装
    - データ不足時は None を返す設計（堅牢性重視）

- モジュール再エクスポート (kabusys.research.__init__)
  - 主要関数を __all__ にまとめて外部から簡単に利用可能に

### 変更 (Changed)
- なし（初版のため既存からの変更は無し）

### 修正 (Fixed)
- なし（初版のため）

### セキュリティ (Security)
- RSS XML パースに defusedxml を導入
- RSS フェッチ時の SSRF 対策（リダイレクト検査、プライベート IP チェック）
- HTTP レスポンス読み込みバイト数制限、gzip 解凍後のサイズチェックを実装し、リソース枯渇攻撃に対処

### 既知の未実装 / 注意点 (Known issues / Notes)
- calc_value: PBR や配当利回りは現バージョンでは未実装（ドキュメントに明記）
- raw_executions テーブル定義は部分的に示されている（コード抜粋の都合で続きが存在する可能性あり）
- feature_exploration モジュールは標準ライブラリのみを使用しているため、大規模データ処理時は pandas 等を用いたバッチ処理の方が高速な場合がある
- NEWS の記事ID生成は URL 正規化に依存するため、外部フィードの形式によっては重複検出に差異が生じる可能性あり

---

今後のリリースでは以下を想定：
- Strategy / Execution 層の具体的な発注ロジック（kabu ステーション API 統合）
- モニタリング / Slack 通知の実装強化
- テストカバレッジ追加と CI ワークフロー
- 性能改善（大規模データ向けのバルク処理最適化）