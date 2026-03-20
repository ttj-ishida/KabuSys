# CHANGELOG

すべての注目すべき変更履歴をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

以下はリポジトリ内の現行コードベースから推測して作成した初回リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として追加し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよびOS環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env 自動ロードの制御（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）を追加。
  - .env パーサを実装：export KEY= 形式、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント処理などをサポート。
  - .env の読み込み優先順位：OS 環境 > .env.local（上書き） > .env（未設定のみ）。
  - 設定値のバリデーション（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証）と便利プロパティ（is_live / is_paper / is_dev）を追加。
  - 各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）取得ヘルパーを追加。
  - データベースパス（duckdb, sqlite）を Path 型で返すユーティリティを追加。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント (jquants_client)
    - API 呼び出しユーティリティを実装（固定間隔のレートリミッタを導入、デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）を実装。
    - 401 応答時はリフレッシュトークンで自動的に ID トークンを更新して再試行（1 回だけ）。
    - ページネーション対応のフェッチ関数を用意：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存ユーティリティを追加：save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - データ型変換ユーティリティ（_to_float, _to_int）を実装して不正値を安全に処理。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスのトレーサビリティを担保。
  - ニュース収集モジュール (news_collector)
    - RSS フィードから記事を取得して raw_news に保存する機能を追加。
    - URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント除去、スキーム/ホスト小文字化）を実装。
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を利用した XML パースで XML ボム等の攻撃を防止。
    - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を軽減。
    - INSERT をバルク化してチャンク毎に実行（チャンクサイズ上限設定）し、DB への負荷を低減。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を登録。

- 研究用モジュール（kabusys.research）
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高変化率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装。
    - 各関数は date, code をキーとした dict のリストを返す設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、営業日ベース）、IC（calc_ic：Spearman の ρ）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - Pandas 等に依存せず標準ライブラリ + DuckDB で動作する設計。

- 戦略ロジック（kabusys.strategy）
  - 特徴量エンジニアリング (feature_engineering)
    - research 層の raw ファクターを取得し、ユニバースフィルタ（最低株価、最低平均売買代金）を適用。
    - 指定列の Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 のクリッピングを実施。
    - features テーブルへの日付単位 UPSERT（トランザクションで置換）を導入し、処理を冪等化。
  - シグナル生成 (signal_generator)
    - features と ai_scores を統合し、コンポーネント（momentum / value / volatility / liquidity / news）ごとのスコアを計算。
    - シグナル統合ロジック（デフォルト重み、閾値）を実装し final_score を算出。
    - Bear レジーム検出（AI の regime_score 平均が負のとき）による BUY 抑制を実装。
    - BUY/SELL シグナルの生成と signals テーブルへの日付単位置換（トランザクション＋バルク挿入）を実装。
    - SELL（エグジット）判定にストップロス（終値が avg_price に対して -8% 以下）とスコア低下を実装。
    - 重みの入力検証・正規化・再スケールを行い不正な重みを無視する設計。

- DB/トランザクション運用
  - features / signals などのテーブル操作は「日付単位で削除して再挿入」のパターンを採用し、トランザクション + バルク挿入で原子性を保証。

- ロギング
  - 各モジュールで詳細なログ出力を追加（情報・警告・デバッグを適切に使用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用し XML 関連攻撃を軽減。
- ニュース取得時の受信バイト数上限を導入しメモリ DoS を抑制。
- J-Quants クライアントはトークン管理と自動リフレッシュを実装（401処理の明示的制御により無限再帰を回避）。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を導入。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Known limitations
- execution パッケージは空の初期プレースホルダとして存在します。実際の発注ロジック（kabuapi との連携）は本バージョンでは実装されていません。
- signal_generator のエグジット条件ではトレーリングストップや時間決済（保有 60 営業日超）などは未実装。これらは positions テーブルに peak_price / entry_date といった追加情報が必要になります。
- news_collector の SSRF / IP レゾリューション制御の詳細実装は（コード断片から）意図が見られますが、外部環境依存の挙動については運用時に追加レビューが必要です。
- 一部ユーティリティ（例: zscore_normalize）は別モジュール（kabusys.data.stats）に依存しており、そちらの実装が前提となります。

---

このCHANGELOGは現在のコードから推測して作成したものであり、実際のコミット履歴や設計ドキュメントに基づく正式な履歴とは異なる場合があります。必要であれば、各モジュールごとにさらに詳細な変更点（関数シグネチャ、例外動作、入出力フォーマット）を追記します。