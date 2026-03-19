# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

現在のリリース履歴は以下の通りです。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース: kabusys - 日本株自動売買システムのコアライブラリを追加。
  - パッケージメタ:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパースロジック強化:
    - コメント行・export 形式のサポート、シングル/ダブルクォートとエスケープ処理、インラインコメント処理。
  - settings オブジェクトにより型付きプロパティで設定値を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH 等にデフォルト値を持つプロパティ。
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ有効）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API との通信ユーティリティを実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx 等を対象）。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
    - JSON デコードのエラーハンドリング。
  - 高レベル API 関数:
    - get_id_token: リフレッシュトークンから ID トークンを取得（POST）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応でデータ取得。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - 入出力変換ユーティリティ: _to_float / _to_int（型安全な変換、変換失敗時は None）。
  - 取得時の fetched_at は UTC ISO8601 で記録（Look-ahead バイアスの記録に対応）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能（記事ID は正規化 URL の SHA-256 ハッシュを使用）。
  - セキュリティ考慮:
    - defusedxml を使用して XML 攻撃を防止。
    - URL 正規化時にトラッキングパラメータ（utm_*, fbclid 等）を除去。
    - 受信バイト数上限（MAX_RESPONSE_BYTES=10MB）を導入してメモリ DoS を軽減。
    - HTTP/HTTPS スキーム以外や不正な URL を排除する実装方針（SSRF 対策の設計）。
  - バルク INSERT のチャンク処理とトランザクション集約で効率的に DB に保存。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを含む。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR の true_range は high/low/prev_close が NULL の場合は NULL として正確に扱う）。
    - calc_value: target_date 以前の最新 raw_financials と当日株価を用いて per / roe を計算。
    - SQL とウィンドウ関数を併用して効率的に DuckDB 上で計算。
    - 営業日（連続レコード数）ベースのホライズン取り扱い、データ不足時は None を返す。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。サンプル不足（<3）や分散が 0 の場合は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（round(..., 12) で ties の誤検知を低減）。
  - research パッケージの __init__ で主要関数をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュールから得た生ファクター（momentum/volatility/value）をマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 数値ファクターを zscore_normalize（kabusys.data.stats から提供）で正規化し ±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入による原子性保証、冪等処理）。
    - 価格取得は target_date 以前の最新価格を参照して休場日考慮。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores（存在する場合）を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - スコア変換: Z スコアをシグモイド関数で [0,1] に変換。欠損コンポーネントは中立値 0.5 で補完。
    - 最終スコア (final_score) は重み付き合算。デフォルト重みは StrategyModel.md に基づく。
    - 重みの検証・正規化を行い、不正な入力は警告して無視。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合）では BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60、SELL シグナルはストップロス（-8%）やスコア低下で判定。
    - 保有ポジションの確認は positions テーブルの latest ポジションを参照。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）。SELL 優先ポリシーにより SELL 銘柄は BUY から除外。
    - 返り値は当日作成したシグナル数（BUY+SELL の合計）。
  - 実装上の注意点として、いくつかの追加エグジット条件（トレーリングストップ、時間決済）は positions テーブルの追加情報が必要で未実装である旨を明記。

- strategy パッケージの __init__ で build_features と generate_signals をエクスポート。

### Security
- news_collector で defusedxml を採用し XML 関連の攻撃を低減。
- RSS URL 正規化・トラッキングパラメータ除去により誤った ID の挿入/重複や追跡パラメータによるノイズを抑制。
- J-Quants クライアントでネットワークエラーや HTTP エラーに対する堅牢なハンドリング（再試行・バックオフ）を実装。

### Documentation / Design notes
- 各モジュール内に設計方針・処理フロー・SQL の前提（参照するテーブル名）などを詳細にコメントとして記載。  
- 多くの DB 操作は DuckDB を前提としており、期待するテーブル:
  - raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news など（関数内コメントや SQL 参照により確認可能）。
- 冪等性: raw データ保存 / features / signals の日付単位置換等、実運用での再実行を想定した設計。

### Breaking Changes
- 本リリースは初版のため互換性情報なし。

### Requirements / Notes for users
- DuckDB 接続を渡して利用する API が多い（直接的な DB スキーマ準備が必要）。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動読み込み機能を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- news_collector の処理はネットワークアクセスと XML パースを伴うため、defusedxml の利用が必須。

---

今後のリリースでは、以下が検討対象です:
- execution 層（kabu ステーション等）との実際の注文執行連携実装。
- positions テーブルの拡張（peak_price / entry_date など）に伴うトレーリングストップや時間決済の実装。
- テストカバレッジと CI の整備、ドキュメントの整備（Usage / DB schema / StrategyModel.md の公開）。