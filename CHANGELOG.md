CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このプロジェクトはセマンティックバージョニングを使用します。

注意: コードベースから推測して作成した初回リリースの変更履歴です。

[Unreleased]
------------

- (なし)

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys (トップレベル)
  - サブパッケージ: data, research, strategy, execution, monitoring（execution は空の初期化ファイルのみ含む）
- 環境設定（kabusys.config）:
  - .env ファイルおよび環境変数からの設定自動読み込みを実装。
  - .git または pyproject.toml を基準にプロジェクトルートを探索して .env / .env.local を読み込む（CWD 非依存）。
  - .env の詳細なパーサ実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどに対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）や各種既定値（KABUSYS_ENV, LOG_LEVEL, DB パス）を取得。KABUSYS_ENV / LOG_LEVEL の検証ロジックを含む（不正値は ValueError）。
- データ収集（kabusys.data.jquants_client）:
  - J-Quants API クライアントを実装。fetch_* 系関数でページネーション対応のデータ取得を行う:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象。429 の Retry-After を尊重。
  - 401 時はトークンを自動リフレッシュして 1 回リトライ（トークン取得時の無限再帰を防止）。
  - DuckDB への保存用ユーティリティ:
    - save_daily_quotes: raw_prices テーブルへ冪等保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials テーブルへ冪等保存。
    - save_market_calendar: market_calendar テーブルへ冪等保存。
  - データ変換ユーティリティ (_to_float / _to_int) による堅牢な型変換と PK 欠損行スキップ。
  - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス回避のためのメタ情報）。
- ニュース収集（kabusys.data.news_collector）:
  - RSS フィード収集基盤を実装（デフォルトで Yahoo Finance のビジネス RSS を定義）。
  - XML パースに defusedxml を使用して XML Bomb 等から防御。
  - 受信サイズ上限（MAX_RESPONSE_BYTES＝10MB）を導入してメモリ DoS を軽減。
  - URL 正規化: トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）により生成し冪等性を確保。
  - SSRF 対策として HTTP/HTTPS スキームの厳格検査や IP アドレスチェックなど（実装方針）。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING）や news_symbols との紐付けを想定した設計。
  - バルク INSERT のチャンク化により SQL 長やパラメータ数の上限に配慮。
- リサーチ（kabusys.research）:
  - ファクター計算ユーティリティの公開:
    - calc_momentum（モメンタム: 1/3/6M リターン、200日 MA 乖離）
    - calc_volatility（ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（PER、ROE の算出。raw_financials から最終財務データを取得）
  - feature_exploration: 研究用ユーティリティを実装:
    - calc_forward_returns（将来リターン: 任意ホライズン、デフォルト [1,5,21]）
    - calc_ic（Spearman のランク相関に基づく IC 計算）
    - factor_summary（各ファクター列の count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理。浮動小数の丸めで ties 検出を安定化）
  - 外部ライブラリに依存せず、DuckDB の prices_daily テーブルのみ参照する方針。
- 特徴量構築（kabusys.strategy.feature_engineering）:
  - research の生ファクターを統合して features テーブルへ書き込む build_features を実装。
  - ユニバースフィルタ: 最低株価（300 円）および 20 日平均売買代金 >= 5 億円。
  - 正規化: 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
  - 日付単位の置換（トランザクション＋バルク挿入）で冪等性と原子性を確保。
  - 休場日・当日欠損を考慮して target_date 以前の最新価格を参照。
- シグナル生成（kabusys.strategy.signal_generator）:
  - features と ai_scores を組み合わせて final_score を算出し BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア:
    - momentum（複数 momentum 指標をシグモイド後平均）
    - value（PER を 20 を尺度に変換）
    - volatility（ATR の Z スコアを反転してシグモイド）
    - liquidity（出来高比率をシグモイド）
    - news（AI スコアをシグモイド。未登録は中立）
  - 重みのマージと再スケーリングロジック（ユーザー指定 weights を検証・補完）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負で且つサンプル数閾値を満たす場合）により BUY を抑制。
  - SELL 条件実装（ストップロス -8%、スコア低下）。トレーリングストップや保有日数による時限決済は未実装（将来対応予定）。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性・原子性を確保。
- ロギング: 各モジュールで適切な INFO/WARNING/DEBUG ログ出力を追加し動作追跡を容易に。

Security
- defusedxml の採用、RSS パース時の受信サイズ制限、URL 正規化・スキーム検査等により潜在的なセキュリティリスク（XML Bomb、SSRF、メモリ DoS）への対策を実装。
- 環境変数や API トークン管理に関する注意喚起（必須変数チェック、トークン自動リフレッシュの取り扱い）を文書化。

Performance & Reliability
- API クライアントはレート制御とリトライ（指数バックオフ）を行い、J-Quants のレート制限に準拠。
- DuckDB への書き込みはバルク挿入と ON CONFLICT を利用して効率的かつ冪等に。
- 大規模 RSS 取り込みに対してはチャンク化で SQL およびメモリ負荷を削減。

Known limitations / TODO
- execution 層（発注処理）の実装は含まれていない（placeholder の __init__ のみ）。
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の拡張が必要。
- news_symbols（ニュースと銘柄紐付け）の完全な実装・名前解決ロジックは今後の課題。
- 外部依存低減のため research モジュールは pandas 等を使わず実装しているが、データ処理量が増えるとパフォーマンス調整が必要になる可能性あり。

開発者向けメモ
- パッケージの __all__ は ["data", "strategy", "execution", "monitoring"] を公開。
- settings オブジェクトを利用して設定にアクセスすること（例: from kabusys.config import settings）。
- DuckDB コネクションを各種関数に渡す設計。関数は副作用を DB に対して行う（features / signals などの書き込み）。

License
- （ソースにライセンス表記がないためここには記載していません。必要に応じて LICENSE を追加してください。）

--- 

（以上）