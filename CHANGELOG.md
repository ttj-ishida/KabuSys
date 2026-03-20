# CHANGELOG

すべての重要な変更をここに記載します。本ファイルは Keep a Changelog の形式に準拠しています。

現在のリリースポリシー: セマンティックバージョニングに従います。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - kabusys パッケージとサブモジュール群を導入（data, strategy, execution, monitoring を公開）。
  - パッケージバージョン: 0.1.0

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応
    - プロジェクトルートの自動検出 (.git または pyproject.toml を基準)
  - .env の行パーサを実装（コメント、`export KEY=...`、シングル/ダブルクォート、エスケープ文字対応、インラインコメント処理など）。
  - 環境変数の保護（既存 OS 環境変数を protected として上書き制御）。
  - Settings クラスを提供し、必須変数のチェックや型/値検証を行うプロパティを実装。
    - J-Quants / kabuステーション / Slack / DB パスなどの設定を取得。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - duckdb/sqlite パスを Path 型で返却。

- データ収集・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔のレート制限（120 req/min）を守る RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、指定ステータスでリトライ）を実装。
    - 401 発生時は id_token を自動リフレッシュして再試行（1 回のみ）。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - JSON デコード検出・エラー処理、Retry-After ヘッダ考慮。
  - データ取得関数を実装
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存（冪等）関数を実装
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT（重複時更新）を用いた冪等保存
    - 型変換ユーティリティ (_to_float / _to_int)
    - PK 欠損行のスキップとログ出力

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集モジュールを追加。
    - デフォルトソース（Yahoo Finance ビジネス RSS）を含む。
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - 受信サイズ上限（10MB）によるメモリ DoS 対策。
    - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - SSRF 対策のため HTTP/HTTPS スキームのみ許可、ソケット/IP 検証など（設計指針）。
    - DB へのバルク挿入とチャンク処理を採用。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - 各関数は DuckDB を受け取り prices_daily / raw_financials のみ参照。
    - データ不足時の None ハンドリングを実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン (デフォルト [1,5,21]) の将来リターン計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数の丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装
    - research の calc_momentum / calc_volatility / calc_value を組み合わせて features を作成。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - 日付単位での置換（DELETE + INSERT）をトランザクションで行い冪等性を確保。
    - DuckDB 上の prices_daily を参照し、target_date 以前の最新価格を使用（ルックアヘッド回避）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を算出。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（AI）。
    - デフォルト重みと閾値を実装（DEFAULT_WEIGHTS、DEFAULT_THRESHOLD=0.60）。
    - ユーザー指定 weights の検証と正規化（合計が 1.0 に再スケール、無効値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合 BUY 抑制）。
    - BUY シグナル生成（threshold 超過かつ Bear でない場合）。
    - SELL シグナル（エグジット）生成ロジックを実装
      - ストップロス（終値/avg_price - 1 <= -8%）
      - final_score の閾値割れ
      - 価格欠損時の判定スキップ、features 未存在時は score=0 として扱う等の安全策
    - BUY / SELL を signals テーブルへ日付単位の置換（トランザクション内で DELETE + INSERT）。
    - 欠損コンポーネントは中立値 0.5 で補完して降格を防止。

### 変更 (Changed)
- 初期設計での安全性・冪等性を重視した実装方針を採用（.env 読み込みの保護、DuckDB への ON CONFLICT、トランザクションでの日付単位置換など）。
- API レート・エラーハンドリング方針を明文化（RateLimiter、指数バックオフ、Retry-After 優先）。

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（トレーリングストップ、時間決済など。positions テーブルに peak_price / entry_date が必要）。
- news_collector の具体的な SSRF/IP 検証や HTTP レスポンスの制限は設計に言及しているが、実装の詳細に依存する。実運用前の追加テストを推奨。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、大規模データでのパフォーマンス評価・チューニングが必要。
- execution / monitoring の具体的な発注・監視実装は未実装（execution パッケージは存在するが中身は空）。

---

貢献・バグ報告・要望は issue を作成してください。