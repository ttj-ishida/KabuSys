# Changelog

すべての変更は Keep a Changelog の形式に従い、重大度に応じて分類しています。バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

全般的な注意
- 本リリースはパッケージ初期版（0.1.0）相当の機能群を実装したものと推定しています。
- 多くの機能は DuckDB の既存スキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar など）を前提としています。スキーマの準備が必要です。
- 設計ドキュメント（StrategyModel.md、DataPlatform.md、Research 設計メモ等）に基づく実装方針・注記が各モジュールに含まれています。

Unreleased
- なし

[0.1.0] - 2026-03-20
================================

Added
- パッケージ基盤
  - パッケージ初期化情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - モジュール群を公開: data, strategy, execution, monitoring（execution は空のプレースホルダ）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env 自動ロードの優先順位を実装: OS 環境 > .env.local > .env。
  - 自動ロード無効化フラグを追加: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 行パーサを実装（export prefix の対応、シングル／ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - 環境変数保護（protected set）を考慮した override 挙動を実装。
  - Settings クラスを追加し、J-Quants / kabu / Slack / DB パス / env/log_level 判定等のプロパティを提供。検証（有効値チェック）を含む。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（トークン取得、API 呼び出し、ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットル _RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 時に自動で ID トークンをリフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - fetch_* 系 API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。いずれも冪等（ON CONFLICT / DO UPDATE）で保存。
  - JSON デコード失敗や PK 欠損行のスキップ、ログ出力を考慮。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集ロジックを実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - XML パースに defusedxml を使用して安全性を強化（XML Bomb 等の防御）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や HTTP スキーム制限等で DoS / SSRF リスク低減措置を反映。
  - トラッキングパラメータ除去、URL 正規化、テキスト前処理、バルク INSERT チャンク処理を実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュールを実装（calc_momentum / calc_volatility / calc_value）。
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 の行数チェックでデータ不足は None）。
    - Volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（TRUE RANGE の NULL 伝播を制御）。
    - Value: per / roe（raw_financials の最新レコードを target_date 以前で取得）。
  - 研究用ユーティリティを実装（calc_forward_returns: 指定ホライズンの将来リターンを一括取得、デフォルト [1,5,21]）。
  - IC 計算（calc_ic: Spearman の rho をランク計算で実装）、rank / factor_summary（count/mean/std/min/max/median）を実装。
  - 外部ライブラリに依存せずに標準ライブラリ + DuckDB で実行できる設計。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで算出した生ファクタをマージし、ユニバースフィルタ・Zスコア正規化を行い features テーブルへ UPSERT（テーブル単位で日付の置換を行い冪等化）。
  - ユニバースフィルタ: 最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8（5 億円）。
  - 正規化対象カラムを指定し、Z スコアを ±3 でクリップして外れ値を抑制。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換保存（冪等）。
  - スコア合成のデフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー提供の weights は検証・補完・再スケールされる。
  - BUY閾値のデフォルトを 0.60 に設定（_DEFAULT_THRESHOLD）。
  - コンポーネントスコア計算:
    - momentum: momentum_20 / momentum_60 / ma200_dev をシグモイド→平均化
    - value: per を 1/(1 + per/20) で変換（PER が 0/欠損/非有限なら None）
    - volatility: atr_pct の Z スコアを反転してシグモイド
    - liquidity: volume_ratio にシグモイド
    - news: ai_score をシグモイド（未登録は中立値で補完）
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）で BUY シグナルを抑制。
  - エグジット判定（SELL）実装:
    - ストップロス: (close / avg_price - 1) < -8% を優先判定
    - スコア低下: final_score が threshold 未満
  - SELL 対象は BUY から除外し、ランクを振り直す（SELL 優先ポリシー）。
  - トランザクションで原子性を担保。

Changed
- ロギング & エラー挙動
  - 各種モジュールで適切な logger 呼び出しを追加（info/warning/debug）し、失敗時に詳細を出すようにした。
  - DuckDB トランザクションで ROLLBACK が失敗した場合の警告ログを追加。

Fixed
- データ型変換ユーティリティ
  - jquants_client の _to_float / _to_int を強化し、不適切な文字列や小数誤変換を安全に None に落とす挙動を保証。

Security
- XML パースに defusedxml を利用して XML による攻撃（XML Bomb など）を軽減。
- news_collector で受信サイズ制限やスキーム検査（http/https のみ許可）を導入し、SSRF / メモリ DoS を軽減。
- J-Quants のトークンは明示的にキャッシュし、401 発生時のリフレッシュを最小化することで不要なリフレッシュを抑制。

Known issues / TODO
- signal_generator のエグジット条件で記載されている一部条件は未実装:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- execution / monitoring 層（発注ロジックや監視ロジック）は本実装に依存しない設計だが、実際の発注連携実装は含まれていない（execution パッケージはまだ空）。
- DuckDB のテーブルスキーマは本実装側で作成しないため、利用前にスキーマ定義を用意する必要がある。
- AI スコア（ai_scores）の生成・更新ルートは本パッケージに含まれていないため、外部プロセスで ai_scores を投入する想定。

Breaking Changes
- なし（初期リリース相当）。

Notes for operators / integrators
- 環境変数必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- KABUSYS_ENV は development / paper_trading / live のいずれかでなければならない（判定は Settings.env）。

開発者向け補足
- 多くの関数は外部副作用を最小化する設計（DuckDB 接続や設定を引数 / Settings から取得）となっており、ユニットテストでモック可能です。
- research モジュールは外部依存を避けるため pandas 等を使わず標準ライブラリ実装になっています。

もし、追加で以下の情報が必要であれば教えてください:
- 各関数についてのサンプル使用例（コード片）
- 想定する DuckDB スキーマ定義（テーブル CREATE 文）
- 未実装機能の優先度付けと設計提案