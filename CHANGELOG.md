CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを実装。
  - パッケージ初期化
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring
  - 設定/環境変数管理 (kabusys.config)
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み
    - .env パーサ実装: export PREFIX、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント処理等に対応
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション
    - Settings クラス実装: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルトあり）、Slack トークン/チャネル、DB パス（DuckDB/SQLite）、KABUSYS_ENV / LOG_LEVEL 検証、is_live/is_paper/is_dev 等のユーティリティ
  - Data モジュール
    - J-Quants API クライアント (kabusys.data.jquants_client)
      - 固定間隔レートリミッタ（120 req/min）を実装
      - HTTP リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）
      - 401 受信時のトークン自動リフレッシュ（1回）とモジュールレベルのトークンキャッシュ
      - ページネーション対応の fetch_* 関数:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
        - save_daily_quotes -> raw_prices
        - save_financial_statements -> raw_financials
        - save_market_calendar -> market_calendar
      - データ変換ユーティリティ: _to_float, _to_int（"1.0" などを安全に処理）
    - ニュース収集 (kabusys.data.news_collector)
      - RSS フィード取得 + XML パース (defusedxml 使用)
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
      - SSRF 対策: スキーム検証、ホストのプライベートアドレス判定、リダイレクト時の検査ハンドラ実装
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の検査（Gzip bomb 対策）
      - テキスト前処理（URL 除去、空白正規化）
      - DB への保存: save_raw_news（チャンク化 INSERT + トランザクション + INSERT ... RETURNING）、save_news_symbols、_save_news_symbols_bulk
      - 銘柄コード抽出ユーティリティ（4桁数字、既知銘柄セットによるフィルタ）
      - 統合収集ジョブ run_news_collection（複数ソースの個別エラーハンドリング、既知銘柄紐付け）
      - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定
  - Research / Factor モジュール
    - feature_exploration:
      - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1/5/21 営業日）先までの将来リターンを一括 SQL で計算
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ランク関数含む）
      - factor_summary: 基本統計量（count, mean, std, min, max, median）集計
      - rank: 同順位は平均ランクを与える実装（丸め誤差対策で round を利用）
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算
      - calc_volatility: atr_20（20日 ATR）/atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を厳密に制御）
      - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（報告日に基づく最新レコード選択）
    - research パッケージのエクスポートを整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）
  - DuckDB スキーマ (kabusys.data.schema)
    - Raw レイヤーの主要テーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions などの DDL を用意）
    - スキーマ初期化用の DDL をコード内で管理

Security
- ニュース収集での SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト時の検査）
- XML パースに defusedxml を使用し XML ベクタ対策
- レスポンスサイズ制限と gzip 解凍後の検査でメモリ DoS を軽減
- J-Quants クライアントでトークン自動更新のループ防止（allow_refresh フラグ）とキャッシュ
- DB 保存は ON CONFLICT / トランザクションを利用し整合性を確保

Fixed / Robustness improvements
- .env パーサで export プレフィックス、クォート内部のエスケープ、インラインコメント等に対応（より既知の .env 形式に近い挙動）
- true_range / ATR 計算で high/low/prev_close の NULL を正しく伝播させ、欠損データでの過大評価を防止
- 数値変換ユーティリティ（_to_int/_to_float）で不正入力や小数部を安全に扱うロジックを導入
- fetch_* のページネーション処理で pagination_key の再利用ループを防止
- ニュース保存処理でチャンク化/INSERT ... RETURNING により実際に挿入された件数を正確に把握

Notes / Known limitations
- calc_value は現状で PER / ROE を提供。PBR・配当利回り等は未実装（将来追加予定）。
- Research モジュールは DuckDB 内の prices_daily / raw_financials 等のテーブル存在を前提とする（外部 API への発注等は行わない設計）。
- 外部ライブラリへの依存を最小限にしているため、pandas 等を使用しない純 Python 実装になっている（大規模データ処理ではパフォーマンス検証が必要）。
- ニュースの銘柄抽出は単純な 4 桁数字マッチと既知コードフィルタに依存しているため、高度なNERは未導入。

------------------------------------------------------------
（以降のリリースでは Added/Changed/Deprecated/Removed/Fixed/Security の各セクションを追記してください。）