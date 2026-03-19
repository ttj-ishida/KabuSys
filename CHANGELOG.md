CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-19
--------------------

初回リリース。日本株自動売買システムのコア機能群を実装しました。主要な追加点は以下の通りです。

Added
- パッケージのエントリポイント
  - kabusys.__init__ にて __version__="0.1.0" と依存公開モジュールを定義。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート中のエスケープ、インラインコメント処理等に対応。
  - 環境変数保護機能: OS側の既存環境変数は protected キーとして扱い、.env.local の上書きから守る。
  - Settings クラスを提供（プロパティ経由で設定取得）。必須キー取得時は未設定で ValueError を送出する _require を使用。
  - 設定検証:
    - KABUSYS_ENV は development / paper_trading / live に制限。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL に制限。
  - デフォルト値:
    - KABUSYS_API_BASE_URL のデフォルト、DUCKDB_PATH/SQLITE_PATH のデフォルト等を設定。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足 / OHLCV）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - rate limiting（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）。対象: ネットワークエラー・408/429/5xx。
    - 401 レスポンス時はリフレッシュトークンからトークンを自動再取得して 1 回リトライ（ループ防止の allow_refresh 制御）。
    - JSON デコード/エラーハンドリングを強化。
  - DuckDB への保存ユーティリティ（冪等化）:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE。
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE。
    - レコードの型変換ユーティリティ _to_float / _to_int を実装（不正値を None にする安全処理）。
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡を意識）。

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・記事整形の基盤を実装（デフォルト RSS ソースに Yahoo Finance を含む）。
  - URL 正規化機能:
    - トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、クエリソート、スキーム/ホスト小文字化、フラグメント除去。
  - セキュリティ/堅牢化:
    - defusedxml を使用して XML の脆弱性を軽減。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリDoS対策。
    - SSRF 対策や非 HTTP/HTTPS スキーム拒否等の方針を採用（実装の意図が明記）。
  - DB 保存はバルク/チャンク挿入でパフォーマンス配慮。記事 ID は正規化 URL の SHA-256 で決める設計。

- 研究系モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播制御など欠損扱いに注意。
    - calc_value: raw_financials から直近財務を参照し PER/ROE を計算。
    - SQL とウィンドウ関数を用いた実装で効率化（DuckDB を前提）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（浮動小数の丸めで ties 検出の安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research 内の calc_momentum / calc_volatility / calc_value を呼び出して原因子を取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定の数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で features テーブルへ置換（DELETE してからトランザクション + bulk INSERT）し原子性を保証。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - コンポーネントごとの計算:
      - momentum: momentum_20/60 と ma200_dev を sigmoid を通して平均化。
      - value: PER を 20 を基準にスケールする逆関数で変換（PER が不正な場合は None）。
      - volatility: atr_pct の Z スコアを反転して sigmoid。
      - liquidity: volume_ratio を sigmoid。
      - news: ai_score を sigmoid（未登録は中立補完）。
    - weights の補完・検証:
      - 未知キー・非数値・NaN/Inf・負値は無視。デフォルト重みを補完し、合計が 1.0 でなければリスケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつ十分なサンプル数（デフォルト 3）であれば BUY を抑制。
    - SELL 生成（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）優先判定。
      - final_score が閾値未満なら売り。
      - 価格欠損時は SELL 判定をスキップして保護的に扱う。
    - 日付単位の signals 置換（DELETE→INSERT、トランザクションで原子性）。
    - 戦略設計の方針（ルックアヘッドバイアス回避、execution 層非依存）に準拠。

Changed
- （初版のため該当なし）

Fixed
- ロバスト性の強化:
  - .env パーサでクォート内のエスケープやコメントの扱いを明確化し、不正な行をスキップする実装。
  - prices/financials の保存で PK 欠損行をスキップするロギングと安全な動作。
  - DuckDB へのバルク挿入でトランザクションとロールバックを適切に使用（失敗時の巻き戻し処理・警告ログ）。

Security
- ニュース取得で defusedxml を使用し XML 関連の攻撃を軽減。
- ニュースの URL 正規化でトラッキングパラメータ除去、スキームチェック等を行い SSRF やデータ漏洩リスクを低減。
- API クライアントでタイムアウト・リトライ制御を実装し、DoS/無限ループ対策を導入。

Notes / Known limitations
- 一部の戦略仕様は将来的な拡張を想定（例: トレーリングストップや時間決済は positions テーブルに peak_price / entry_date が必要なため未実装）。
- news_collector のフルパイプライン（RSS フェッチ→記事抽出→DB 紐付け）の細部は拡張余地あり（本リリースでは基盤と安全方針を実装）。
- research モジュールは DuckDB と prices_daily/raw_financials 等の前提テーブルが必要。実運用前にスキーマ確認を推奨。
- J-Quants の API 利用にはリフレッシュトークン等の環境変数設定が必須（Settings で未設定時は ValueError を送出）。

開発者向けメモ
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Settings プロパティは遅延評価・検証型なのでユニットテストでは環境変数を差し替えて挙動確認すること。

--- 

今後の予定（候補）
- execution 層の実装（kabu ステーション連携・注文発行）
- news_collector の記事→銘柄紐付けロジックの強化（NLP/シンボル抽出）
- モデル学習 / AI スコア算出パイプラインの統合
- 単体テスト・CI の整備とカバレッジ追加

（以降のリリースでは Unreleased セクションを用いて差分を記載してください）