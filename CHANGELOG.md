CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。 (https://semver.org/)

Unreleased
----------

（現在のスナップショットに対する未リリース変更はここに記載します。）
※本CHANGELOGはコードベースから推測して作成しています。実際のリリース履歴と差異がある可能性があります。

0.1.0 - 2026-03-21
------------------

Added
- パッケージ初期実装:
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開APIとして data/strategy/execution/monitoring をエクスポート。
- 環境設定・自動.env読み込み (kabusys.config):
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動読み込みを無効化可能。
  - .env パーサー実装（コメント、export プレフィックス、シングル/ダブルクォートとエスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）を扱う。必須環境変数の検証を行う。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等。
  - 有効値チェック: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- データ取得クライアント (kabusys.data.jquants_client):
  - J-Quants API クライアントを実装。fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar をサポート（ページネーション対応）。
  - 認証: refresh token から id token を取得する get_id_token を実装。モジュールレベルのトークンキャッシュを保持。
  - レート制限: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 再試行ロジック: 指数バックオフによる最大3回リトライ（408, 429, 5xx を対象）、429 の Retry-After を尊重。
  - 401 受信時はトークンを自動リフレッシュして1回リトライ（無限再帰防止）。
  - DuckDB への保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar。ON CONFLICT DO UPDATE による冪等保存、PK 欄欠損行のスキップとログ警告。
  - 入出力変換ユーティリティ: _to_float, _to_int（堅牢な型変換ロジック）。
- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィードからの記事収集設計を実装（URL 正規化・トラッキングパラメータ除去、記事ID の SHA-256 ベース生成、XML の安全パーシングに defusedxml を使用）。
  - SSRF・XML Bomb 等の脅威に配慮した設計（受信サイズ上限、スキーム検査等を想定）。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING）と銘柄紐付け想定。
- リサーチ / ファクター計算 (kabusys.research):
  - ファクター計算群を実装（factor_research: calc_momentum, calc_volatility, calc_value）。
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio（20日窓）。
    - バリュー: per, roe（raw_financials から最新財務データを取得）。
  - 特徴量探索ツール (feature_exploration):
    - 将来リターン計算: calc_forward_returns（複数ホライズン、LEAD を利用した1クエリ取得）。
    - IC（スピアマン）計算: calc_ic（rank 確定・同順位は平均ランクで処理、サンプル閾値チェック）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - ランク付けユーティリティ: rank（丸め誤差対策で round(v, 12) を使用）。
  - z-score 正規化ユーティリティの利用（kabusys.data.stats 経由で提供を想定）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering):
  - build_features 実装:
    - research の生ファクター(calc_momentum/calc_volatility/calc_value) を結合。
    - ユニバースフィルタ（最低株価300円、20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化して ±3 にクリップ。
    - DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）することで冪等性と原子性を担保。
    - 価格欠損や数値不正に対する防御的処理あり。
- シグナル生成 (kabusys.strategy.signal_generator):
  - generate_signals 実装:
    - features, ai_scores, positions を参照して BUY/SELL シグナルを生成し、signals テーブルへ日付単位で置換保存。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（AI スコア）。各コンポーネントは欠損時中立値 0.5 で補完。
    - final_score は重み付け和で計算。weights はデフォルト値からユーザ値をマージし、合計が1でなければ再スケール。無効な重みはスキップして警告。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
    - SELL 条件実装（ストップロス: -8% / スコア未満）。トレーリングストップ・長期保持時間決済は未実装（コメントで明記）。
    - signals テーブルへのバルク挿入はトランザクションで原子性を確保。ROLLBACK 失敗時は警告ログ出力。
- パッケージ公開インターフェース:
  - kabusys.strategy: build_features, generate_signals を __all__ で公開。
  - kabusys.research: 主要関数を __all__ で公開。

Security
- ニュース収集で defusedxml を用いた安全な XML パースを採用（XML Bomb 対策）。
- RSS URL 正規化・トラッキングパラメータ除去、最大受信サイズ（10MB）を設けるなど DoS/追跡対策を設計に含む。
- J-Quants クライアントは Authorization トークン処理に注意（キャッシュ・自動リフレッシュ・無限再帰防止）。
- HTTP エラーやネットワーク障害時の再試行はログに記録され、再試行ポリシーを明確化。

Known limitations / Notes
- execution パッケージは空の __init__.py のみで、発注ロジック（実際の注文送信）は未実装（将来的な実装を想定）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。
- news_collector の実装は設計（正規化関数など）までで、RSS フェッチ本体や DB 保存周りの完全実装はコードの続きに依存（与えられたソースから推測）。
- DuckDB テーブル名（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等）を前提としているため、スキーマ準備が必要。
- 一部ユーティリティ（kabusys.data.stats など）は本CHANGELOGの対象外の別ファイルに実装されている想定。

Developer / Migration notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意の便利な環境変数:
  - KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
- .env 自動読込みはプロジェクトルート判定に依存するため、配布後に CWD を起点に動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト環境で明示的に環境を注入すること。

Acknowledgements / References
- 実装は StrategyModel.md / DataPlatform.md 等の設計仕様を参照している旨の注記がコード内にあり、これらのドキュメントに従ったアルゴリズム設計になっている。

（以上）