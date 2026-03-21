# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主要な機能は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義し、主要サブモジュール（data, strategy, execution, monitoring）を公開。

- 環境変数・設定管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動ロード（プロジェクトルートの検出は .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサの実装: コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応。
    - 環境変数保護（OS 環境変数を protected として .env.local の上書きを制御）。
    - Settings クラスでアプリケーション設定をプロパティ提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
      - KABUSYS_ENV 値検証（development, paper_trading, live）。
      - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
      - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py を追加。
    - API レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
    - リトライ（指数バックオフ）・最大試行回数の制御、HTTP 408/429 と 5xx を再試行対象とする実装。
    - 401 の場合はリフレッシュトークンで id_token を自動更新して 1 回再試行。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE。
      - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE。
      - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE。
    - 保存時の PK 欠損行はスキップして警告ログを出力。
    - fetched_at を UTC ISO8601 で記録。
    - 型変換ユーティリティ (_to_float / _to_int) を提供し、安全な変換を行う。

- ニュース収集
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード収集の基本処理を実装（デフォルトに Yahoo Finance のビジネスカテゴリ RSS を含む）。
    - XML 処理に defusedxml を使用し XML アタック対策を実施。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 保護。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を保証。
    - RSS コンテンツの前処理（URL 除去、空白正規化）や SSRF 対策（HTTP/HTTPS 限定、IP/ホストチェック等を想定）。
    - バルク INSERT のチャンク処理で DB 負荷を抑制。INSERT RETURNING を用いて挿入件数を正確に返す方針。

- リサーチ用ファクター計算・探索
  - src/kabusys/research/factor_research.py を追加。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（ma200 は 200 行未満なら None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR の NULL 伝播やウィンドウカウントを適切に処理）。
    - calc_value: raw_financials から最新財務を結合して per / roe を計算。
    - すべて prices_daily / raw_financials のみ参照し、ルックアヘッドバイアスを避ける設計。
  - src/kabusys/research/feature_exploration.py を追加。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク）相関を計算（有効データが 3 未満なら None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク、丸め誤差対策あり）や基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __init__ で主要関数をエクスポート。

- 戦略（特徴量エンジニアリング・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py を追加。
    - build_features(conn, target_date):
      - research の calc_momentum / calc_volatility / calc_value を呼び出しファクタを取得。
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
      - 数値ファクターを z-score 正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップして外れ値を抑制。
      - features テーブルへ日付単位で削除→挿入（トランザクションにより原子性を保証、冪等）。
  - src/kabusys/strategy/signal_generator.py を追加。
    - generate_signals(conn, target_date, threshold=0.6, weights=None):
      - features と ai_scores を統合し、モメンタム / バリュー / ボラティリティ / 流動性 / news（AI）を組み合わせて final_score を計算（デフォルト重みを用意）。
      - 不足コンポーネントは中立値 0.5 で補完し欠損銘柄の不当な降格を防止。
      - _sigmoid / _avg_scores 等のスコア計算ユーティリティを実装。
      - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数が十分な場合）により BUY シグナルを抑制。
      - エグジット（SELL）判定を実装:
        - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
        - final_score が threshold 未満なら score_drop で SELL。
        - 価格欠損や avg_price 欠損時のスキップ・警告。
      - BUY / SELL を signals テーブルへ日付単位で削除→挿入（トランザクションで原子性）。
      - weights 引数は入力検証（既知キーのみ、負値/NaN/Inf/非数は無視）、合計が 1.0 でなければ再スケール。

- モジュールエクスポート
  - src/kabusys/strategy/__init__.py で build_features と generate_signals を公開。

### Security
- ニュース XML パースに defusedxml を利用して XML 関連攻撃を防止。
- news_collector で受信バイト数上限を設け、メモリ消費による DoS を緩和。
- news_collector の URL 正規化とスキーム制限（HTTP/HTTPS）により SSRF リスクを低減。
- jquants_client の HTTP リトライ実装で不正なヘッダ等に対する堅牢性を向上。

### Design / Implementation Notes
- Look-ahead bias の防止を設計上の重要要件としており、各計算は target_date 時点のデータのみを使用するように実装。
- DuckDB を主要な分析 DB として使用。保存処理は冪等化（ON CONFLICT）およびトランザクションでの置換を基本とする。
- 外部依存は最小限（duckdb と defusedxml 等）。research モジュールは pandas 等に依存しない純 Python 実装。
- ロギングを広範に利用し、操作の可観測性（警告・情報・デバッグ）を確保。

### Fixed
- 初回リリースのため該当なし。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後の予定（例）
- ニュース記事と銘柄の自動紐付け（news_symbols テーブルへの連携）。
- positions テーブルに peak_price / entry_date を持たせ、トレーリングストップや時間決済のエグジット条件を実装。
- パフォーマンス向上のため DuckDB クエリ最適化とバルク処理の改善。