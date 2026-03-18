# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
安定版へのリリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

初回公開リリース。日本株の自動売買・データ基盤のプロトタイプ実装を含みます。

### Added
- パッケージ初期定義
  - kabusys パッケージを追加（src/kabusys/__init__.py）。
  - バージョン 0.1.0 を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動で読み込む機能を追加。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを実装:
    - export 形式対応、クォート処理、インラインコメントの取り扱い。
  - Settings クラスを追加し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env（development/paper_trading/live の検証）、log_level（ログレベル検証）および is_live / is_paper / is_dev ヘルパー
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。

- Data: J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（JSON デコード検証、ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライと指数バックオフ（408/429/5xx を対象、最大 3 回）、429 の場合は Retry-After を優先。
  - 401 Unauthorized を検出した場合のトークン自動リフレッシュ（1 回）と ID トークンのモジュールレベルキャッシュ。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存ユーティリティ（冪等性を考慮した ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ: _to_float, _to_int（堅牢な型変換）

- Data: ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事抽出の実装。
  - セキュリティ対策:
    - defusedxml による XML パース、安全なリダイレクトハンドラで SSRF 防止（スキーム検証、プライベートIP拒否）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去）、記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - 許可スキームは http/https のみ。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news：チャンク分割＋トランザクション、INSERT ... RETURNING で挿入された記事IDを返却。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄の紐付けを一括保存（チャンク、トランザクション、INSERT ... RETURNING）。
  - 銘柄抽出ロジック（4桁コード抽出と known_codes によるフィルタリング）。
  - run_news_collection：複数ソースの統合収集ジョブ（個別ソースごとにエラーハンドリング）。

- Data: DuckDB スキーマ初期化（src/kabusys/data/schema.py）
  - Raw Layer 用テーブル DDL（raw_prices, raw_financials, raw_news, raw_executions 等）の定義を追加。
  - スキーマ定義は DataSchema.md に基づく3層設計（Raw / Processed / Feature / Execution）の方針を注記。

- Research: ファクター計算・特徴量探索（src/kabusys/research/*）
  - feature_exploration.py:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括SQLで計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（検出された ties の平均ランク処理含む）。
    - rank: 同順位は平均ランクを与えるランク処理（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 設計: DuckDB の prices_daily テーブルのみ参照、標準ライブラリのみで実装。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率）を計算。
    - calc_volatility: atr_20（20日ATR）/atr_pct/avg_turnover/volume_ratio を計算。true range の NULL 伝播を考慮。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて per（PER）と roe を計算。
    - 各関数は DuckDB に対する SQL ウィンドウ関数を活用し、欠損・データ不足時の挙動（None）を明示。

- research パッケージ公開（src/kabusys/research/__init__.py）
  - 主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサ・HTTP クライアントに対して SSRF、XML Bomb、巨大応答による DoS を想定した保護を実装。
- J-Quants クライアントはトークンリフレッシュ処理とレート制御を備え、誤ったリクエストの繰り返しや認証切れでの無限再帰を防止。

### Notes / Design decisions
- Research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しており、DuckDB の SQL と標準ライブラリでの集計を行う設計。
- DuckDB への保存は冪等性を優先（ON CONFLICT を使用）。
- .env ローダは __file__ を基準にプロジェクトルートを探索するため、カレントワーキングディレクトリに依存しない。
- NewsCollector は記事 ID の生成・重複排除や銘柄紐付け工程を堅牢に行うため、チャンク分割やトランザクション運用を採用。

---

開発・運用中に以下の改善・追加が考えられます（今後の候補）:
- Strategy / Execution / Monitoring の実装（現在パッケージは空の __init__ のみ）。
- テストカバレッジと CI の整備（単体テスト / 結合テスト）。
- 高度なバックオフ戦略やメトリクス収集（監視用）。
- NewsCollector の自然言語処理（トピック分類や感情分析）や記事と銘柄関連性向上のための辞書拡張。

----