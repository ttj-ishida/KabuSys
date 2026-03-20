CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。  

Unreleased
----------

- なし

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース (0.1.0) — 日本株自動売買システム「KabuSys」の基本機能を実装。
- パッケージ化
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / ロード
  - settings 管理クラスを実装（kabusys.config.Settings）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理（クォートなしでは '#' の直前が空白/タブのときコメントと判定）。
  - 必須環境変数取得時の判定 (ValueError を発生) とデフォルト値（例: KABU_API_BASE_URL, DB パス等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。

- Data 層（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 固定間隔レートリミッタ（120 req/min 相当）実装。
    - 汎用 HTTP リクエストユーティリティ: ページネーション対応、JSON デコードエラー検出、最大リトライ（指数バックオフ）処理。
    - 401 応答時にリフレッシュトークンで ID トークンを再取得して 1 回リトライする自動リフレッシュ機能（トークンキャッシュをモジュール内で保持）。
    - リトライ対象ステータスおよび Retry-After 処理（429 の場合優先）。
    - fetch_* 関数群（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）: ページネーション対応。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - 冪等性確保のため ON CONFLICT DO UPDATE を使用。
      - PK 欠損レコードのスキップとログ警告。
      - fetched_at を UTC で記録して取得時点をトレース可能に。
    - 型変換ユーティリティ (_to_float, _to_int) による堅牢なデータ整形。
  - ニュース収集（news_collector）
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - RSS 取得と記事整形、URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や defusedxml を用いた XML 攻撃対策。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - DB バルク挿入のチャンク分割（INSERT_CHUNK_SIZE）とトランザクション集約。
    - SSRF / 非 HTTP スキーム対策やトラッキングパラメータ除去ロジックを実装。

- Research 層（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - Volatility: 20 日 ATR、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播制御とカウント条件を実装。
    - Value: raw_financials から最新財務データを参照して per, roe を算出（EPS が 0 または欠損時は None）。
    - DuckDB SQL を用いた効率的な窓関数利用とスキャン範囲バッファ（カレンダー日 2 倍）による休日対応。
  - Feature exploration（feature_exploration）
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）対応、LEAD を使った一括取得。
    - IC 計算 (calc_ic): ファクターと将来リターンのスピアマンランク相関（ties は平均ランク処理）。有効サンプル数が 3 未満の場合は None を返す。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算（None を除外）。
    - ランク計算ユーティリティ (rank): 同位は平均ランク、浮動小数誤差対策の round() を適用。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering）
    - research の生ファクターを取得し統合・正規化して features テーブルに保存。
    - ユニバースフィルタ実装: 最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8（5 億円）。
    - Z スコア正規化と ±3 でのクリップ、日付単位の置換（トランザクションで原子性確保、冪等）。
    - ルックアヘッドバイアス防止の設計（target_date 時点のデータのみ使用）。
  - シグナル生成（signal_generator）
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。閾値 DEFAULT_THRESHOLD = 0.60。
    - 重みのバリデーション（未知キーや非数値・負値は無視）、合計を 1.0 に再スケール。
    - コンポーネントスコア計算: シグモイド変換、欠損値は中立 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（サンプル数閾値あり）。
    - SELL 条件実装: ストップロス（終値/avg_price - 1 <= -8%）優先、スコア低下（final_score < threshold）。
    - 未実装のエグジット条件を明示（トレーリングストップ / 時間決済）。
    - 日付単位の置換（トランザクション + バルク挿入）で冪等性を維持。
    - ログ出力で重要イベント（Bear 検知、ROLLBACK エラー等）を報告。

Changed
- -（初回リリースのため該当なし）

Fixed
- -（初回リリースのため該当なし）

Security
- defusedxml を使用した RSS パース、受信バイト制限、SSRF を意識した URL 検証など、外部入力に対する基本的な安全対策を導入。

Notes / Implementation details
- DuckDB を中心に prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルを想定した実装。
- 多くの書き込み処理はトランザクション + 一括挿入で原子性を担保。
- 冪等性に配慮した設計（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING / 日付単位の DELETE→INSERT パターン）。
- ルックアヘッドバイアス防止を設計方針として明示（target_date 以前のデータのみ参照）。
- 一部機能（execution 層、monitoring 層）は名前空間のみ用意され、発注ロジック等の実装は含まれない。

Breaking Changes
- なし（初回リリース）

Contributing
- 今後は機能追加・修正ごとに本 CHANGELOG に記録してください。