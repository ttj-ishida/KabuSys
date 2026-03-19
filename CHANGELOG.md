# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定モジュール
  - src/kabusys/config.py
    - .env ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み順序: OS 環境 > .env.local（override=True）> .env（override=False）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装（export 形式対応、クォート/エスケープ、インラインコメント処理）。
    - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等のプロパティ）。
    - 環境変数検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須値チェック（_require）。

- データ取得・永続化（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（ページネーション対応）。
    - API レート制限制御（固定間隔スロットリング、120 req/min）。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 を検知した場合の自動トークンリフレッシュ（1 回のみ）とキャッシュ機構。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）：
      - PK 欠損行をスキップし警告を出力。
      - ON CONFLICT DO UPDATE による冪等な保存。
    - レスポンスパース用ユーティリティ _to_float / _to_int。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news へ保存する処理（冪等）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、スキーム/ホスト小文字化）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - セキュリティ対策: defusedxml による XML パース、安全でないスキームの拒否、受信バイト数上限（10MB）によるメモリ DoS 防止、SSRF を意識した処理。
    - バルク INSERT チャンク化による性能制御。

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等のファクター計算実装（prices_daily / raw_financials を参照）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 行未満は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR 算出は欠損制御付き）。
    - calc_value: per（EPS が 0 または欠損時 None）、roe（最新開示をマージ）。
    - DuckDB による SQL ベースの実装で、外部 API に依存しない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（1 クエリで取得、範囲バッファあり）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外、サンプル不足時は None）。
    - rank / factor_summary: tie 処理（平均ランク）や基本統計量（count/mean/std/min/max/median）を計算。
    - すべて標準ライブラリ + duckdb ベースで外部依存を避ける方針。

- 戦略（strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを取り込み、ユニバースフィルタ適用、Z スコア正規化、±3 でクリップして features テーブルへ UPSERT。
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円を採用。
    - DuckDB トランザクションで日付単位の置換（DELETE -> INSERT、冪等）。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成、signals テーブルへ書き込む（冪等）。
    - デフォルト重み、閾値（0.60）といった StrategyModel に基づく実装。
    - AI ニューススコアを補完、欠損コンポーネントは中立 0.5 で代替して不当な降格を防止。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY を抑制。
    - SELL 生成ロジック: ストップロス（-8%）とスコア低下（threshold 未満）。不足データ時の挙動（価格欠損時は SELL 判定をスキップ）を明記。
    - weights の検証・正規化（未知キー・負値・NaN/Inf を無視、合計が 1.0 に再スケール）。
    - signals 書き込みもトランザクションで日付単位の置換を行い原子性を保証。

- データ統計ユーティリティ
  - src/kabusys/data/stats の zscore_normalize を研究/戦略で利用可能に統合（__all__ 経由で exposure）。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py と src/kabusys/research/__init__.py にて主要関数をエクスポート（build_features, generate_signals, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, rank, factor_summary, zscore_normalize など）。

### Known limitations / Notes
- 未実装のエグジット条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）や時間決済（保有 60 営業日超）等は未実装。
- calc_value: PBR や 配当利回りは本バージョンでは未実装。
- 一部ロジックは positions / ai_scores / features / prices_daily / raw_* 等の DB スキーマ存在を前提とする（テーブル定義は別途必要）。
- news_collector の記事 ID は URL 正規化に依存するため、URL 正規化ルールの変更は冪等性に影響する可能性がある。
- 外部 HTTP 呼び出し（J-Quants, RSS）に関してはネットワーク・認証エラーに対する再試行や保護があるが、厳密な SLA は保証しない。

### Security
- news_collector は defusedxml を使用し XML 攻撃を軽減。
- RSS URL のスキーム検査や受信バイト数制限を実装して SSRF / DoS リスクを低減。
- J-Quants クライアントは認証トークン処理と自動リフレッシュを行い、機密トークンは Settings 経由で環境変数として管理。

---

今後の予定（検討中）
- positions テーブルの拡張（peak_price, entry_date）に伴うトレーリングストップ実装。
- AI スコアの算出パイプラインと news -> ai_scores 連携の実装。
- 単体テスト・統合テストの追加、CI パイプライン整備。
- PBR / 配当利回り等のバリューファクター追加。

もし他に CHANGELOG に含めたい詳細（例: リリース日付の修正、担当者、コミット参照など）があればお知らせください。