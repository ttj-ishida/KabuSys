# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日付は YYYY-MM-DD 形式です。
- セクション: Added / Changed / Deprecated / Removed / Fixed / Security を使用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にて version を "0.1.0" として公開。
  - __all__ に "data", "strategy", "execution", "monitoring" を含める。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root() を実装（CWD に依存しない）。
  - .env パーサ: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応する _parse_env_line() を実装。
  - .env 自動ロード順: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - 保護された OS 環境変数を上書きしない実装（protected パラメータ）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live） / ログレベル等のプロパティを公開。
  - Settings.env, is_live, is_paper, is_dev による環境判定。無効値は ValueError を送出。
  - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi", DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db" 等。

- データ取得・永続化: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 基本機能: レート制限（120 req/min 固定間隔スロットリング）、最大リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュを含む堅牢な _request() 実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存用関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供。ON CONFLICT（UPSERT）で冪等性を保証。
  - 型安全な変換ユーティリティ _to_float / _to_int を実装。
  - fetched_at を UTC ISO8601 で保存し、Look-ahead バイアスをトレース可能に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news へ保存する基盤を実装（デフォルト RSS: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策: defusedxml を用いた XML パース、防爆 XML 対策、受信最大バイト数制限（10MB）、HTTP/HTTPS スキームチェック、SSRF 想定対策。
  - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソートを行う _normalize_url() を実装。
  - 記事 ID を正規化 URL の SHA-256 の先頭 32 文字で生成する方針を採用。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）およびトランザクションでの一括保存を想定。

- 研究（research）モジュール
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、および 200 日移動平均乖離率 (ma200_dev) を計算（ウィンドウ行数不足時は None）。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio) を計算。true_range の NULL 伝播を適切に制御。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER / ROE を計算。EPS が 0 の場合は PER を None にする。
    - SQL-ベースの効率的スキャン設計（スキャン範囲は余裕を持ったカレンダー日で制限）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman のランク相関（IC）を計算（有効レコード数 < 3 の場合は None）。
    - rank(values): 同順位は平均ランクにするランク関数（丸め誤差対策で round(v, 12) を使用）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。

  - research パッケージ __init__ に主要関数群をエクスポート。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features(conn, target_date): research モジュールの calc_* から生ファクターを取得し、
      ユニバースフィルタ（最低株価 300 円 / 20 日平均売買代金 5 億円）を適用、Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 正規化対象カラムの指定（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）と欠損取り扱いを実装。
    - 価格参照は target_date 以前の最新価格を使用（休場日・欠損対応）。

  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - コンポーネントスコア:
      - momentum, value, volatility, liquidity, news（AI スコア）を計算するユーティリティを提供。
      - Z スコアをシグモイドで [0,1] に変換。PER は 1/(1+per/20) の近似で変換。
    - ウェイト処理: 与えられた weights を既定値にマージし、無効値を除外、合計が 1 に再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、サンプル数が閾値以上なら BUY を抑制。
    - SELL 生成: ストップロス（終値が平均取得価格から -8% 以下）と final_score が閾値未満の場合に SELL。保有銘柄の価格欠損時は判定をスキップする等の安全措置。
    - BUY/SELL の競合処理: SELL 対象を優先して BUY から除外し、BUY のランクを再付与。
    - signals テーブルへの書き込みはトランザクションで原子性を保証。

- データ統計ユーティリティのエクスポート
  - kabusys.research と kabusys パッケージで zscore_normalize 等を再エクスポートする仕組みを提供（src/kabusys/research/__init__.py）。

### Known issues / Notes
- トレーリングストップや保有期間による強制決済などの一部エグジット条件は未実装（signal_generator 内で TODO コメントあり）。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要。
- news_collector や RSS 処理の詳細な実装（完全なフィードパース・記事→銘柄マッピング等）は骨格が提供されており、追加実装が想定される。
- features テーブルに avg_turnover は保存しない（ユニバースフィルタ用に内部で参照するのみ）。
- _request() のリトライ対象は基本的なステータスセットとネットワークエラーに限定。運用上の例外ケースはログ・例外でトラブルシュート可能だが、環境依存の挙動を観測する必要あり。
- 自動 .env ロードはプロジェクトルート判定に依存するため、パッケージ配布後に環境が期待通りでない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って挙動を切り替え可能。

### Security
- news_collector: defusedxml の採用、最大受信サイズ制限、トラッキングパラメータ除去などの安全対策を実装。
- jquants_client: トークンの扱いはキャッシュと自動リフレッシュで実装。ログにセンシティブ情報を出力しない運用に留意。

---

このリリースはシステム全体の基盤（データ収集、特徴量生成、シグナル生成、研究用ユーティリティ、設定管理）を一通り揃えた初期版です。運用時は環境変数設定（特に API トークンや Slack 設定）と DuckDB / SQLite のスキーマ準備を行った上でご利用ください。