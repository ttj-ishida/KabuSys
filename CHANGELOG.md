# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティック バージョニングを使用します。  
初回リリースは 0.1.0 です。

## [0.1.0] - 2026-03-19

初期リリース — KabuSys: 日本株自動売買システムのコア機能を実装しました。以下は主な追加・設計方針・実装の要点です。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名・バージョン (0.1.0) と公開モジュールを定義。

- 環境設定管理
  - src/kabusys/config.py:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の柔軟なパース実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを提供し、必須環境変数取得（_require）、値検証（KABUSYS_ENV, LOG_LEVEL）および便利なプロパティ（duckdb/sqlite パス、is_live/is_paper/is_dev など）を実装。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py:
    - API レート制御（固定間隔スロットリング）を実装（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx を再試行対象に含め、429 の場合は Retry-After を優先。
    - 401 発生時に自動的にリフレッシュトークンで ID トークンを再取得して 1 回だけリトライする処理を実装（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力不正値に耐性を持たせた処理。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を収集し raw_news に冪等保存する処理の骨子を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
    - セキュリティ対策：defusedxml による XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、既知トラッキングパラメータ除去、HTTP/HTTPS スキームの想定等（設計方針として明記）。
    - バルク挿入チャンクや挿入数の正確な把握（INSERT RETURNING を想定）などパフォーマンス配慮。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value に該当する定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した過去データスキャン、欠損データや不正データの取り扱いに配慮。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンρ）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。
    - 小数丸めや ties の扱いを明示（round(v, 12) により浮動小数点の誤差対策）。
  - src/kabusys/research/__init__.py に主要関数をエクスポート。

- 戦略（特徴量作成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py:
    - 研究環境で計算された生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化（外れ値 ±3 でクリップ）して features テーブルへ UPSERT（日付単位の置換、トランザクションで原子性を保証）。
    - ユニバース判定に必要な定数（_MIN_PRICE, _MIN_TURNOVER 等）と正規化カラムの指定を実装。
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合成で final_score を算出。
    - デフォルト重みと閾値（_DEFAULT_WEIGHTS, _DEFAULT_THRESHOLD）を定義し、ユーザ指定 weights の検証・補完・再スケールを実装。
    - Bear レジーム検知（AI の regime_score 平均が負 → BUY 抑制）を実装（サンプル数閾値あり）。
    - BUY 条件（threshold 超え）および SELL 条件（ストップロス -8% / final_score の低下）を実装。SELL は優先扱いし、signals テーブルへ日付単位で置換（トランザクション）。
    - 欠損コンポーネントは中立値（0.5）で補完するポリシーを採用し、公平なランク付けを維持。

- モジュールエクスポート
  - src/kabusys/strategy/__init__.py と src/kabusys/research/__init__.py により主な関数を外部公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml の使用、受信サイズ制限、トラッキングパラメータ除去、HTTP/HTTPS スキーム想定等のセキュリティ設計を明記。
- jquants_client の HTTP エラーハンドリングやリトライにより、意図しない API 負荷や認証エラー時の情報漏洩を抑制する設計。

### Notes / Design highlights
- ルックアヘッドバイアス対策: 取得時刻（fetched_at）を UTC で記録し、feature/signal の計算は target_date 時点のデータのみ参照する方針を徹底。
- 冪等性: raw データと分析結果の保存は可能な限り冪等（ON CONFLICT / 日付単位DELETE→INSERT の置換）になるよう設計。
- DuckDB を中心に設計しており、本リポジトリの関数群は発注 API や本番 execution 層に依存しない（分離された責務）。
- エラーハンドリング: トランザクション中の例外発生時は ROLLBACK を試み、失敗時は警告ログを出力するように実装。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後の予定（例）
- ニュース → 銘柄マッチング（news_symbols への紐付け）実装の完成
- execution 層（kabu API）との連携部の実装
- 追加のリスク管理条件（トレーリングストップ、時間決済等）の実装

ご要望があれば、この CHANGELOG を英語版に翻訳したり、個別ファイルや関数ごとの詳細変更点（コミット単位想定）を追記します。