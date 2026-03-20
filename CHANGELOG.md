CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
  - パッケージ構成:
    - kabusys.config: 環境変数／.env の自動ロードと設定ラッパー（Settings）。
    - kabusys.data: 外部データ取得および保存ロジック（J-Quants クライアント、ニュース収集など）。
    - kabusys.research: ファクター計算・探索ユーティリティ（momentum / volatility / value，forward returns，IC，統計サマリー等）。
    - kabusys.strategy: 特徴量エンジニアリングとシグナル生成ロジック（build_features, generate_signals）。
    - kabusys.execution / kabusys.monitoring: パッケージ公開名に含める（実装の拡張を想定）。

- 環境設定（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルートから自動読み込み（OS環境変数優先）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを探索する実装のため、CWD に依存しない自動ロードを実現。
  - .env 行の柔軟なパーシング:
    - コメント行、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 必須設定の検証を提供（未設定時に ValueError を送出）。
  - 設定項目の例（必須・デフォルトあり）:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意／デフォルト: KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi), DUCKDB_PATH, SQLITE_PATH
    - システム設定: KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL（DEBUG/INFO/...）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装:
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等なページネーション処理（pagination_key を追跡）。
    - リトライ（指数バックオフ、最大 3 回）およびステータス 408/429/5xx に対する再試行。
    - 401 発生時はトークン自動リフレッシュを行い 1 回のみ再試行。
    - id_token のモジュールレベルキャッシュを提供（ページネーション間で再利用）。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT（重複更新）で冪等性を確保。
  - データ型変換ユーティリティ (_to_float / _to_int) を実装し、受信データの堅牢な処理を実現。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news 等へ保存する骨格を実装。
  - セキュリティ・堅牢化:
    - defusedxml を使用した XML パース（XML Bomb 等の対策）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 挿入はバルクかつチャンク化（パフォーマンスと SQL 長制限対策）。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを登録（DEFAULT_RSS_SOURCES）。

- 研究用ファクター計算（kabusys.research.factor_research）
  - Momentum, Volatility, Value のファクター計算を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）。過去スキャン範囲はバッファ付き。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播制御等考慮）。
    - calc_value: per, roe（raw_financials の最新報告を結合）。
  - DuckDB の prices_daily / raw_financials テーブルのみを参照する設計（外部 API 呼び出しなし）。

- 研究用解析ユーティリティ（kabusys.research.feature_exploration）
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
  - calc_ic: スピアマン（順位）相関による IC 計算（同順位は平均ランク処理、最小サンプル数チェック）。
  - factor_summary: count/mean/std/min/max/median を出力する統計サマリー。
  - rank: 同順位を平均ランクで扱う安全なランク関数（浮動小数丸めで ties 検出の安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを取得して正規化・合成し、features テーブルへ UPSERT（日付単位で削除→挿入・トランザクションで原子性保証）。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value の結果をマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
  - 冪等性を重視（target_date 分を置換）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存（日付単位で置換）。
  - 実装要点:
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（シグモイド変換など）。
    - デフォルト重みと閾値: weights デフォルトはモデル定義（momentum 0.40 等）、閾値 default=0.60。
    - weights は部分的に上書き可能。未知キーや無効値は無視、合計が 1 でない場合は再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル最小数制約あり）。
    - SELL 条件（実装）:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - スコア低下: final_score < threshold
    - 保有ポジションの価格欠損等はログを出し判定をスキップする等、安全策を導入。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。
    - トランザクションによる原子性（DELETE → INSERT）。

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Security
- ニュース収集で defusedxml を採用し、受信サイズ制限や URL 正規化で攻撃耐性を向上。
- API クライアントでトークン管理・リトライ制御・レート制限を実装し、認証エラー時の自動リフレッシュを安全に扱う。

Database / Schema Notes
- 本バージョンで参照／更新される主なテーブル（DuckDB / SQLite 想定）:
  - raw_prices, raw_financials, market_calendar  (データ取得保存用)
  - prices_daily, features, ai_scores, positions, signals  (研究・戦略実行用)
  - raw_news, news_symbols  (ニュース集約用)
- 各種保存関数は ON CONFLICT による冪等性、戦略モジュールは日付単位の DELETE→INSERT による置換で原子性を確保。

Usage / Migration Notes
- 必須環境変数（設定がないと例外を送出）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みはデフォルトで有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要がある。
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかである必要がある。
- J-Quants API の利用にはリフレッシュトークン準備が必要。get_id_token() が自動でトークン取得・リフレッシュを行う。

開発者向け
- 単体テストや CI 実行時に環境依存の自動 .env 読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB 接続を渡す形で関数群（calc_*, build_features, generate_signals 等）を呼び出せます。これらは外部ネットワークや発注 API へ直接アクセスしない設計です。

Contributors
- 初版の実装はリポジトリ内の各モジュールに基づく（自動生成された CHANGELOG のため個別貢献者は未記載）。

-- end --