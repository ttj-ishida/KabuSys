# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています: https://semver.org/

## [Unreleased]

### Added
- ドキュメント化された初期設計・実装のコードベースを追加（初期リリース準備）。
- パッケージメタ情報:
  - kabusys パッケージ初期版（__version__ = 0.1.0）。
  - __all__ に data / strategy / execution / monitoring を公開。
- 環境設定管理モジュール（kabusys.config）を追加:
  - .env/.env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応。
  - .env パーサーは export プレフィックス、クォート文字列、行内コメント処理、エスケープをサポート。
  - 上書き動作（override）と protected（OS 環境変数保護）を実装。
  - Settings クラスで主要設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DB パス、実行環境、ログレベル等）。
  - KABUSYS_ENV の検証（development/paper_trading/live）と LOG_LEVEL の検証。
- データ取得・保存関連（kabusys.data）を追加:
  - J-Quants クライアント（kabusys.data.jquants_client）:
    - 固定間隔のレートリミッタ（120 req/min）。
    - 冪等的な DuckDB 保存関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT/UPSERT）。
    - ページネーション対応の fetch 関数（daily_quotes, financial_statements, market_calendar）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）、429 の Retry-After を尊重。
    - 401 受信時にリフレッシュトークンからの id_token 自動更新を 1 回だけ行う処理。
    - レスポンスパース・型変換ユーティリティ（_to_int/_to_float）。
    - fetched_at を UTC ISO 文字列で記録（look-ahead bias 対策）。
  - ニュース収集モジュール（kabusys.data.news_collector）:
    - RSS フィードから記事収集して raw_news に冪等保存する処理設計。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、クエリソート、フラグメント削除）。
    - セキュリティ考慮: defusedxml 利用、受信サイズ上限（10MB）、HTTP(S) スキーム検証、SSRF/XML Bomb 対策。
    - デフォルト RSS ソース定義（例: Yahoo Finance）。
    - バルク挿入のチャンク化（デフォルト 1000 件）で DB への負荷を制御。
- リサーチ（研究）モジュール（kabusys.research）を追加:
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20、atr_pct）、20 日平均売買代金・出来高比率を計算。true_range の NULL 処理に注意。
    - calc_value: 最新の raw_financials を参照して PER / ROE を計算（EPS が 0 の場合は None）。
    - DuckDB のウィンドウ関数を活用した高効率実装。営業日欠損への耐性を考慮。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（同順位は平均ランク扱い、最小サンプル数チェック）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank ユーティリティ（同順位の平均ランク化、丸めによる ties 対応）。
  - zscore_normalize をデータ層（kabusys.data.stats から）と連携して利用可能にするエクスポートを追加。
- 戦略モジュール（kabusys.strategy）を追加:
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - research の calc_* 出力をマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化対象カラムの Z スコア正規化（±3 でクリップ）を適用して features テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - 冪等設計（対象 date を削除して再挿入）。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネント変換: Z スコア → シグモイド、PER → 値スコア、atr_pct の反転などを実装。
    - デフォルト重みを定義（momentum:0.4, value:0.2, volatility:0.15, liquidity:0.15, news:0.1）と閾値（BUY 閾値 0.60）。
    - 重みのバリデーションとリスケール（合計が 1 でない場合に正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。
    - BUY シグナルの生成（Bear 時は抑制）、SELL シグナル生成（ストップロス -8% / final_score が閾値未満）。
    - positions, prices_daily, ai_scores を参照し signals テーブルへ日付単位の置換（トランザクションで原子性）。
    - SELL が優先されるポリシー（SELL 対象を BUY から除外してランクを再付与）。
- パッケージのエクスポートを整備（kabusys.research/__init__.py, kabusys.strategy/__init__.py など）。

### Changed
- n/a（初期追加のため変更履歴はなし）。

### Fixed
- n/a（初期追加のため修正履歴はなし）。

### Security
- news_collector で defusedxml を使用し XML 攻撃対策を実施。
- RSS 受信にサイズ上限を設けメモリ DoS 対策を実装。
- J-Quants クライアントで認証トークンの自動更新と慎重な再試行ロジックを導入（無限再帰回避のため allow_refresh フラグを利用）。

---

## [0.1.0] - 2026-03-21

初回公開リリース。上記の機能群をパッケージとしてまとめて公開。

- 主要機能:
  - 環境設定管理 (.env 自動読み込み、Settings)
  - データ収集・保存 (J-Quants クライアント、raw_prices/raw_financials/market_calendar 保存、ニュース収集)
  - リサーチ機能 (ファクター計算: momentum/volatility/value、forward returns、IC、summary)
  - 特徴量作成（正規化・ユニバースフィルタ）とシグナル生成（BUY/SELL）
  - DuckDB を用いたデータ処理フロー
  - ロギング、本番/ペーパー/開発環境の判定、設定バリデーション

- 既知の制限 / TODO:
  - signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で未実装。
  - news_collector の RSS パース／言語処理（ステミング、分かち書き等）は未実装。外部 NLP 処理は将来検討。
  - execution 層（実際の発注ロジック）と monitoring モジュールの実装は今後追加予定（パッケージ階層は準備済み）。
  - テストカバレッジ・エンドツーエンドの統合テストは今後整備予定。

- 注意事項:
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトの DuckDB/SQLite パスは data/kabusys.duckdb / data/monitoring.db。必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH で上書き可能。

---

過去のリリースについては今後このファイルに追記していきます。もし追記・修正すべき点があればお知らせください。