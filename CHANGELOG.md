CHANGELOG
=========

すべての注目すべき変更履歴はこのファイルに記載します。
このプロジェクトは Keep a Changelog の慣例に従います。
非互換性のある API 変更は "Changed"、バグ修正は "Fixed"、新機能は "Added" に記載します。

Unreleased
----------

なし

[0.1.0] - 2026-03-21
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買ライブラリを公開。
  - パッケージ基礎
    - パッケージバージョンを __version__ = "0.1.0" として定義。
    - パッケージ公開 API: data, strategy, execution, monitoring（execution はプレースホルダ）。
  - 設定 / 環境管理 (kabusys.config)
    - .env ファイルまたは環境変数からの設定読み込みを実装。プロジェクトルートを .git または pyproject.toml から検出して自動読み込み。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export 形式、クォート、インラインコメント等に対応。
    - Settings クラスを提供（settings インスタンス）。主なプロパティ:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN, 必須)
      - kabu_api_password (KABU_API_PASSWORD, 必須)
      - kabu_api_base_url (KABU_API_BASE_URL, デフォルト http://localhost:18080/kabusapi)
      - slack_bot_token / slack_channel_id (必須)
      - duckdb_path / sqlite_path（デフォルトパス）
      - 環境 (KABUSYS_ENV: development / paper_trading / live) と log_level の検証、is_live / is_paper / is_dev の判定ユーティリティ
  - データ取得・保存 (kabusys.data)
    - J-Quants クライアント (data.jquants_client)
      - API 呼び出しラッパーを実装。レート制限を固定間隔スロットリングで制御（120 req/min）。
      - リトライ（指数バックオフ、最大 3 回）・429 の Retry-After 尊重、408/429/5xx をリトライ対象。
      - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行。
      - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
      - DuckDB への保存用関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供。ON CONFLICT DO UPDATE により冪等性を確保。
      - 内部ユーティリティ: 型変換ヘルパー _to_float / _to_int。
    - ニュース収集 (data.news_collector)
      - RSS から記事を収集して raw_news に保存。デフォルト RSS ソースに Yahoo Finance を含む。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。トラッキングパラメータ除去、フラグメント削除、キーソート等で正規化。
      - defusedxml を利用して XML 脆弱性（XML Bomb 等）に対処。
      - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10 MB)、HTTP スキーム検証、SSRF 対策を考慮。
      - バルク挿入のチャンク化で DB 負荷を抑制。
  - 研究用モジュール (kabusys.research)
    - factor_research: calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials テーブルのみを参照し、(date, code) ベースの結果を返す。
      - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日データ不足時は None）。
      - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日窓、部分窓での平均算出）。
      - Value: per / roe（raw_financials の最新財務データを使用）。
    - feature_exploration: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman のランク相関）、factor_summary（基本統計）、rank（平均ランク処理）。
    - research.__init__ で上記ユーティリティをエクスポート。
    - 実装方針: pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。
  - 戦略モジュール (kabusys.strategy)
    - feature_engineering.build_features
      - research モジュールが計算した生ファクターを統合し、ユニバースフィルタ（最低株価 = 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 指定日で Z スコア正規化（指定列）→ ±3 でクリップ → features テーブルへ日付単位で置換（トランザクションで原子性確保）。
      - DuckDB 接続を受け取り prices_daily / raw_financials を参照。
    - signal_generator.generate_signals
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出し、重み付き合算で final_score を計算。
      - デフォルト重みや閾値を定義（デフォルト閾値 BUY=0.60、デフォルト重みは momentum:0.40 など）。weights は検証・正規化して合計1に調整。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
      - SELL 判定（エグジット）としてストップロス（-8%）とスコア低下（threshold 未満）を実装。positions と prices_daily を参照して判定、signals テーブルへ日付単位で置換。
      - 未登録 AI スコアは中立値で補完、欠損コンポーネントは中立値 0.5 で補完（不当な降格回避）。
  - ロギング・エラーハンドリング
    - 各処理で適切な警告/情報ログを出力。DB トランザクションでエラー時に ROLLBACK を試行し、失敗もログ出力。

Changed
- 初回公開版のため該当なし。

Fixed
- 初回公開版のため該当なし。

Deprecated
- 初回公開版のため該当なし。

Removed
- 初回公開版のため該当なし。

Security
- news_collector で defusedxml を採用して XML に起因する攻撃を軽減。
- URL 正規化とスキーム検証により SSRF/トラッキングリスクを軽減。
- J-Quants クライアントはトークン自動更新の際の無限ループ回避ロジックを有する。

Notes / Known limitations
- エグジット条件の一部（トレーリングストップ、時間決済など）は未実装。これらは positions テーブルに peak_price や entry_date などの追加情報が必要。
- DB スキーマの事前準備が必要（主に期待されるテーブル: raw_prices, prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news）。関数はこれらのスキーマに依存して動作する。
- news_collector の既定 RSS は Yahoo（DEFAULT_RSS_SOURCES）だが、外部ソースは追加可能。
- research モジュールは外部依存を避ける方針のため pandas 等を使用していない。大量データの高度な分析では使い分けを検討のこと。
- J-Quants クライアントは 120 req/min の制約を前提としているため、大規模並列取得は設計上抑制される。

Migration / Usage tips
- 設定は環境変数で与えるかプロジェクトルートの .env / .env.local を利用。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要 API:
  - settings: 環境設定アクセス (kabusys.config.settings)
  - data.jquants_client.get_id_token / fetch_* / save_*: データ取得 → DuckDB 保存
  - research.calc_momentum/calc_volatility/calc_value: ファクター計算
  - strategy.build_features(conn, target_date): features テーブル作成
  - strategy.generate_signals(conn, target_date, threshold?, weights?): signals 作成
- DuckDB コネクションを渡して使用。トランザクションは内部で管理するが、外部で BEGIN/COMMIT を行わないこと（内部で置換を行うため）。

ライセンス
- 初回リリース。ライセンス情報はプロジェクトルートを参照してください（pyproject.toml 等）。

-- End of CHANGELOG --