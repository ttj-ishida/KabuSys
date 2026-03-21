CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog"（https://keepachangelog.com/ja/）
およびセマンティックバージョニングに従います。

v0.1.0 - 2026-03-21
-------------------

Added
- 全体
  - 初期リリース。パッケージ名 kabusys、公開 API を __all__ でエクスポート（data, strategy, execution, monitoring）。
  - DuckDB を中心としたデータパイプラインと戦略モジュールを含む日本株自動売買向けライブラリを提供。

- config (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を基準）。
  - 環境変数読み込みパーサを実装。コメント行、export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメントの扱いなどを考慮。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定アクセス用の Settings クラスを提供（jquants_refresh_token / kabu_api_password / slack_bot_token 等の必須項目を _require() で検証）。
  - KABUSYS_ENV（development/paper_trading/live） と LOG_LEVEL（DEBUG/INFO/...） のバリデーションを実装。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）を Path 型で取得。

- data.jquants_client (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - 固定間隔レートリミッタ（120 req/min）を実装し、呼び出し間隔を厳守。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。再試行対象には 408/429/5xx を含む。
  - 401 を検知した場合のトークン自動リフレッシュを実装（リフレッシュは 1 回のみ）。get_id_token でリフレッシュトークンを用いて ID トークンを取得。
  - ページネーションをサポートしたデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複を排除。
  - 型変換ユーティリティ（_to_float, _to_int）により不正データを安全に扱う。

- data.news_collector (src/kabusys/data/news_collector.py)
  - RSS からニュースを収集して raw_news へ保存するモジュールを実装。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を担保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_, fbclid, gclid 等）の除去、クエリキーソート、フラグメント除去。
  - セキュリティ対策：defusedxml による XML パース、防止対象（XML Bomb 等）、HTTP/HTTPS スキーム以外の URL 拒否、最大受信バイト数（10MB）制限、SSRF/メモリ DoS 対策。
  - バルク INSERT のチャンク化（デフォルト 1000 件）とトランザクションでの一括保存を想定。

- research モジュール（src/kabusys/research/...)
  - factor_research: prices_daily/raw_financials を参照してファクター計算を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率(ma200_dev) を計算。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播制御と窓内カウントによる欠損判定を実装。
    - calc_value: 直近財務データと当日の株価を組み合わせて PER / ROE を計算（EPS が 0/欠損なら PER は None）。
  - feature_exploration: 研究用ユーティリティを実装。
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは営業日数（連続レコード）として扱い、スキャン範囲はバッファで制限。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。サンプル不足（<3）や定数系列を扱う際は None を返す。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位（ties）を平均ランクで扱うランク関数（丸めによる ties 検出を防ぐため round(v,12) を使用）。

- strategy モジュール（src/kabusys/strategy/...)
  - feature_engineering.build_features:
    - research で計算した raw ファクターをマージ・ユニバースフィルタ適用（最低株価 300 円、20日平均売買代金 5 億円）・Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）・±3 でクリップして features テーブルへ日付単位で置換（トランザクションによる原子性保証、冪等）。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照してユニバース判定を行う。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算（デフォルト重みは StrategyModel.md に準拠）。
    - weights の検証・補完・再スケーリング（未知キーや負値/非数値を無視、合計が 1 でない場合は正規化）。
    - シグモイド変換で Z スコアを [0,1] にマップ。欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）では BUY シグナルを抑制。
    - BUY シグナルは threshold（デフォルト 0.60）を超える銘柄に付与。SELL は保有ポジションに対してストップロス（-8%）またはスコア低下で判定。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で冪等）。

Security
- news_collector で defusedxml を使用して XML パースの安全性を確保（XML Bomb 等の攻撃を防止）。
- RSS の受信サイズ上限を設け、SSRF を考慮した URL 検証を行う。
- J-Quants クライアントではトークン自動リフレッシュの際に無限ループにならないよう allow_refresh フラグを導入。

Known limitations / TODOs
- signal_generator の一部エグジット条件は未実装（コメント記載）。
  - トレーリングストップ（peak_price が positions テーブルで必要）、時間決済（保有日数閾値）は未実装。
- news_collector: RSS フィード取得 /記事パースの詳細な実装（XML -> NewsArticle 抽出ロジックの続き）が本稿の抜粋で未完（コードベースの一部のみ）。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は本パッチの参照先として存在するが、当 CHANGELOG は実装の横断説明に留める（詳細は該当モジュール参照）。

Notes / Design decisions
- DuckDB を利用し SQL と Python を組み合わせて効率的に時系列計算を実施。
- ルックアヘッドバイアス防止方針: すべて target_date 時点で「当該時点で利用可能なデータのみ」を参照する設計。
- 冪等性を重視し、DB 書き込みは可能な限り ON CONFLICT / 日付単位の DELETE+INSERT（トランザクション）で処理。

署名
- 初期リリース: v0.1.0（2026-03-21）

もし CHANGELOG に追記すべき項目（リリース日変更、抜け、あるいは実装箇所の補足説明など）があれば指示してください。