# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルではリポジトリの変更履歴を自然言語で要約しています。バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

以下はコードベースから推測して作成した初回リリースの説明です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-19

Added
- パッケージ初期リリース。日本株自動売買システムのコア機能群を提供。
- 環境設定管理（kabusys.config.Settings）
  - .env/.env.local 自動読み込み（読み込み優先順位: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応（テスト用途）。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 環境変数取得ヘルパ `_require`（未設定時に ValueError を送出）。
  - 各種設定プロパティ:
    - J-Quants / kabu ステーション / Slack トークン等（必須チェック）
    - DB パス（duckdb / sqlite のデフォルトパス）
    - 実行環境（development/paper_trading/live）とログレベル検証
    - ヘルパプロパティ is_live/is_paper/is_dev

- Data 層
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 固定間隔スロットリングによるレート制御（120 req/min 相当）。
    - 自動リトライ: 指数バックオフ（最大 3 回）、408/429/5xx をリトライ対象。
    - 401 受信時のトークン自動リフレッシュ（1 回まで）と再試行処理。
    - ページネーション対応（pagination_key の循環防止）。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes: raw_prices への ON CONFLICT DO UPDATE を使用した保存
      - save_financial_statements: raw_financials への冪等保存
      - save_market_calendar: market_calendar への冪等保存
    - HTTP ユーティリティと安全な JSON デコード、エラーメッセージ強化。
    - 型変換ユーティリティ: _to_float / _to_int（空値・不正値を None にする安全設計）。
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィード取得・パースと raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING 想定）。
    - 記事ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - URL 正規化:
      - スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント除去、クエリソート等。
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和。
    - SSRF 対策（HTTP/HTTPS 以外のスキーム拒否等の方針が示唆されている設計）。
    - バルク挿入のチャンク処理（_INSERT_CHUNK_SIZE）で SQL 長制限を回避。
    - デフォルト RSS ソース定義（例: Yahoo Finance の Business RSS）。

- Research 層（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の算出（window の行数不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率の算出。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（最新報告の取得ロジックあり）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）による Information Coefficient（IC）計算。データ不足時は None を返す。
    - rank: 同順位の平均ランク付け（丸めによる ties 検出対策あり）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリー。
    - 全て外部ライブラリに依存せず標準ライブラリで実装。

- Strategy 層（kabusys.strategy）
  - feature_engineering.build_features:
    - research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列を zscore_normalize（kabusys.data.stats に依存）して ±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションによる原子性確保）で冪等性を担保。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用する設計。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントは欠損時に中立値 0.5 で補完して不当な降格を防止。
    - デフォルト重み（momentum 0.40 等）を持ち、与えられた weights は検証後に合計 1.0 に再スケーリング。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear、サンプル数閾値あり）による BUY 抑制。
    - BUY 閾値はデフォルト 0.60、STOP-LOSS は -8%（優先判定）。SELL の判定条件はストップロスとスコア低下。
    - positions / prices_daily を参照して保有ポジションのエグジット判定を行い、SELL シグナル生成。
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換で書き込み（トランザクションで原子性）。
    - weights の不正値（未知キー、NaN/Inf、負値、非数値）をスキップして警告出力。

- その他
  - パッケージ __init__.py でバージョンを定義（0.1.0）と、公開 API（data, strategy, execution, monitoring）を整理。
  - execution パッケージのプレースホルダを用意（将来の発注・実行ロジックの設計を示唆）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- news_collector で defusedxml を利用し XML 関連の攻撃を緩和。
- HTTP レスポンスサイズ上限や SSRF 対策（設計方針）により外部入力の安全性に配慮。

Notes / Known limitations（コードから推測）
- 一部のエグジット条件（トレーリングストップ、時間決済など）は positions テーブルの追加情報（peak_price / entry_date 等）が未実装のため未対応。
- news_collector の URL 検証や SSRF 対応は設計方針として記載されているが、実運用時の詳細なネットワーク制限は利用側で注意が必要。
- 外部 API 呼び出しにおけるタイムアウトや重いページネーションワークロードに対する追加の運用監視が望ましい。

---

（この CHANGELOG はコード内容から推測して作成した要約です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。）