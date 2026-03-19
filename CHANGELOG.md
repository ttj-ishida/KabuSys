Changelog
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初期リリース。主要サブパッケージと機能を追加。
  - kabusys パッケージ公開情報
    - バージョン: 0.1.0
    - __all__ に data / strategy / execution / monitoring を定義。

- 環境設定 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD非依存）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装（コメント/export/シングル/ダブルクォート/エスケープ対応）。
  - Settings クラスにアプリ設定を集約（必須設定チェックと型変換）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - デフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時にリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
    - DuckDB への冪等保存関数:
      - save_daily_quotes(), save_financial_statements(), save_market_calendar()
      - INSERT ... ON CONFLICT DO UPDATE による重複排除。
    - データ変換ユーティリティ: _to_float(), _to_int()。
    - トークンキャッシュ（モジュールレベル）でページネーション間のトークン共有。
    - 取得時の fetched_at を UTC ISO8601 で記録（Look-ahead バイアス対策）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news へ保存する基盤を追加。
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - HTTP 応答サイズ制限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
    - SQL バルク挿入のチャンク分割（_INSERT_CHUNK_SIZE）で DB オーバーヘッドを制御。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - NewsArticle TypedDict による型定義。

- 研究用ファクター計算 (kabusys.research and kabusys.research.factor_research)
  - ファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - calc_momentum(): mom_1m/mom_3m/mom_6m、ma200_dev（MA200 のデータ不足時は None）。
    - calc_volatility(): atr_20, atr_pct, avg_turnover, volume_ratio（20 日ウィンドウ）。
    - calc_value(): per, roe（target_date 以前の最新財務データを使用）。
  - 研究ユーティリティ群（kabusys.research）
    - zscore_normalize を外部参照で利用可能に公開（kabusys.data.stats 由来）。
    - calc_forward_returns(): 任意ホライズンの将来リターンを一括取得（複数ホライズン対応・安全チェック）。
    - calc_ic(): ファクター値と将来リターンの Spearman（ランク相関）を計算（有効サンプル3未満で None）。
    - factor_summary(): count/mean/std/min/max/median を算出する統計サマリー。
    - rank(): 同順位は平均ランクを割り当てるランク関数（浮動小数丸めで ties 対応）。
  - 実装方針: DuckDB SQL を中心に実装、外部ライブラリに依存しない（pandas 不使用）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装。
    - research の calc_* 関数から生ファクター取得、ユニバースフィルタ（価格 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化（zscore_normalize）→ ±3 でクリップ → features テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - 不要なルックアヘッドを防ぐため target_date 時点のデータのみ使用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装。
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付き合算（デフォルト重みを定義）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。サンプル閾値あり）。
    - Bear 相場では BUY シグナルを抑制。
    - BUY: final_score >= threshold、SELL: ストップロス（-8%）またはスコア低下。
    - 保有銘柄（positions テーブル参照）に対するエグジット判定を実装。
    - signals テーブルへ日付単位置換で保存（トランザクション + バルク挿入）。
    - 重み指定は妥当性検査と正規化を行い、不正値は無視してフォールバック。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector: defusedxml の採用、受信サイズ制限、HTTP スキーム/SSRF 対策など複数の安全対策を導入。
- jquants_client: トークン自動リフレッシュ時の無限再帰防止設計（allow_refresh フラグ）、HTTP エラー毎の適切なハンドリングとリトライ制御。

Notes / Design decisions
- ルックアヘッドバイアス対策:
  - すべての戦略/研究関数は target_date 時点のデータのみを使用する設計。
  - 外部データ取得時に fetched_at を UTC で記録。
- 冪等性:
  - DB への保存（raw_* / market_calendar / features / signals 等）は日付単位削除→挿入、あるいは ON CONFLICT を使い冪等化。
- DuckDB を主要なデータレイヤとして使用。外部分析ライブラリに依存しない実装を優先。

Known issues / Roadmap
- signal_generator の未実装（将来追加予定）機能:
  - トレーリングストップ（positions の peak_price が必要）
  - 時間決済（保有 60 営業日超過）
  これらはコード中に TODO が記されており、positions テーブルに追加カラムが必要。
- feature_engineering:
  - ma200_dev は 200 行未満で None となるため、短期上場銘柄では欠損が発生する可能性あり。
- モジュールはロギングで多くの警告/情報を出力するため、本番運用時は LOG_LEVEL の適切な設定を推奨。
- テスト、CI、ドキュメント（ユーザー向け手順・テーブル定義・StrategyModel.md 等の参照資料）は別途整備予定。

以上。