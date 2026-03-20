CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
初回リリース 0.1.0 の内容をコードベースから推測して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" の基本機能を実装。
  - パッケージ情報
    - src/kabusys/__init__.py: バージョン 0.1.0、公開モジュールの一覧を定義。

  - 設定・環境変数ロード
    - src/kabusys/config.py:
      - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルート検出を .git または pyproject.toml を基準に行い、__file__ を起点に探索するため配布後も動作。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサを強化:
        - export KEY=val 形式をサポート
        - シングル/ダブルクォート内のバックスラッシュエスケープをサポート
        - インラインコメント処理（クォートあり/なしでの挙動の違いを適切に処理）
      - Settings クラスで必須項目の取得と検証を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
      - 環境値の検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）をチェック。
      - デフォルトの DB パス設定（DUCKDB_PATH / SQLITE_PATH）をサポート。

  - データ取得・保存（J-Quants API）
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。日足、財務データ、マーケットカレンダーの取得機能を提供。
      - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
      - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
      - 401 Unauthorized 受信時はトークンを自動リフレッシュして 1 回だけリトライする安全策を実装（無限再帰回避）。
      - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
      - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - DuckDB への保存関数は冪等性を担保（ON CONFLICT DO UPDATE）:
        - save_daily_quotes / save_financial_statements / save_market_calendar
      - 数値変換ユーティリティ (_to_float, _to_int) を実装し、不正データ・空値に対処。
      - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスへの配慮。

  - ニュース収集
    - src/kabusys/data/news_collector.py:
      - RSS フィードからのニュース収集を実装（デフォルトソースに Yahoo Finance）。
      - セキュリティ対策: defusedxml を用いた XML パース、安全でないスキームの排除、受信サイズ上限（10MB）などを実装。
      - URL 正規化機能: トラッキングパラメータ（utm_*/fbclid 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
      - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
      - 大量挿入に配慮したチャンク処理、1 トランザクションでの保存、挿入件数の正確な把握を想定。

  - 研究用 / ファクター計算
    - src/kabusys/research/factor_research.py:
      - Momentum, Volatility, Value 等の定量ファクター計算関数を実装:
        - calc_momentum: mom_1m/mom_3m/mom_6m、MA200乖離（データ不足時は None）。
        - calc_volatility: ATR(20)、相対ATR(atr_pct)、20日平均売買代金、出来高比率。
        - calc_value: per/roe（raw_financials から最新財務データを取得して price と結合）。
      - 各関数は DuckDB の prices_daily / raw_financials を参照し、営業日とカレンダー日のバッファを考慮したスキャンレンジを採用。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算 calc_forward_returns（複数ホライズン、SQLで一括取得）。
      - IC（Spearman の ρ）計算 calc_ic（ランク付けは同順位を平均ランクで処理）。
      - factor_summary（count/mean/std/min/max/median）と rank ユーティリティを実装。
      - 外部ライブラリに依存せず標準ライブラリ + DuckDB の SQL で実装。

  - 戦略（特徴量整備・シグナル生成）
    - src/kabusys/strategy/feature_engineering.py:
      - 研究で計算した raw factors を正規化・合成して features テーブルに保存する build_features を実装。
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を適用。
      - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）後 ±3 でクリップして外れ値を抑制。
      - 日付単位での置換（DELETE + INSERT）をトランザクションで行い冪等性と原子性を担保。
    - src/kabusys/strategy/signal_generator.py:
      - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
      - デフォルト重みや閾値（default threshold = 0.60）を備え、ユーザ指定重みは検証・正規化して利用。
      - AI レジームスコアを集計して Bear 相場検出（サンプル数制限あり）を行い、Bear 時は BUY を抑制。
      - エグジット判定（STOP-LOSS -8%、スコア低下）を実装。価格欠損時の SELL 判定スキップや警告出力あり。
      - signals テーブルへの日付単位置換をトランザクションで行い冪等性を確保。
    - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。

  - データ統計ユーティリティ
    - src/kabusys/data/stats.py（参照あり）経由で zscore_normalize を利用（エクスポートは research/__init__ で提供）。

Documentation / Logging
- 各モジュールに詳細な docstring を追加し、処理フロー・設計方針・注意点（ルックアヘッドバイアス回避、冪等性、トランザクション処理など）を明記。
- 重要な分岐・例外発生時に logger.warning / logger.info / logger.debug を用いたログ出力を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- ニュース収集で defusedxml を使用、受信サイズ制限、SSRF の低減策（スキーム検査等）を導入。
- J-Quants クライアントで 401 の自動トークン更新時には無限再帰を防ぐフラグを導入。

Notes
- DB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など）はコードの期待を反映している前提。実運用ではスキーマの整合性確認が必要。
- 一部の機能（トレーリングストップ、時間決済など）はコード内で未実装として明記されている（将来的な実装予定）。
- 外部依存: duckdb, defusedxml が利用される想定。環境構築時にインストールが必要。

---