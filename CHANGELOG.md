# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-20

### Added
- 初回リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
- パッケージ全体
  - パッケージ初期化情報 (src/kabusys/__init__.py) とバージョンを追加（0.1.0）。
  - モジュール公開インターフェースを整理（data, strategy, execution, monitoring）。
- 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数からの設定自動読み込みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数の保護（OS 環境変数を protected として .env.local で上書きされないようにする）。
  - settings オブジェクトを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを公開。値検証（有効値チェック・必須チェック）を実装。
- Data 層 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出し用の汎用リクエスト関数を実装。固定間隔のレートリミット（120 req/min）を RateLimiter で管理。
    - リトライ戦略（指数バックオフ、最大試行回数、408/429/5xx の再試行）を導入。429 の場合は Retry-After ヘッダを尊重。
    - 401 応答時の自動トークンリフレッシュ処理（1 回リフレッシュして再試行）とモジュールレベルのトークンキャッシュを実装。
    - ページネーション対応でデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による冪等保存、PK欠損行のスキップとログ出力、fetched_at の UTC タイムスタンプ記録。
    - 型変換ユーティリティ（_to_float, _to_int）で安全に数値へ変換。
  - ニュース収集 (news_collector.py)
    - RSS フィードから記事を収集して raw_news に保存する処理を実装。
    - URL 正規化（スキームとホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を使った安全な XML 解析、受信サイズ上限（MAX_RESPONSE_BYTES）などメモリ DoS 対策、SQL のバルク挿入チャンク化を実装。
- Research 層 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum, Volatility, Value 等の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
    - SQL ウィンドウ関数と移動ウィンドウを用いて mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per/roe 等を算出。
    - データ不足時の None 扱い、営業日ベースのスキャン範囲バッファ考慮。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）：複数ホライズンのリターンを一括取得するクエリを実装。horizons の検証を行う。
    - IC（Information Coefficient）計算（calc_ic）：factor と forward を code で結合して Spearman の ρ（ランク相関）を算出する実装。
    - ランク変換ユーティリティ（rank）とファクター統計サマリ（factor_summary）を提供。
  - research パッケージの __all__ を整備。
- Strategy 層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - 研究環境の生ファクターを取得し、ユニバースフィルタ（最低株価・最低売買代金）を適用、Z スコア正規化（kabusys.data.stats.zscore_normalize 利用）・±3 でクリップし features テーブルへ UPSERT（日付単位の置換）する処理を実装。
    - DuckDB トランザクションによる削除→挿入で原子性を保証。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算、重み付き合算で final_score を算出。
    - デフォルト重みとしきい値（threshold）を提供。ユーザー指定 weights の妥当性検証と合計スケーリング処理を実装。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - エグジット（SELL）ロジック：ストップロス（-8% 以下）とスコア低下による SELL 判定を実装。保有銘柄の最新価格欠損時の判定スキップや features 未登録銘柄の扱いを明確化。
    - signals テーブルへの日付単位置換をトランザクションで保証（BUY / SELL の挿入）。
  - strategy パッケージの __all__ を整備。

### Fixed / Robustness
- 環境変数読み込み処理の堅牢化
  - .env のクォート内エスケープ、行中コメントの扱い、export プレフィックスに対応。キー空白や不正行のスキップを実装。
  - .env の読み込み失敗時に warnings を発行して処理継続。
- J-Quants クライアントの堅牢化
  - JSON デコード失敗時にわかりやすいエラーを投げる実装。
  - ネットワーク/HTTP エラーに対するリトライの適用範囲を明示。
  - ページネーションでループ検知（pagination_key の重複チェック）を導入して無限ループを防止。
- DuckDB 保存処理
  - PK 欠損レコードをスキップしてログ出力、挿入済み件数を返すようにした。
  - save_* 関数は空レコード時に 0 を返す。
- Signal / Feature ロジックの安全化
  - 欠損値・非有限値（NaN/Inf）に対するガードを追加し、平均やシグモイド計算での例外を防止。
  - 重みのユーザー入力検証で不正値をスキップし、合計が 0 の場合はデフォルトにフォールバック。

### Security
- news_collector における XML 解析で defusedxml を利用し XML-Bomb 等の攻撃を緩和。
- RSS / URL 正規化でトラッキングパラメータを除去。設計上、HTTP/HTTPS スキーム以外や SSRF 対策（IP/ホスト検証）を念頭に置いた実装方針を採用（実装の一部は明示的な検証処理を含む）。
- ネットワーク受信サイズ上限の導入（MAX_RESPONSE_BYTES）によりメモリ型 DoS を軽減。

### Notes / Design
- 多くのモジュールは外部通信や本番発注層（execution）へ直接依存しない設計（ルックアヘッドバイアス回避、研究環境と本番の分離）。
- DuckDB を主なストレージとして使用し、日付単位の置換（DELETE → INSERT）をトランザクショナルに行うことで冪等性と原子性を確保。
- ドメイン仕様（StrategyModel.md, DataPlatform.md 等）に基づく設計方針を明記・順守。
- execution パッケージはプレースホルダ（空）として用意。

---

今後の予定（未実装 / TODO）
- execution 層: 発注 API 統合（kabuステーション/証券会社 API）と注文管理の実装。
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済等）: positions テーブルの peak_price / entry_date を利用可能にする必要あり。
- news_collector の外部 URL 検証強化（IP ブラックリスト/ホワイトリスト、ソケット接続チェック等）の追加。
- 単体テスト・統合テストの拡充と CI ワークフローの整備。

（注）本 CHANGELOG はリポジトリ内のソースコードからの推測に基づいて作成しています。実際のリリースノート作成時はコミット履歴・issue 等を参照してください。