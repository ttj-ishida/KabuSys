Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

すべての公開リリースはセマンティックバージョニングに従います。なお、この CHANGELOG はソースコードから推測して作成しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 全体
  - 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージの公開 API を整理（kabusys.__all__ に data/strategy/execution/monitoring を設定）。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込みの優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env のパーサーを強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント無視に対応。
    - クォートなしの値では '#' の前のスペース／タブでコメントを判定。
  - _load_env_file に override/protected オプションを実装（OS 環境変数を保護して上書き制御）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に:
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）。
    - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。
    - KABUSYS_ENV の有効値チェック (development, paper_trading, live) と LOG_LEVEL の検証。

- Data / J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API との通信クライアントを実装。
    - 固定間隔スロットリングによるレート制限 (_RateLimiter, デフォルト 120 req/min)。
    - 再試行（指数バックオフ）実装: ネットワークエラーおよび 408/429/5xx を対象に最大 3 回リトライ。
    - 401 応答時にはトークンを自動リフレッシュして 1 回だけリトライ（再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
    - JSON デコードエラーや最大リトライ失敗時の明確な例外処理。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装（ページネーション対応）。
    - 取得ログ（取得件数）を出力。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。ON CONFLICT (UPSERT) による重複排除。
    - PK 欠損行のスキップや挿入件数ログ出力を実装。
    - fetched_at を UTC ISO 形式で記録。
  - ユーティリティ変換関数: _to_float, _to_int（不正値は None を返す、安全な変換）。

- Data / ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存するモジュールを実装（デフォルトで Yahoo Finance のビジネス RSS を登録）。
  - セキュリティと堅牢性:
    - defusedxml を利用して XML 関連の攻撃（XML bomb 等）を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を抑制。
    - URL 正規化で utm_* 等のトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリのソートを実施。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を保証。
  - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）により SQL 長・パラメータ数を制御。
  - raw_news への保存は ON CONFLICT DO NOTHING を想定し、news_symbols との紐付けを想定。

- Research（kabusys.research）および Factor 計算
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離率）を計算。MA200 はウィンドウ内データが 200 行未満なら None を返す。
    - calc_volatility: ATR（20 日）および相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。EPS が 0 や欠損の場合は PER を None に。
    - 各関数は DuckDB の prices_daily / raw_financials のみを参照し、外部 API への依存を持たない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: デフォルト horizon = [1,5,21]（翌日・翌週・翌月）。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効サンプルが 3 未満なら None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクで処理（丸めによる ties 対応）。
  - research パッケージの公開 API を整理（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- Strategy（kabusys.strategy）
  - feature_engineering.build_features:
    - research の生ファクター（calc_momentum, calc_volatility, calc_value）を取得しマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを zscore_normalize で正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT をトランザクションで行い原子性を保証）。
    - 冪等性を維持（同日付のデータは置換）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー指定 weights は検証・補完・リスケールされる（不正値は無視）。
    - final_score を算出し、デフォルト BUY 閾値は 0.60。
    - Bear レジーム判定: ai_scores の regime_score 平均が負であれば BUY を抑制（サンプル数不足時は Bear と判定しない）。
    - SELL（エグジット）判定:
      - ストップロス: 終値と平均取得単価の差が -8% 以下で即時 SELL。
      - スコア低下: final_score が閾値未満の場合 SELL。
      - SELL ロジックは保有ポジション（positions）と最新価格を参照し、価格欠損時は判定をスキップ。
      - トレーリングストップ等の未実装条件はコメントで明示。
    - signals テーブルへ日付単位の置換（冪等、トランザクションで実施）。
    - 実行結果をログに出力（BUY/SELL/total）。

Changed
- なし（初期リリースのため）

Fixed
- なし（初期リリースのため）

Security
- ニュース収集で defusedxml を使用、受信サイズ制限、URL 正規化などを取り入れ SSRF / XML 攻撃 / メモリ DoS の抑制を図る設計になっていることを明記。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。未設定時は Settings のプロパティ参照で ValueError が発生する。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db（いずれも環境変数で上書き可能）。
- 設計上の制約:
  - ルックアヘッドバイアス防止のため、全ての日付基準処理は target_date 時点での入手可能データのみを使う実装方針。
  - DuckDB をデータレイヤーに用い、外部 API 呼び出しや発注 API への依存を分離している。
- ログレベルと環境検証:
  - KABUSYS_ENV, LOG_LEVEL の許容値チェックを行い、不正値は ValueError を投げる。

今後の予定（推測）
- execution 層（発注ロジック）や monitoring の実装・統合。
- ニュースと銘柄紐付け（news_symbols）の強化、SSRF チェックの追加実装。
- トレーリングストップや時間決済等の SELL 条件の実装。

----- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートと差異がある場合は、該当する正式ドキュメントに合わせて編集してください。