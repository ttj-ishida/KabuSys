KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。
なお本リリース情報はソースコードから推測して作成しています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-03-19
--------------------
Added
- パッケージ初期リリース。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開モジュール: data, strategy, execution, monitoring を __all__ で公開。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を自動読み込み（OS 環境変数 > .env.local > .env、プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - コメント / 空行 / export KEY=val 形式対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、トラッキングを考慮したパース。
  - 読み込み時の保護機構: 既に存在する OS 環境変数は protected として上書き回避。override オプション対応。
  - 必須変数チェック用 _require() と Settings クラスを提供。以下のプロパティを含む:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- データ収集クライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx に対するリトライ。429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン処理:
    - get_id_token(refresh_token) によるリフレッシュ。
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - HTTP ユーティリティ _request() による JSON 応答処理とエラーハンドリング。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials テーブルへ保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar テーブルへ保存（ON CONFLICT DO UPDATE）
  - ユーティリティ変換関数: _to_float, _to_int（安全な変換ロジック）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事保存の基礎実装。
  - セキュリティ・堅牢化:
    - defusedxml による XML パースで XML Bomb 等を防止。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10 MB）を導入してメモリ DoS を緩和。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）の除去、クエリソート、フラグメント除去。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - HTTP/HTTPS スキーム以外の URL を拒否するよう設計（SSRF 緩和）。
  - DB へのバルク INSERT はチャンク化（_INSERT_CHUNK_SIZE）してオーバーヘッドを抑制。news_symbols との紐付け想定。
  - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS をサンプル定義。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - ファクター計算群（src/kabusys/research/factor_research.py）:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、atr_pct（atr_20 / close）、avg_turnover（20 日平均売買代金）、volume_ratio（当日 / 20 日平均）。
      - true_range の NULL 伝播を考慮した実装（high/low/prev_close のいずれか NULL なら true_range NULL）。
    - calc_value: raw_financials から最新財務を参照して PER（close / EPS）・ROE を計算。EPS が 0 または欠損のときは None。
    - DuckDB の prices_daily / raw_financials のみ参照する設計（本番 API にアクセスしない）。
  - 特徴量探索ツール（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。horizons の検証（1〜252）を実施。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。データが 3 件未満なら None。
    - rank: 同順位は平均ランクで処理（round(v, 12) により浮動小数誤差の ties を防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージの __init__ で主要関数をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - 正規化: 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を zscore_normalize で標準化後 ±3 にクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT）し原子性を確保（トランザクション）。
    - look-ahead bias を防ぐため target_date 時点のデータのみを使用。execution 層への依存無し。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出。
    - コンポーネント変換: Z スコア → シグモイドで [0,1] に変換、欠損は中立値 0.5 で補完。
    - デフォルト重みを備え、ユーザ指定 weights は検証後にマージ・リスケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で且つサンプル >= 3 の場合に BUY を抑制。
    - BUY シグナル閾値: デフォルト 0.60。STOP-LOSS: -8%（優先判定）。
    - 保有ポジションのエグジット判定（positions テーブル参照）。価格欠損時は判定スキップか警告。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - 戦略仕様（StrategyModel.md セクション 4〜5）に基づく実装方針を明示。

- strategy パッケージの __init__ で build_features / generate_signals をエクスポート。

Security
- news_collector に defusedxml を使用した安全な XML パースを導入。
- RSS の受信サイズ制限、URL 正規化・トラッキング除去、スキーム制限等で外部からの攻撃リスクを低減。

Notes / Design decisions
- DuckDB をローカル分析ストアとして利用する前提の実装（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等のテーブルを前提）。
- ルックアヘッドバイアス対策: 多くの処理で target_date 時点の情報のみを参照し、fetched_at を記録することで「データをいつ知り得たか」をトレース可能に設計。
- 冪等性: 外部データ保存（raw_* / market_calendar / features / signals）では ON CONFLICT / 日付単位の DELETE→INSERT パターンで冪等操作を実現。
- 外部依存は最小化（標準ライブラリ中心、DuckDB と defusedxml のみ利用想定）。research モジュールは pandas 等に依存しない実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版で既述の通りニュースパーサに対する XLM 攻撃・SSRF・DoS 対策を反映。

Acknowledgements
- この CHANGELOG はソースコードから推測して作成したものであり、実際の変更履歴とは異なる可能性があります。必要に応じて差分・運用上の注意点を追記してください。