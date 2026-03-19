# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基盤となる以下の機能を実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にバージョン情報を追加（__version__ = "0.1.0"）し、主要サブパッケージを __all__ で公開。
  - 空のサブパッケージプレースホルダを配置: execution, strategy（今後の実装用）。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途想定）。
  - .env パーサを実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 上書き制御と OS 環境変数の保護機構（protected set）を実装。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス設定）
    - KABUSYS_ENV 値検証（development / paper_trading / live）
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティプロパティ

- データ取得・保存（J-Quants クライアント） (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対応: 120 req/min に基づく固定間隔スロットリング（RateLimiter）。
  - 再試行 (retry) ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - ページネーション対応（pagination_key）。
  - DuckDB 用の保存関数（冪等）:
    - save_daily_quotes -> raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar へ ON CONFLICT DO UPDATE
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、入力データの頑健な取り扱いを実現。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と前処理、DuckDB への保存ワークフローを実装。
  - 設計上の対策:
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化。
    - defusedxml を用いた安全な XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - リダイレクト検査用ハンドラ (_SSRFBlockRedirectHandler)
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかを検査
      - http/https 以外のスキームを拒否
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の検証（Gzip bomb 対策）
    - テキスト前処理 (URL 除去、空白正規化)
    - raw_news テーブルへのチャンクINSERT（INSERT ... RETURNING）とトランザクション管理
    - news_symbols（記事 - 銘柄紐付け）を一括で保存する内部ユーティリティ
    - 銘柄コード抽出ユーティリティ (4桁数字の抽出 & known_codes フィルタ)
    - 統合収集ジョブ run_news_collection: 複数ソースの独立処理、エラーハンドリング、紐付け処理

- 研究（Research）モジュール (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定基準日の終値から将来リターン（任意の営業日ホライズン）を計算
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（Information Coefficient）計算
    - rank: 同順位は平均ランクとするランク変換（丸め誤差対策あり）
    - factor_summary: 各ファクター列に対する基本統計量（count/mean/std/min/max/median）
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部ライブラリに依存しない実装
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials の最新財務データと価格を組み合わせて PER / ROE を算出
    - 大量データを効率的に取得するための SQL ウィンドウ関数中心の実装、データ不足時は None を返す設計

- スキーマ初期化 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層のうち Raw 層のDDLを実装）:
    - raw_prices, raw_financials, raw_news, raw_executions（途中までの定義を含む）
  - DDL を文字列で保持し、初期化に利用可能な構造に。

### 修正・改善 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Removed / Deprecated)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- News 集約で以下の安全対策を導入:
  - defusedxml による安全な XML パース
  - SSRF 対策（リダイレクト時のスキーム/ホスト検査、発信先のプライベートIPブロック）
  - レスポンスサイズ制限と gzip 解凍後検査（DoS / zip bomb 対策）
- J-Quants クライアント: レート制限（固定間隔スロットリング）およびリトライポリシーにより外部 API への過負荷を防止

---

注意:
- 本バージョンは基盤実装に注力しており、strategy / execution の実装はこれから追加されます。
- DuckDB のスキーマ定義は Raw 層を中心に提供しており、実運用に際しては環境に応じたテーブル追加・マイグレーションが必要です。
- .env パーサ・自動ロードはプロジェクトルート探索に依存するため、パッケージ配布後は配置場所に注意してください。