Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更を時系列で記録します。  
フォーマット: https://keepachangelog.com/ja/ を参照。

Unreleased
----------
- （なし）

[0.1.0] - 2026-03-20
-------------------
Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージエントリポイント: src/kabusys/__init__.py にて version と公開モジュールを定義。
- 環境設定・ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルと OS 環境変数からの設定自動読み込みを実装。
  - プロジェクトルート判定は .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env のパースは export 構文、クォート・エスケープ、インラインコメント等に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ユーティリティ（_require）と Settings クラスを提供。
  - 必須設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト値（DB パス等）を定義。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値チェック）。
- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レートリミッタ（120 req/min 固定間隔スロットリング）を実装し、API レート制限を尊重。
  - リトライロジック（指数バックオフ、最大3回）および 401 受信時の自動トークンリフレッシュを実装。
  - ID トークンのモジュール内キャッシュを実装（ページネーション間で共有）。
  - データ整形ユーティリティ（_to_float, _to_int）を実装。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE
  - 取得・保存時のログ出力・欠損 PK 行スキップの警告を行う。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集モジュールを実装（デフォルトに Yahoo Finance のビジネス RSS を追加）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）を実装。
  - defusedxml を使用した XML パース（XML Bomb 等の対策）、受信サイズ上限（10MB）や SSRF を意識した実装方針を採用。
  - 冪等保存（ON CONFLICT DO NOTHING）やバルク挿入のチャンク処理等、実運用を想定した設計。
- 研究用ファクター計算・探索（src/kabusys/research/*.py）
  - ファクター計算モジュール（factor_research.py）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe）を DuckDB 上で計算する関数を実装。
    - 期間バッファや欠損制御、NULL 伝播の注意点を考慮。
  - 特徴量探索モジュール（feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（calc_ic）
    - 基本統計サマリ（factor_summary）とランク変換ユーティリティ（rank）
  - research パッケージ API を __init__ でエクスポート。
- 戦略層（src/kabusys/strategy/*.py）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側で計算した生ファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへトランザクション単位で日付置換（冪等性）して保存。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - 各コンポーネントの欠損は中立値 0.5 で補完。
    - final_score を重み付き合算で計算、weights の検証と再スケール処理を実装（無効値はスキップ）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負でサンプル数閾値以上の場合）。
    - BUY（閾値 0.60）・SELL（ストップロス -8% / スコア低下） を判定し signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 保有ポジションの取得は positions テーブルの最新レコードを参照し、価格欠損時や features に存在しない場合の挙動を明確化。
- モジュール分割と型注釈
  - 多くの関数に型ヒント、詳細な docstring とロギングを追加し可読性と運用性を向上。

Changed
- （該当なし — 初期リリース）

Fixed
- （該当なし — 初期リリース）

Security
- news_collector で defusedxml を使用して XML 関連の脆弱性に対処。
- RSS/URL 正規化とトラッキングパラメータの除去、受信サイズ制限、HTTP スキーム検証等の防御策を記載。

Notes / Known limitations / TODO
- execution パッケージは存在する（ディレクトリ）ものの実装ファイルはまだ追加されていません（発注層は分離設計）。
- signal_generator のエグジット条件でトレーリングストップや時間決済（60 営業日超）等は未実装（positions テーブルに peak_price / entry_date 等が必要）。コード中に TODO コメントあり。
- news_collector の一部実装（RSS パース→NewsArticle 生成→DB 挿入の残り処理）はファイル末尾の続きが必要（このリリースではユーティリティと設計が実装済みで、実際の完全ワークフローは今後追加される可能性あり）。
- zscore_normalize の実装は kabusys.data.stats 側に依存（本コードベースでは外部に実装済みである想定）。
- J-Quants クライアントはネットワーク・API の仕様変化により挙動が変わる可能性があるため、本番運用前にエンドツーエンドの検証が必要。
- 必須環境変数が未設定の場合は Settings._require により ValueError が発生するため、デプロイ前に .env を準備すること。

アップグレード / 初回導入手順（簡易）
- .env.example を参考に .env を作成し、以下最低限の環境変数を設定:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- DuckDB / SQLite のデータベースパスはデフォルトで data/kabusys.duckdb / data/monitoring.db（必要に応じて DUCKDB_PATH/SQLITE_PATH を設定）。
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に同期。

もし特定のコミットログや追加の変更点を明示したい場合、あるいはリリースノートの別フォーマット（英語版など）を作成したい場合はお知らせください。