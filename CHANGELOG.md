# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリースの重要な設計方針・制約（Look-ahead バイアス対策、冪等性、レート制御など）も併記しています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース。kabusys の主要コンポーネントを導入。
  - パッケージメタ情報: src/kabusys/__init__.py にて version=0.1.0、公開 API を定義（data, strategy, execution, monitoring）。

- 環境変数/設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装:
    - コメント行や export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを考慮した堅牢なパース。
  - 読み込みポリシー:
    - OS 環境変数 > .env.local > .env の優先度。
    - .env.local は override=True（ただし OS 環境変数は保護）。
  - Settings クラス:
    - J-Quants / kabu API / Slack / DB パス（DuckDB / SQLite）等のプロパティを提供。
    - env（development/paper_trading/live）と log_level の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を _RateLimiter で管理。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に設定。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ。
    - ページネーション対応の fetch_XXX 関数 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar) を実装。
    - DuckDB へ保存する save_XXX 関数（save_daily_quotes, save_financial_statements, save_market_calendar）
      - ON CONFLICT / DO UPDATE による冪等保存を実現。
      - fetched_at を UTC で記録して「そのデータがいつ取得されたか」をトレース可能に。
    - 入出力変換ユーティリティ (_to_float / _to_int)。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS 取得 → 前処理 → raw_news 保存 のワークフロー設計と主要ユーティリティを実装。
    - デフォルト RSS ソース（Yahoo Finance Business）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータの除去（utm_* 等）、フラグメント除去、クエリのソート。
    - defusedxml を用いた安全な XML パース想定、SSRF・XML Bomb 対策を考慮した実装方針。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）。
    - 記事の型定義 TypedDict (NewsArticle) を提供。
    - 記事 ID は正規化後の URL 等から SHA-256 を使う方針（docstringで仕様記載）。

- 研究用ファクター計算（src/kabusys/research/*.py）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン・200日移動平均乖離率を計算。データ不足時の扱いを明確化。
    - calc_volatility: 20日 ATR（true range の取り扱いに注意）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を計算。最新の財務データ取得ロジックを実装。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。サンプル不足や ties の扱い（平均ランク）を考慮。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
    - rank: ランク計算ユーティリティ（同順位は平均ランク、丸めで ties 検出漏れを防止）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装。
    - research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT）することで冪等性と原子性を確保。
    - 欠損・非有限値の取り扱いを明確化。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features / ai_scores / positions を参照して BUY/SELL シグナルを生成。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティ関数を実装。
      - シグモイド変換、平均化、PER の逆数スコア化などを含む。
    - AI スコア (ai_score, regime_score) を統合:
      - ai_score が未登録なら中立（0.5）で補完。
      - regime_score の平均が負かつサンプル数が一定以上なら Bear と判定し BUY を抑制。
    - 重みの検証・補完・再スケール機能（未知キーや不正値を無視）。
    - エグジット（SELL）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満の場合は SELL。
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位で置換して保存（冪等性・原子性を確保）。

- パッケージエクスポート整備
  - src/kabusys/strategy/__init__.py および src/kabusys/research/__init__.py で主要関数をエクスポート。

### Changed
- 初版リリースにつき該当なし（新規導入）。

### Fixed
- 初版リリースにつき該当なし。

### Security
- 外部データ取り込みに関する対策を明記・実装:
  - news_collector: defusedxml の使用、受信サイズ制限、トラッキングパラメータ除去、URL 正規化により SSRF / XML Bomb / トラッキング問題を軽減。
  - jquants_client: HTTP エラーおよびネットワーク例外に対するリトライ、429 に対する Retry-After の尊重、401 のトークンリフレッシュで不正な認証状態を扱う。

### Notes / Design Decisions
- 冪等性:
  - API から取得したデータを DuckDB に保存する際は ON CONFLICT を用いて上書きし、データの重複挿入を防止。
  - features / signals テーブルへの書き込みは「日付単位」で DELETE→INSERT のトランザクションを行い、処理の再実行（再計算）を安全に行えるようにしている。
- Look-ahead Bias 対策:
  - 取得時刻（fetched_at）を UTC で記録し、「いつシステムがデータを知り得たか」をトレース可能にしている。
  - ファクター計算・シグナル生成は target_date 時点までのデータのみを使用する設計。
- 欠損値戦略:
  - シグナル生成におけるコンポーネント欠損は中立値（0.5）で補完し、不当な降格を防ぐ。
  - 保有銘柄が features に存在しない場合は final_score=0.0 扱いで SELL 判定対象となる（ログ出力あり）。
- レート制御:
  - J-Quants API 呼び出しは固定間隔スロットリングで制御（120 req/min 想定）。ページネーションを跨ぐ呼び出しでもトークンを共有可能にするキャッシュを実装。

---

今後のロードマップ（予定・提案）
- execution 層の具体的実装（kabuステーション連携、注文管理、発注リトライ等）。
- monitoring 層（Slack 通知・アラート・運用ダッシュボード）。
- news_collector の全文抽出 / 記事→銘柄紐付けロジックの実装強化（現状はユーティリティと設計方針を実装済み）。
- より細かいテスト・例外カバレッジの整備（ネットワーク障害時の挙動・DuckDB 操作のエラー処理等）。

（翻訳・要約ではなく、コードの実装内容・設計方針に基づき記載しています。実装漏れや追加修正がある場合は随時更新してください。）