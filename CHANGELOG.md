# Changelog

すべての注記は Keep a Changelog の形式に従います。日付はリリース日を示します。

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム「KabuSys」のコアモジュールを実装しました。以下はコードベースから推測される主要な追加・設計方針・注意点の要約です。

### 追加
- パッケージ基盤
  - パッケージメタ情報（src/kabusys/__init__.py）を追加。エクスポート対象: data, strategy, execution, monitoring。
  - バージョン: 0.1.0

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイル・環境変数からの設定読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。
  - .env パーサは `export KEY=VAL` 形式、シングル／ダブルクォート内のエスケープ、インラインコメントの取り扱い等に対応。
  - 環境変数の上書き制御（override）と「保護キーセット（protected）」をサポートし、OS 環境変数を保護。
  - Settings クラスを提供（settings オブジェクト）。
    - J-Quants / kabu API / Slack / DB パス等の取得プロパティを用意。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の入力検証。
    - デフォルトの DB パス（DuckDB, SQLite）や API ベース URL のデフォルト値を設定。

- データ取得/保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - レート制御（120 req/min 固定間隔スロットリング）。
    - 自動リトライ（指数バックオフ）とステータスコードに基づく再試行、429 の Retry-After の尊重。
    - 401 発生時にはリフレッシュトークンからの id_token 再取得を 1 回行って再試行する実装。
    - ページネーション対応で全ページ取得。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT による冪等なアップサート。
    - データ型変換ユーティリティ（_to_float / _to_int）を実装（不正値は None とする）。
    - データ取得時に fetched_at を UTC で記録し、look-ahead バイアスのトレースを可能にする設計。

  - ニュース収集（news_collector.py）
    - RSS フィードからの記事収集と前処理（URL 正規化、トラッキングパラメータ除去、空白正規化等）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用い、冪等性を確保。
    - defusedxml を用いた XML パースによるセキュリティ対策（XML Bomb 等）。
    - レスポンス受信サイズ上限（10MB）や SSRF 対策の考慮（URL の扱いに対する安全策が想定される）。
    - raw_news への冪等保存（ON CONFLICT / DO NOTHING 想定）と銘柄紐付け用の機能を想定。
    - バルク INSERT のチャンク化で DB パラメータ上限対策。

- リサーチ（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高指標）、Value（PER / ROE）等の計算関数を実装。
    - DuckDB のウィンドウ関数を活用した実装。データ不足時の None ハンドリング。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman の ρ）やファクター統計サマリー（factor_summary）、rank 関数を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結。

- 戦略（src/kabusys/strategy/）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research が算出した raw factor を合成・正規化（Z スコア正規化）して features テーブルへ UPSERT（ターゲット日単位で削除→挿入＝日付単位置換）する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコアを ±3 でクリップして外れ値影響を抑制。
    - トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を保証。

  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存する generate_signals を実装。
    - スコア合成はモメンタム / バリュー / ボラティリティ / 流動性 / ニュース（AI）に対する重み付け（デフォルト値を定義）。ユーザー指定 weights の検証と正規化（合計 1 に再スケーリング）を実施。
    - sigmoide 変換、欠損補完（中立値 0.5）、ランク付け、BUY 閾値（デフォルト 0.60）等を実装。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）により BUY を抑制。
    - エグジット判定（_generate_sell_signals）にてストップロス（-8%）・スコア低下判定を実装。価格欠損時の SELL 判定スキップや保有銘柄未評価時のデフォルト動作を明確化。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）やトランザクションによる原子性を実装。
    - 未実装のエグジット（トレーリングストップ、時間決済）はコード中に TODO として記載。

- 研究 API エクスポート（src/kabusys/research/__init__.py）
  - 研究用途の関数群（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### 変更
- （初版のため該当なし）設計文書（コメント / docstring）に StrategyModel.md / DataPlatform.md 等の参照があり、実装はそれらの仕様に準拠するよう設計されています。

### 修正（堅牢性/安全性向上）
- .env パーサの改善: export プレフィックス・クォート内のエスケープ・インラインコメント処理に対応し、テストしやすく CWD に依存しないプロジェクトルート探索を実装。
- J-Quants クライアント: レート制御・リトライ・401 自動刷新などの堅牢な HTTP 周りの制御を実装。
- News collector: defusedxml による安全な XML パース、受信サイズ制限など DoS/セキュリティ対策を導入。

### 既知の制限 / 注意点
- execution / monitoring モジュールの実体は含まれていない（__all__ に名前はあるが実装ファイルは空/未着手）。
- 一部エグジット条件（トレーリングストップ、時間決済）は未実装（コード内コメントあり）。
- news_collector の SSRF/ホスト検査等の詳細実装はドキュメント化されているが、抜粋には全実装が含まれていない可能性がある（安全設計は意図されている）。
- _to_int は小数を持つ文字列（"1.9" 等）の場合 None を返し、不正な切り捨てを防ぐ仕様。
- settings.jquants_refresh_token / KABU_API_PASSWORD / SLACK_* 等は必須環境変数として未設定時に ValueError を発生させる（運用前に .env を整備してください）。

### セキュリティ
- XML パースに defusedxml を使用し、RSS パースに対する既知の攻撃ベクトルに対処。
- ニュース URL の正規化でトラッキングパラメータを除去し ID を生成、重複を抑止。
- J-Quants クライアントはトークン管理・エラーハンドリングを備え、429/Retry-After を尊重することで API 利用制限に安全に対処。

---

今後の予定（想定／ドキュメント化された TODO）
- execution 層（実際の発注ロジック）の実装と kabu ステーション API 連携。
- monitoring 周り（アラート、Slack 通知等）の実装。
- news_collector の詳細な SSRF 対策の実装と追加ソース対応。
- 戦略のパラメータ調整、バックテスト結果に基づく改善。

---
作成にあたってはコード中の docstring / コメント・関数名・定数・トランザクション処理・ログ出力等から実装意図を推定して記載しました。追加情報やリリースノートの変更希望があれば教えてください。