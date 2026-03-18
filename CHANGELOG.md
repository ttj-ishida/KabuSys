# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog（https://keepachangelog.com/）に従って作成されています。

各リリースは semver に準拠しています。

## [Unreleased]
（現時点の開発中の変更はここに記載）

---

## [0.1.0] - 2026-03-18

最初の公開リリース。日本株自動売買システムの基盤となるモジュール群を追加しました。設計方針として、DuckDB を用いたデータ層、外部 API との堅牢なやり取り、研究（Research）用途の特徴量・統計ユーティリティ等を含みます。

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys.__init__` を追加（__version__ = "0.1.0"、公開 API: data, strategy, execution, monitoring）。
- 環境設定
  - `kabusys.config`:
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサ（export 形式対応、クォートとエスケープ対応、インラインコメント処理）。
    - protected/override ロジックを備えた .env 読み込み。
    - 必須環境変数取得ヘルパー `_require` と `Settings` クラス（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベルの検証プロパティ等）。
- データ取得 / 保存（J-Quants）
  - `kabusys.data.jquants_client`:
    - J-Quants API クライアント（ベース URL、ページネーション対応）。
    - 固定間隔レートリミッタ（120 req/min）によるスロットリング。
    - 再試行（指数バックオフ、最大 3 回、408/429/5xx 対象）と 401 時の自動トークンリフレッシュ（1 回のみ）。
    - fetch/save 関数：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存: ON CONFLICT）。
    - 入力データを安全に数値変換するユーティリティ `_to_float`, `_to_int`。
- ニュース収集
  - `kabusys.data.news_collector`:
    - RSS フィード取得と前処理（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
    - URL 正規化（utm_* 等トラッキングパラメータ削除）、ID 生成（正規化後 SHA-256 の先頭 32 文字）。
    - SSRF 対策: スキーム検証、プライベート IP / ループバック検出、リダイレクト先検証用ハンドラ。
    - レスポンスサイズ上限（10 MB）、gzip 解凍後のサイズ検査、defusedxml による安全な XML パース。
    - テキスト前処理（URL 除去・空白正規化）、銘柄コード抽出ユーティリティ（4 桁コード、既知銘柄フィルタ）。
    - DB へのバルク保存（チャンク化、トランザクション、INSERT ... RETURNING による新規件数取得）、news_symbols の一括保存。
- データスキーマ
  - `kabusys.data.schema`:
    - DuckDB 用 DDL 定義（Raw レイヤーのテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions 等のスキーマ定義）。
- 研究（Research）モジュール
  - `kabusys.research.feature_exploration`:
    - calc_forward_returns: DuckDB を用いた将来リターン計算（複数ホライズン、SQL LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（結合・欠損排除・最小サンプル検査）。
    - rank: 同順位は平均ランクを与えるランク関数（丸めで浮動小数点の ties 検出を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
  - `kabusys.research.factor_research`:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（ウィンドウ集計、データ不足時の None 処理）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true range の NULL 伝播制御、カウント条件）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（最新の過去財務レコードを取得）。
  - `kabusys.research.__init__` に主要ユーティリティを公開（calc_momentum 等）。
- その他ユーティリティ
  - 各所でログ出力（info/debug/warning）を追加し、処理状況・スキップ件数等を可視化。

### Security
- ニュース収集での SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
- defusedxml による XML パースで XML Bomb 等の攻撃を軽減。
- URL 正規化でトラッキングパラメータを削除し、ID の冪等性を改善。
- API クライアントでトークン管理と最小権限（キャッシュ・リフレッシュ）を実装。

### Performance
- J-Quants クライアントでのレート制限とページネーション処理。
- ニュースとシンボル紐付けでのチャンク化バルク挿入により DB オーバーヘッドを削減。
- DuckDB に対する集計処理を SQL ウィンドウで行い、効率化を図る。

### Reliability
- API リトライ（指数バックオフ）と HTTP ステータス別の再試行戦略。
- 401 発生時の安全なトークンリフレッシュ（無限ループ回避）。
- DB 操作はトランザクションで保護（失敗時はロールバック）。
- 入力不正や欠損値に対して安全にスキップ/None を返す実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes
- 本リリースは「基盤機能の実装」を目的としており、実際の発注/約定処理や監視 UI 等の上位モジュールは未実装または空のパッケージ境界を残しています（strategy, execution, monitoring の __init__ は存在）。
- 実行に必要な主要外部パッケージ: duckdb, defusedxml（README / requirements に追加推奨）。
- 環境変数の設定例は .env.example を参照する想定。必須環境変数を未設定でアクセスした場合は ValueError が発生します（settings の各プロパティで検査）。

---

今後の予定（例）
- Feature 層の永続化・定期バッチ化
- Strategy 実装と発注ワークフローの統合
- モニタリング用 DB / Slack 通知の実装強化
- 単体テスト・CI の整備

（注）本 CHANGELOG はコードの内容・コメント・設計ノートから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜修正してください。