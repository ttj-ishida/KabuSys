CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-21
-------------------

Added
- パッケージ初版を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 初期化
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml を基準に検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - インラインコメント処理（クォートなしはスペース/タブ直前の # をコメントと判断）。
  - Settings クラスを提供（settings インスタンス経由で利用）:
    - 必須環境変数を明示的に取得し未設定時は ValueError を送出。
    - 主な設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - システム環境: KABUSYS_ENV の検証（development, paper_trading, live）。
    - ログレベル検証: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- Data (J-Quants) クライアント
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限: 120 req / min（固定間隔スロットリングによる制御）。
    - 再試行ロジック: 最大 3 回、指数バックオフ、408/429/5xx に対するリトライ。
    - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応（pagination_key を使用）。
    - fetch_* 系関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（JSON レスポンス解析）。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 保存時に fetched_at を UTC ISO8601 (Z) 形式で記録。
    - 入力パースユーティリティ: _to_float / _to_int（空文字や変換失敗時に None を返す、_to_int は "1.0" を int に変換するが非整数小数は None）。
    - モジュールレベルの ID トークンキャッシュを持ち、ページネーション間で共有。

- News 收集モジュール
  - RSS フィードからニュースを取得して raw_news に保存するモジュールを追加（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を追加。
    - defusedxml を利用して XML 攻撃対策を実施。
    - URL 正規化機能:
      - スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリパラメータソート。
    - レスポンスサイズ制限（最大 10 MB）や SSRF 対策を想定した実装方針。
    - 挿入はチャンク化（デフォルトチャンク 1000）して DB へバルク挿入、冪等性を確保（ON CONFLICT DO NOTHING を想定）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を想定して冪等性を確保する設計方針。

- Research / Factor 計算機能
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - calc_momentum:
      - mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
      - データ不足時は None を返す仕様（ウィンドウ行数チェック）。
    - calc_volatility:
      - atr_20（20 日 ATR の単純平均）、atr_pct（相対 ATR）、avg_turnover（20 日平均売買代金）、volume_ratio（当日/20日平均）を計算。
      - true_range の NULL 伝播を明示的に制御。
    - calc_value:
      - raw_financials から最新財務を結合し PER / ROE を計算（EPS が 0 または欠損の場合 PER は None）。
  - 研究支援モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns:
      - 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを LEAD を用いて計算。
      - horizons の検証（1〜252 の整数）。
    - calc_ic:
      - factor_records と forward_records を code で結合し、スピアマンのランク相関（IC）を計算。サンプル不足（<3）では None を返す。
    - factor_summary:
      - count/mean/std/min/max/median を計算。
    - rank ユーティリティ:
      - 同順位は平均ランクを採用、丸め（round(..., 12)）による ties 対応。
  - 研究 API は DuckDB の prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。

- Strategy 層
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - build_features(conn, target_date):
      - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
      - 指定カラムを Z スコア正規化（data.stats.zscore_normalize を利用）し ±3 でクリップ。
      - features テーブルへ「日付単位の置換（削除→挿入）」をトランザクションで行い冪等性を確保。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
      - コンポーネントスコア:
        - momentum/value/volatility/liquidity/news（シグモイド変換や PER ベースの変換を実装）。
      - AI スコア未登録銘柄は中立（0.5）で補完。
      - 重みはデフォルト値を持ち、ユーザ指定の weights は検証（既知キーのみ採用、負値/NaN/Inf は無視）、合計が 1 でなければ再スケール。
      - Bear レジーム判定: ai_scores の regime_score 平均が負のとき（サンプル数 >= 3）BUY を抑制。
      - BUY シグナル閾値デフォルト 0.60、SELL シグナルは stop_loss（-8%）やスコア低下を判定。
      - positions / prices_daily を参照してエグジット判定を行い、SELL 対象は BUY から除外。
      - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。

- パッケージエクスポート
  - kabusys.__init__ にて __all__ = ["data", "strategy", "execution", "monitoring"] を公開。
  - strategy パッケージのトップレベルに build_features / generate_signals をエクスポート。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 外部データ（RSS/XML）解析に defusedxml を使用する方針を明示。
- J-Quants クライアントは認証情報（トークン）を扱うため、HTTP エラー時の取り扱いとリフレッシュ制御を実装。  

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定時は Settings のプロパティアクセスで ValueError を送出します。
- 自動 .env 読み込みを一時的に無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテストで使用）。
- DuckDB 側のスキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）に依存します。初回導入時はスキーマの準備が必要です。

今後の予定（例）
- Execution 層と監視（monitoring）の実装（発注 API 連携、Slack 通知など）。
- News の銘柄紐付け（news_symbols）ロジックの実装。
- トレーリングストップや時間決済などの追加エグジット条件の実装。

----- 

脚注:
- 本 CHANGELOG はソースコードの実装内容と docstring から推測して作成しています。実際のリリースノートやバージョン管理履歴に基づく正確な履歴は別途ご用意ください。