# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（初期リリース）から推測した機能追加・設計上の変更点をまとめたものです。

全般:
- SemVer を想定したバージョニングを使用（パッケージ版では __version__ = "0.1.0"）。
- パッケージの主要サブモジュールを公開（data, strategy, execution, monitoring）。

Unreleased
- （現時点なし）

[0.1.0] - 2026-03-20
Added
- パッケージ基盤
  - パッケージ初期化を提供（kabusys パッケージ、__version__ と __all__ を設定）。
  - execution パッケージの雛形を追加（将来的な発注/実行層の基盤）。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。
  - プロジェクトルート自動検出: __file__ の親ディレクトリを上位にたどり .git または pyproject.toml を検出してプロジェクトルートを特定。
  - .env パーサを実装:
    - 空行・コメント行（#）を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポートし、対応する閉じクォートまでを読み取る（インラインコメントは無視）。
    - クォート無し値では " #" の直前が空白またはタブの場合のみコメントと認識。
  - .env 読み込みの優先順位を実装: OS 環境変数 > .env.local > .env（.env.local は上書き、.env は未設定時にセット）。
  - OS 側既存の環境変数を保護する protected キーサポート。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テストや CI のため）。
  - Settings クラスを提供し、各種必須設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や DB パス（DUCKDB_PATH, SQLITE_PATH）、環境（KABUSYS_ENV）・ログレベル検証（LOG_LEVEL）をラップ。値検証（許容値チェック、未設定時に ValueError）を実装。
  - 環境判定プロパティ: is_live / is_paper / is_dev。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を保つ固定間隔スロットリング RateLimiter を導入。
  - HTTP リクエスト共通処理で以下を実装:
    - ページネーション対応。
    - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象とする。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
    - JSON デコードエラー時は明示的に例外化。
  - 認証: refresh_token から id_token を取得する get_id_token を実装（設定値からの取得に対応）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を考慮して ON CONFLICT を使用）:
    - save_daily_quotes -> raw_prices テーブルへ保存（fetched_at: UTC ISO8601 を記録）
    - save_financial_statements -> raw_financials テーブルへ保存
    - save_market_calendar -> market_calendar テーブルへ保存
  - ユーティリティ関数: _to_float / _to_int（安全な変換、空値や不正値は None を返す）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する処理を追加。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パースで XML Bomb 等への対策。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）を導入してメモリDoSを緩和。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント除去、クエリソート）を実装。
    - HTTP/HTTPS スキーム以外の URL を拒否する方針（SSRF 対策）。
  - 記事 ID の生成方針（ドキュメント）: URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）を使用して冪等性を保証する方針。
  - バルク INSERT はチャンク（_INSERT_CHUNK_SIZE = 1000）で行い、トランザクション内にまとめて保存。ON CONFLICT DO NOTHING を用いる想定。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。

- 研究・ファクター計算（kabusys.research）
  - factor_research: prices_daily / raw_financials を参照して定量ファクターを計算する関数群を提供。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離率）を計算。必要な窓サイズやスキャン範囲を考慮した SQL を使用。
    - calc_volatility: ATR（20 日平均 true range）、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算。true_range 計算は high/low/prev_close が揃っている場合のみ算出してカウントを厳密に管理。
    - calc_value: raw_financials の最新報告を銘柄ごとに結合し PER（EPS が 0 または欠損なら None）と ROE を算出。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）後までの将来リターンを計算（営業日ベース）。ホライズン引数検証あり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。NULL/欠損を除外し、有効サンプル数が 3 未満の場合は None を返す。ties（同順位）は平均ランク処理を採用。
    - rank: 浮動小数点の丸め（round(..., 12)）を行って同値検出を安定させるランク関数を実装。
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を計算（None を除外）。

  - research パッケージは外部ライブラリに依存しない実装方針（標準ライブラリ + DuckDB SQL を活用）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタを適用（閾値: 最低株価 300 円、20 日平均売買代金 5 億円）。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位の置換（DELETE + INSERT）をトランザクションで行い原子性を保証。挿入行数を返す。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores（存在しない場合は補完）を読み込み、各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - 各コンポーネントでの欠損は中立値 0.5 で補完。
    - 重み（weights）はデフォルト値でフォールバック。未知キー・非数値・負値等は無視し既知キーのみ受け付け、合計が 1.0 でなければ再スケールする。
    - スコア変換にシグモイド関数を利用（Z スコア → [0,1]）。オーバーフローは安全に処理。
    - Bear レジーム判定: ai_scores の regime_score の平均が負であり、サンプル数が閾値以上（_BEAR_MIN_SAMPLES = 3）の場合に Bear と判定し BUY を抑制。
    - BUY は threshold（デフォルト 0.60）を超えた銘柄に付与。SELL はエグジット判定（ストップロス -8% が最優先、次にスコア低下）で生成。SELL 対象は BUY から除外する優先ポリシーを採用。
    - 保有ポジションの最新情報は positions テーブルから参照。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへ日付単位の置換（DELETE + INSERT）をトランザクションで行い原子性を保証。生成総数を返す。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- ニュース収集で defusedxml を利用、HTTP/HTTPS スキーム検査、受信サイズ制限などを導入。
- J-Quants クライアントにおいて認証トークンの安全な自動リフレッシュと再試行戦略を実装。

Notes / Known limitations
- 実行層（execution）はまだ実装が薄く、実際の発注 API との結合は将来対応予定。strategy 層は発注 API に直接依存しない設計。
- 一部仕様（トレーリングストップ、時間決済、ポジションの peak_price / entry_date）については positions テーブル側の情報が必要で、未実装の機能がドキュメント内に記載されています。
- news_collector の記事 ID 生成や記事→銘柄紐付け処理は設計方針が記載されているが、実装は RSS パース部分の実装状況に依存します（コードはセキュリティ対策を備えた実装を意図しています）。
- zscore_normalize は kabusys.data.stats 側の実装を利用（本差分には含まれていないが呼び出しがあるため依存関係に注意）。

参考
- 各モジュールの docstring に主要な設計方針・処理フロー・注意点が記載されています。運用・拡張時はそれらを参照してください。