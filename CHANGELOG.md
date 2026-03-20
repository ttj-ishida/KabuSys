CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース: kabusys v0.1.0 を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、公開 API として data, strategy, execution, monitoring をエクスポート。

  - 環境設定・読み込み機能（src/kabusys/config.py）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式やクォート／エスケープ、インラインコメント処理を考慮した .env パーサを実装（_parse_env_line）。
    - .env と .env.local の読み込み順序・上書きルール（OS 環境変数保護）を実装。
    - 必須環境変数取得用のヘルパー _require と Settings クラスを提供。J-Quants / kabu / Slack / DB パスなどのプロパティ、環境値検証（KABUSYS_ENV / LOG_LEVEL）とユーティリティプロパティ（is_live / is_paper / is_dev）を実装。

  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限を固定間隔スロットリング（120 req/min）で守る RateLimiter を導入。
    - HTTP リクエスト共通処理 _request を実装（JSON デコード検証、リトライ（指数バックオフ）、408/429/5xx リトライ、429 の Retry-After 優先処理）。
    - 401 Unauthorized を検知した場合の ID トークン自動リフレッシュ（1 回のみ）と安全な再試行を実装。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務）
      - fetch_market_calendar（取引カレンダー）
    - DuckDB へ冪等に保存する関数:
      - save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT を用いた更新で重複排除）
    - データ型変換ヘルパー _to_float / _to_int（堅牢な変換ルールを実装）。
    - 取得時刻 (fetched_at) を UTC で記録（Look-ahead バイアス対策）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからのニュース収集フローを実装（デフォルトソースに Yahoo Finance のカテゴリ RSS を設定）。
    - XML パースに defusedxml を使用して XML-Bomb 等対策。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、HTTP スキーム検証等による SSRF/DoS 緩和方針を導入。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート）を実装（_normalize_url）。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成する方針を採用し冪等性を担保。
    - raw_news / news_symbols 等へのバルク保存を想定（チャンク化、トランザクション最適化）。

  - 研究 / ファクター計算モジュール（src/kabusys/research/*）
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。ウィンドウ/スキャン範囲のバッファを考慮。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を明示的に制御。
      - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算。最新財務レコードを取得する SQL ロジックを実装。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する高速 SQL 実装。
      - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算する実装（結合・欠損除外・最小サンプルチェック）。
      - rank / factor_summary: ランク付け（同順位は平均ランク）と basic 統計量（count/mean/std/min/max/median）を実装。
    - research パッケージの __all__ で主要関数を再エクスポート。

  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - build_features(conn, target_date):
      - research モジュールの calc_momentum/calc_volatility/calc_value を組み合わせて生ファクターを取得。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
      - 指定の数値カラムを zscore_normalize（data.stats のユーティリティ参照）し ±3 でクリップ。
      - features テーブルへ日付単位で置換（DELETE + バルク INSERT をトランザクションで実行し原子性を保証）。
      - 休場日や当日欠損に対応するため、target_date 以前の最新価格を参照してフィルタリング。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold, weights):
      - features テーブルと ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
      - シグモイド変換・欠損値の中立補完（0.5）・ユーザ提供 weights の検証と正規化（合計が 1 に再スケール）を実装。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）により BUY シグナルを抑制。
      - BUY 閾値（デフォルト 0.60）を超える銘柄を BUY、保有ポジションに対するストップロス（-8%）やスコア低下で SELL を生成。
      - SELL を優先して BUY から除外、ランク再付与。
      - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 売却ロジックに関する注意点: トレーリングストップや保有期間による決済は未実装（positions テーブルに peak_price / entry_date が必要）。

  - パッケージ構成
    - strategy パッケージは build_features / generate_signals を公開する __all__ を定義。
    - execution パッケージ（現状 __init__.py のみ）と monitoring が出口として用意されていることを明示。

Fixed
- 各モジュールでの堅牢性向上:
  - jquants_client: ネットワーク／HTTP エラー時のリトライ・ログ、429 の Retry-After 優先処理、JSON デコードエラーの明確化。
  - save_* 系: PK 欠損レコードのスキップとログ出力を追加。
  - factor/feature 処理: 欠損や非有限値の扱いを明示（math.isfinite で検査）。

Security
- news_collector で defusedxml を使用し、XML パース時の攻撃を防止。
- RSS 処理で受信サイズ上限を設定しメモリ DoS を緩和する方針を採用。
- J-Quants クライアントはトークンの自動リフレッシュを安全に行う設計（無限再帰防止）。

Notes / Known limitations
- 一部の戦略要件（トレーリングストップ、保有60営業日での決済など）は実装予定だが現バージョンでは未実装（signal_generator のコメント参照）。
- positions テーブルに peak_price / entry_date 等が存在しないと一部のエグジット条件は利用できない。
- news_collector の SSRF 対策や URL の検証（IP のチェック等）は方針・インポートはあるが完全実装はファイル末尾に依存（今後の拡張で厳格化する想定）。
- 外部依存: duckdb、defusedxml 等が必要。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH / SQLITE_PATH はデフォルト値あり（data/...）だが環境に合わせて設定推奨。

Breaking Changes
- なし（初回リリース）。

Authors
- 本リリースはリポジトリ内の実装に基づき自動生成的にまとめられています。変更・追記は次バージョンで反映してください。