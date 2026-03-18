Keep a Changelog 準拠 — CHANGELOG
===============================

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

v0.1.0 - 2026-03-18
-------------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)
- パッケージ公開インターフェース:
  - package-level __all__: data, strategy, execution, monitoring
- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml ベース）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応
  - 上書き制御 (override/protected) による安全な環境変数セット
  - Settings クラス提供（settings インスタンス）
    - 必須環境変数を要求: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi"
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API レート制御: 固定間隔スロットリング（120 req/min）
    - リトライ戦略: 指数バックオフ、最大3回（408/429/5xx を対象）、429 は Retry-After を尊重
    - 401 応答時の自動トークンリフレッシュ（1回のみ）とモジュール内トークンキャッシュ
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務四半期データ)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB への冪等保存関数:
      - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE
      - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と不正値処理）
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレーサビリティを確保

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードからの記事収集機能（デフォルト: Yahoo Finance ビジネス RSS を含む）
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 対策）
      - SSRF 対応: リダイレクト前後でスキーム検証、プライベートIP/ループバック/リンクローカルの拒否
      - URL スキーム検証 (http/https のみ)
      - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の再チェック
    - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成（utm_* 等トラッキングパラメータ削除）
    - テキスト前処理: URL 除去、空白正規化
    - DuckDB 保存:
      - save_raw_news: チャンク挿入 + INSERT ... RETURNING id を用い、新規挿入IDを返す（トランザクション管理）
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入（ON CONFLICT DO NOTHING, RETURNING 使用）
    - 銘柄抽出: 4桁数列パターンから known_codes に含まれるもののみ抽出（重複除去）
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソース単位で隔離されたエラーハンドリング）

  - DuckDB スキーマ定義 (kabusys.data.schema)
    - Raw layer の DDL 定義を含む（raw_prices, raw_financials, raw_news, raw_executions 等の雛形）
    - DataSchema に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した初期化用モジュール

- リサーチ・ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定基準日の終値から複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括取得
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランク処理、3 件未満で None）
    - rank: 同順位平均ランクの実装（丸め誤差対策に round(v,12) を使用）
    - factor_summary: count/mean/std/min/max/median を計算
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部 API へはアクセスしない、標準ライブラリで実装
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離 ma200_dev（過不足データは None）
    - calc_volatility: 20 日 ATR (atr_20)、相対ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio)
    - calc_value: raw_financials から最新財務を取得して PER (price / eps) と ROE を計算（EPS 不在/0 は None）
    - 実装ノート: スキャン範囲のカレンダーバッファや窓サイズの定数化、ウィンドウ内データ不足時の None 戻し
  - research パッケージ __init__ で主要関数を再エクスポート
  - zscore_normalize ユーティリティを kabusys.data.stats から利用（正規化ユーティリティを公開）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- defusedxml を用いた RSS XML パースによる安全化
- RSS フェッチで SSRF 対策（リダイレクト検査、プライベートアドレス拒否）
- .env 読み込み時のファイル読み取り失敗は警告で安全に無視

Known issues / Notes
- strategy/execution/monitoring パッケージは初期化ファイルのみで、戦略実装や発注エンジン統合は未実装（プレースホルダ）
- calc_value は現時点で PBR や配当利回りなど一部バリューメトリクスを未実装
- DuckDB のスキーマ定義は Raw レイヤー中心に実装。Processed/Feature 層の詳細 DDL は今後拡張予定
- research モジュールは設計上 pandas 等外部データ解析ライブラリに依存しない（標準ライブラリ実装）。大規模データ処理時の性能/利便性改善は今後検討
- J-Quants クライアントは urllib を使用した実装。商用での高負荷運用時は HTTP セッション管理や非同期化を検討すると良い

開発・使用上の参考
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みを無効にするには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- KABUSYS_ENV の有効値:
  - development, paper_trading, live
- LOG_LEVEL の有効値:
  - DEBUG, INFO, WARNING, ERROR, CRITICAL

今後の予定 (例)
- strategy と execution の統合（注文送信、ポジション管理、約定処理）
- Processed / Feature 層の DDL 完成・ ETL ジョブ実装
- research の高速化（pandas / numpy オプション実装）およびバックテスト基盤追加
- テストカバレッジ拡充と CI パイプラインの整備

-----