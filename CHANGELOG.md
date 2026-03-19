Keep a Changelog
=================

すべての重要なリリースノートをこのファイルで管理します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。日本株自動売買のためのコア機能を実装しました。
  - パッケージ初期化
    - src/kabusys/__init__.py: バージョン 0.1.0、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
  - 設定管理
    - src/kabusys/config.py:
      - .env ファイルおよび環境変数からの自動設定読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
      - .env, .env.local の読み込み順序を実装（.env.local が上書き）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
      - export 形式、クォートあり/なし、インラインコメント処理など堅牢な .env パースロジックを導入。
      - 必須値取得ヘルパー _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
      - 環境（KABUSYS_ENV）およびログレベル（LOG_LEVEL）のバリデーションを実装。デフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）を設定。
  - Data 層（J-Quants クライアント）
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。ページネーション対応の fetch_* API（株価, 財務, カレンダー）を提供。
      - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
      - ネットワーク/HTTP エラーに対する再試行（指数バックオフ, 最大 3 回）、429 の Retry-After 優先処理を実装。
      - 401 (Unauthorized) 受信時にはリフレッシュトークンから ID トークンを自動再取得して再試行するロジックを実装。
      - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存。
      - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の不正や欠損に対して安全に処理。
  - Data 層（ニュース収集）
    - src/kabusys/data/news_collector.py:
      - RSS フィードからのニュース収集機能を実装（デフォルトで Yahoo Finance のビジネスカテゴリ）。
      - 記事ID に URL 正規化後の SHA-256 ハッシュ（先頭32文字）を利用して冪等性を確保。
      - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリキーソートを実施。
      - defusedxml を利用した安全な XML パース、受信サイズ上限（10MB）、HTTP スキーム検証など SSRF / XML Bomb / DoS 対策を考慮。
      - DB 保存はチャンク化して一トランザクションで実行し、INSERT の実際の挿入数を正しく扱う設計。
  - Research 層（因子計算・解析）
    - src/kabusys/research/factor_research.py:
      - Momentum（1M, 3M, 6M リターン、MA200 乖離）、Volatility（20日 ATR, 相対 ATR, 平均売買代金, 出来高比率）、Value（PER, ROE）を計算する関数を実装。
      - DuckDB のウィンドウ関数を活用し、欠損や不足データに対する取り扱いを明示。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算 (calc_forward_returns)、IC（スピアマン ρ）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク変換 (rank) を実装。
      - pandas 等外部依存を持たない純粋な実装。
    - src/kabusys/research/__init__.py: 主要関数をエクスポート。
  - Strategy 層
    - src/kabusys/strategy/feature_engineering.py:
      - research の生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
      - 指定列を Z スコア正規化し ±3 でクリップ。features テーブルへ日付単位で置換（トランザクションで原子性確保）。
      - ルックアヘッドバイアスを回避するため target_date 時点のデータのみ使用。
    - src/kabusys/strategy/signal_generator.py:
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重み付けと正規化（デフォルト重みは Model に基づく）を実装。
      - Bear レジーム検知（ai_scores の regime_score の平均が負で一定サンプル数以上の場合）により BUY 抑制。
      - BUY シグナル閾値（デフォルト 0.60）を超えた銘柄に対する BUY、保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）に基づく SELL を生成。
      - signals テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - src/kabusys/strategy/__init__.py: build_features / generate_signals をエクスポート。
  - 共通設計・品質上の考慮
    - ルックアヘッドバイアス防止の明示（target_date 時点のみ参照）。
    - 冪等性を重視した DB 操作（DELETE + INSERT や ON CONFLICT を利用）。
    - ロギングによる警告・情報出力を多用し、欠損や異常時の挙動を追跡可能に。
    - execution モジュールはプレースホルダ（実装は今後）、monitoring はパッケージに含める設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- ニュース収集で defusedxml を使用、受信サイズ制限、URL スキーム検証等を行い外部入力に対する安全性を高めています。
- J-Quants クライアントはトークンリフレッシュ・再試行・レート制御を実装し、意図しない情報漏洩や過負荷を抑制します。

Known limitations / Todo
- signal_generator のエグジット条件でトレーリングストップや時間決済（保有日数超過）は未実装。positions テーブルに peak_price / entry_date が必要（コメント記載）。
- execution（発注）層は未実装で、signals テーブルへの出力までが本リリースの責務。
- monitoring サブパッケージの具体的実装は未提供（パッケージ API には含めているが内部未実装）。

脚注
- 設定キー例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db

（以降のリリースでは新機能、バグ修正、API 変更点をここに追記します）