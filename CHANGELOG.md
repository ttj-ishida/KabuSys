CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース: 基本的な日本株自動売買ライブラリを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: パッケージ名とバージョンを定義（__version__ = "0.1.0"）。公開 API: data, strategy, execution, monitoring をエクスポート。

  - 環境設定 / 設定管理
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - .env 行パーサー実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
      - 環境変数必須チェック用 _require と Settings クラスを提供。主要な設定プロパティ:
        - JQUANTS_REFRESH_TOKEN（必須）
        - KABU_API_PASSWORD（必須）
        - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
        - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
        - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト: data/monitoring.db）
        - KABUSYS_ENV（development|paper_trading|live の検証あり）
        - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）
      - OS 環境変数の保護機能（.env による上書きを制限）。

  - データ取得 / 保存（J-Quants API クライアント）
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアント実装（ページネーション対応）。
      - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
      - リトライロジック: 指数バックオフ、最大リトライ回数 3、HTTP 408/429 と 5xx をリトライ対象。
      - 401 発生時にリフレッシュトークンで ID トークンを自動更新して再試行（1 回のみ）。
      - JSON デコードやネットワークエラーに対する扱いを整備。
      - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
      - DuckDB への冪等保存: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による更新）。
      - 型安全な変換ユーティリティ: _to_float, _to_int。
      - 取得時刻 (fetched_at) を UTC ISO フォーマットで記録（Look-ahead バイアス防止のため）。

  - ニュース収集（RSS）
    - src/kabusys/data/news_collector.py:
      - RSS から記事を収集し raw_news / news_symbols 等に保存するための実装基盤。
      - defusedxml を用いた XML パーシング（XML Bomb 対策）。
      - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF/非 HTTP スキーム対策、チャンクバルク挿入などの安全対策を設計。
      - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を登録。

  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py:
      - calc_momentum: 約1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev) の計算。
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio) の計算。
      - calc_value: EPS/ROE 等の raw_financials を用いた PER/ROE の計算（target_date 以前の最新財務データを使用）。
      - 各関数は prices_daily / raw_financials のみ参照し、結果を date/code ベースの dict リストで返す。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
      - calc_ic: スピアマンランク相関（Information Coefficient）を計算（同順位は平均ランクで処理）。
      - rank: 値リストをランクに変換（同順位の平均ランク、丸めで ties 判定の頑健化）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出するユーティリティ。
    - re-export: research パッケージの __init__ で主要ユーティリティを公開。

  - 特徴量エンジニアリング（戦略入力）
    - src/kabusys/strategy/feature_engineering.py:
      - build_features: research の生ファクター（calc_momentum/calc_volatility/calc_value）を統合し、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5 億円）を適用。
      - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
      - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性保証）。
      - 価格欠損や非有限値への安全策を実施。

  - シグナル生成（戦略）
    - src/kabusys/strategy/signal_generator.py:
      - generate_signals: features と ai_scores を統合して各銘柄の final_score を計算し、BUY / SELL シグナルを生成。
      - コンポーネントスコア:
        - momentum, value, volatility, liquidity, news（AI）を計算するユーティリティを実装。
        - Z スコアをシグモイド変換し、欠損コンポーネントは中立 0.5 で補完（欠損ペナルティを緩和）。
      - デフォルト重みと閾値を実装（デフォルト重みは StrategyModel.md に準拠、閾値 default=0.60）。
      - ユーザー指定 weights の検証・正規化（未知キー・非数値・負値を無視、合計が 1.0 に再スケール）。
      - Bear レジーム判定: ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合に BUY を抑制。
      - SELL 条件（実装済）:
        - ストップロス: 終値 / avg_price - 1 < -8%
        - スコア低下: final_score < threshold
        - （未実装注意: トレーリングストップや時間決済は positions に peak_price / entry_date 等の追加情報が必要）
      - signals テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性保証）。
      - 保有銘柄の SELL を優先して BUY から除外するポリシー。

  - その他
    - src/kabusys/strategy/__init__.py: build_features / generate_signals をエクスポート。
    - ロガー使用と詳細な警告/情報ログを各主要処理に追加（操作失敗時のロールバック警告など）。

Security
- XML パースに defusedxml を利用（news_collector）。
- ニュース収集で受信バイト数を制限し DoS を軽減。
- .env 読み込みで OS 環境変数を保護する仕組みを実装。
- J-Quants クライアントでトークン自動リフレッシュと安全なリトライを実装。

Notes / Migration / 設定
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- オプション / デフォルト:
  - KABUSYS_ENV デフォルトは development（有効値: development, paper_trading, live）
  - LOG_LEVEL デフォルトは INFO
  - DUCKDB_PATH デフォルト data/kabusys.duckdb
  - SQLITE_PATH デフォルト data/monitoring.db
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。
- DuckDB テーブル構造（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar, raw_news 等）が前提です。マイグレーションやスキーマ作成は別途用意してください。

Known limitations / TODO
- news_collector の一部（記事 ID 生成や DB への紐付けなど）は設計に基づく実装が進行中（ファイル途中までの実装を含む）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルの追加情報が必要で未実装。
- 一部ベースライン（StrategyModel.md / DataPlatform.md）に準拠した設計参照があり、該当ドキュメントを参照してカスタマイズが必要。

Acknowledgements
- 内部で使用するアルゴリズムや設計はリポジトリ内の StrategyModel.md / DataPlatform.md 等の仕様に準拠しています。詳細は該当ドキュメントを参照してください。