# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"、主要サブモジュールを __all__ に公開）

- 設定管理
  - 環境変数・.env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
    - export KEY=val、クォート（シングル/ダブル）やエスケープ、行内コメントの取り扱いに対応したパーサを実装。
    - OS 環境変数を保護する protected ロジック、.env.local による上書きサポート。
    - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定プロパティ等）。
    - 必須変数未設定時は _require() により ValueError を投げる。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）と 401 受信時の自動トークンリフレッシュ処理。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT を用いた upsert）。
    - 型変換ユーティリティ（_to_float / _to_int）を提供。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスのトレーサビリティを確保。

- ニュース収集
  - RSS ベースのニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリ RSS）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事 ID = SHA-256 ハッシュ先頭部による冪等性確保。
    - XML パースに defusedxml を使用して XML-Bomb 等の攻撃対策。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF/不正スキームの防止、バルク INSERT のチャンク化による DB 負荷抑制。
    - raw_news / news_symbols への保存ワークフローを想定した設計。

- リサーチ（研究用）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）、Value（per / roe）などのファクター計算を実装。
    - DuckDB の prices_daily / raw_financials を用いた SQL + Python 実装。
    - データ不足（必要行数未満）の扱いやスキャン範囲バッファを含む堅牢な実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、引数の検証）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのρ に相当）、ランク変換ユーティリティ rank。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - research/__init__.py で主要関数群を公開。

- 戦略（strategy）モジュール
  - feature_engineering（src/kabusys/strategy/feature_engineering.py）
    - research の raw ファクターを統合して features テーブルへ保存する処理（ユニバースフィルタ、Z スコア正規化、±3 でクリップ、日付単位の置換（DELETE + INSERT）による冪等性）。
    - ユニバースフィルタ（最小株価・最小 20 日平均売買代金）を実装。
  - signal_generator（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存する処理を実装。
    - デフォルト重み・閾値（デフォルト重みは momentum 0.4 等、閾値は 0.60）を提供。ユーザー指定 weights の検証・補完・再スケール処理あり。
    - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）、シグモイド変換、欠損値は中立 0.5 で補完するロジック。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合に BUY を抑制）。
    - エグジット判定（STOP-LOSS -8% / final_score が閾値未満）を実装。未実装の追加エグジット条件（トレーリングストップ、時間決済）はコード内ドキュメントで明示。
    - signals テーブルへの日付単位置換をトランザクションで実施（ROLLBACK 処理とログ出力あり）。
  - strategy/__init__.py で build_features / generate_signals を公開。

- データ統計ユーティリティ
  - zscore_normalize を参照して使う設計（kabusys.data.stats から提供される想定）。

- トランザクション性・堅牢性
  - 主要な DB 書き込み処理で BEGIN/COMMIT/ROLLBACK による原子性を確保し、失敗時には警告ログを出力してロールバック失敗にも対処。

- ロギング・警告
  - 各モジュールで適切な logger を使用し、異常系やスキップした行数などを警告出力するように実装。

### Security
- ニュース取得で defusedxml を使用して XML 関連の攻撃に対抗。
- RSS の URL 正規化・トラッキングパラメータ除去、受信サイズ上限、HTTP スキーム検証などで SSRF/メモリ DoS のリスクを低減。
- J-Quants クライアントで Authorization トークンの取り扱いを明示し、トークンリフレッシュ時の再試行ロジックに注意を払う。

### Notes / Known limitations
- execution パッケージ（src/kabusys/execution）は空のプレースホルダが含まれており、注文実行層は本リリースで直接の実装依存を持たない（戦略層は発注 API に依存しない設計）。
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は未実装（positions テーブルに peak_price / entry_date などの追加情報が必要）。
- 一部の設計・パラメータ（閾値・重み・フィルタ基準等）は StrategyModel.md / DataPlatform.md 等の外部ドキュメントに依存する想定。将来的なチューニング・変更により互換性が変わる可能性あり。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

（補足）本 CHANGELOG はコードベースから推測して記載しています。実際のリリースノート作成時は変更履歴・コミットログ・設計ドキュメントを参照して内容を調整してください。