Keep a Changelog に準拠した変更履歴 (日本語)
すべての注目すべき変更をこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/

[0.1.0] - 2026-03-19
===================

Added
-----
- 初期リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - パブリックモジュール: data, strategy, execution, monitoring

- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読込する機能を実装。
  - 読み込み挙動:
    - OS 環境変数 > .env.local > .env の優先順位。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export 形式、クォート内のエスケープ、インラインコメント処理などに対応。
    - 既存 OS 環境変数は保護され、.env.local の override は制御可能。
  - Settings クラスを提供（settings インスタンス経由で利用）:
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - デフォルト値: KABUSYS_ENV=development、LOG_LEVEL=INFO、KABU_API_BASE_URL 等
    - データベースパスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - env / log_level の検証、is_live / is_paper / is_dev のブールプロパティ

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - rate limiter（120 req/min 固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから自動で id_token を再取得して 1 回リトライ。
    - ページネーション対応（pagination_key）。
    - JSON パースエラー検出・明示的エラー。
  - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - save_* 系: save_daily_quotes, save_financial_statements, save_market_calendar を実装（DuckDB への冪等保存、ON CONFLICT DO UPDATE を使用）。
  - データ変換ユーティリティ: _to_float, _to_int、UTC fetched_at の付与。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集機能を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - HTTP/HTTPS スキーム以外を拒否して SSRF を抑制。
    - 受信サイズ上限（10 MB）によるメモリ DoS 対策。
    - トラッキングパラメータの除去（utm_* 等）、URL 正規化、記事 ID を SHA-256 で生成して冪等性を確保。
  - raw_news / news_symbols などへのバルク保存を想定した実装（バルクチャンク、トランザクション単位で保存）。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）等を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（欠損ハンドリングあり）。
    - calc_value: 最新の raw_financials と当日株価を組み合わせて per/roe を計算。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日欠損（休日等）に配慮したスキャン範囲を設定。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を利用）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（ties を平均ランクで処理）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとして扱うランク関数を提供。
  - zscore_normalize は kabusys.data.stats 経由で利用可能（research パッケージ経由でも再エクスポート）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research モジュールから生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定の数値カラムを Z スコア正規化（正規化後 ±3 でクリップ）。
    - features テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性を保証）。
    - ルックアヘッドバイアス対策: target_date 時点のデータのみを使用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネント毎の変換ロジック（シグモイド、PER の逆数近似 等）を実装。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数は検証・正規化して使用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY/SELL シグナル生成（SELL は stop_loss(-8%) と score_drop、将来的なトレーリング等は未実装として明記）。
    - signals テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性を保証）。
    - 生成数をログ出力して戻す。

- 公開 API の整理
  - strategy パッケージは build_features / generate_signals を __all__ で公開。
  - research パッケージは主要関数を __all__ で再エクスポート。

Security
--------
- news_collector は defusedxml と入力検証（スキーム、トラッキング除去、受信サイズ制限）を導入。
- jquants_client はトークンリフレッシュ時の無限再帰を防ぐ設計、429 の Retry-After を尊重する挙動を実装。

Notes / 互換性 / 前提
--------------------
- DuckDB のスキーマ（想定テーブル、列）:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news などが必要（各関数の docstring を参照）。
  - features / signals / raw_* の重複処理は ON CONFLICT / DELETE+INSERT により冪等性を保つ前提。
- 必須環境変数（実行前に設定が必要）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env の自動読込はプロジェクトルート検出に依存するため、パッケージ配布後や実行環境での挙動に注意。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自前で設定を注入してください。
- 一部の機能（execution 層や監視）についてはパッケージ構成はあるが詳細実装はスケルトン（未実装）である可能性があります。運用前に各 DB スキーマと実行フローを確認してください。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Acknowledgements / References
-----------------------------
- 各モジュールの docstring に設計方針・参照ドキュメント（StrategyModel.md, DataPlatform.md 等）の箇所が記載されています。詳細なアルゴリズム仕様や運用ルールは該当ドキュメントを参照してください。

（補足）開発者向けチェックリスト
- DuckDB スキーマ定義（CREATE TABLE）を用意して初期化すること。
- 必須環境変数を設定したうえで、J-Quants API の動作確認（get_id_token / fetch_*）を実施すること。
- ニュース収集は外部 HTTP アクセスを行うため、プロキシやネットワーク設定に注意すること。