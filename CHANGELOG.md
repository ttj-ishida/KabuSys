# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。重要な実装や動作はコードのコメント・実装から推測してまとめています。

なお日付は本 CHANGELOG 作成日時（推測）です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主に以下の領域をカバーします：環境設定読み込み、データ取得と保存（J-Quants API / RSS ニュース）、研究系ファクター計算、特徴量エンジニアリング、シグナル生成。DuckDB をデータ層として使用し、各処理は冪等性・トランザクション制御・ルックアヘッドバイアス防止を考慮して設計されています。

### Added

- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。トップレベルの公開モジュールを定義（data, strategy, execution, monitoring）。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
  - 自動 .env ロード機能（プロジェクトルートの探索: .git または pyproject.toml を基準）。
  - ロード優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォートなし値では '#' 前のスペース/タブをコメント開始とみなす）
  - 必須変数取得用の _require ヘルパー（未設定時は ValueError を送出）。
  - 設定バリデーション: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェック。
  - DB パス設定（DUCKDB_PATH / SQLITE_PATH）を Path として扱うユーティリティを提供。

- データ取得 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限対応（120 req/min）の固定間隔スロットリング（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大リトライ回数 3、408/429/5xx 対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を回避）。
  - ページネーション対応のデータ取得ユーティリティ:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB へ冪等保存する関数を実装（ON CONFLICT による upsert を使用）:
    - save_daily_quotes → raw_prices テーブル（fetched_at を UTC で記録）
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - ユーティリティ関数: _to_float / _to_int（安全な型変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存するためのユーティリティ群を追加。
  - defusedxml を用いた XML パース（XML Bomb 等の対策）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）の除去、スキーム/ホストの小文字化、クエリパラメータソート、フラグメント削除。
  - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）やバルク INSERT のチャンク処理を導入。
  - 記事 ID の生成方法（正規化した URL の SHA-256 ハッシュ先頭 32 文字）など、冪等性を意識した設計が記載されている。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネス RSS）。

- 研究 / ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。過去データ不足に対する保護あり。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播制御（欠損の正しい扱い）。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS=0 や欠損は None）。
  - feature_exploration を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に取得（1クエリ）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル不足や ties の取り扱いを考慮。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary: 各ファクターの基本統計（count/mean/std/min/max/median）を計算。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research で計算した生ファクターを統合して features テーブルに保存するパイプラインを実装。
  - フロー:
    - calc_momentum / calc_volatility / calc_value を呼び出して素のファクターを取得
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用
    - 指定カラムを Z スコアで正規化し ±3 でクリップ
    - 日付単位で削除→挿入を行うことで原子性（トランザクション）を保証（冪等）
  - ルックアヘッドバイアス回避の方針が組み込まれている（target_date 時点のデータのみ使用）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合し、BUY / SELL シグナルを生成して signals テーブルへ保存するパイプラインを実装。
  - 実装ポイント:
    - モメンタム・バリュー・ボラティリティ・流動性・ニュースのコンポーネントスコア計算（シグモイド変換、欠損は中立 0.5 で補完）
    - デフォルト重み（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）に対する user-provided weights の補完・正規化・検証
    - Bear レジーム判定（AI の regime_score の平均が負の場合）による BUY 抑制
    - SELL（エグジット）判定の実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
      - 保有銘柄で価格欠損時は SELL 判定処理をスキップして誤クローズを防止するログ出力
    - 日付単位の置換（DELETE → bulk INSERT）により冪等性を確保
    - ログ出力としきい値・合算結果の保護ロジックあり

- モジュール公開（kabusys.strategy.__init__ / kabusys.research.__init__）
  - 主要 API（build_features, generate_signals, calc_momentum, calc_volatility, calc_value, zscore_normalize 等）をパッケージ公開。

### Changed

- （初回リリースのため無し／実装段階で設計上の配慮多数）
  - 各モジュールは冪等性・トランザクション・ログ出力・入力検証を重視して実装されていることを明記。

### Fixed

- （初回リリースのため無し）

### Security

- news_collector で defusedxml を採用し、RSS パース時の XML 攻撃に対策。
- J-Quants クライアントでトークンの扱い・自動更新ロジックを実装し、認証エラーに対処（無限再帰回避のための allow_refresh フラグあり）。
- HTTP 429 の Retry-After を尊重する実装や、ネットワークエラーに対する指数バックオフが導入されている。

### Notes / Implementation details（重要ポイント）

- DuckDB をデータレイクとして想定し、prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions / market_calendar 等のテーブルを参照／更新する実装。
- 多くの処理で「target_date 時点のデータのみ」を使う設計（ルックアヘッドバイアス回避）。
- 各種保存は ON CONFLICT（upsert）やトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性・冪等性を確保。
- news_collector のドキュメントには SSRF や IP 検査などの言及があるが、実装ファイルの断片からは URL 正規化・トラッキング除去・受信サイズ制限・defusedxml の採用が確認できる点に留意してください。
- strategy 層は execution 層（発注API）への直接依存を持たない設計。signals テーブルへの書き込みが最終出力。

---

今後の予定（推測）
- execution 層（注文発行 / kabuステーション API）と monitoring（モニタリング / Slack 通知等）の実装統合
- テスト・CI、実稼働向けのより詳細なエラーハンドリングとメトリクス収集
- news_collector の SSRF 対策・ソース多様化、AI スコア周りの学習パイプライン統合

--- 

この CHANGELOG はコード内の docstring / 実装から推測して作成しています。実際の変更履歴（コミット履歴やリリースノート）と差異がある場合があります。必要であれば実際のコミットログに基づく正確な CHANGELOG 作成のお手伝いをします。