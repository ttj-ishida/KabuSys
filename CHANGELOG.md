# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
安定版リリースはセマンティックバージョニングに従います。

最新変更
=========

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-18
------------------

最初の公開リリース。日本株自動売買システム KabuSys の主要コンポーネントの初期実装を含みます。

- Added
  - パッケージ初期化
    - src/kabusys/__init__.py
      - パッケージ名・バージョン定義（__version__ = "0.1.0"）。
      - 公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env/.env.local 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - .env の行解析ロジックを実装（export 形式・クォート・インラインコメント等の扱いに対応）。
      - 環境変数の取得ユーティリティ（必須キー未設定時に ValueError を送出）。
      - 設定オブジェクト Settings を提供（J-Quants トークン、kabu API、Slack、DB パス、環境名検証、ログレベル検証、is_live/is_paper/is_dev 等）。
  - Data 層: J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - J-Quants API からのデータ取得（株価日足、財務諸表、マーケットカレンダー）を行う fetch_* 関数群を実装。ページネーション対応。
      - 固定間隔の RateLimiter 実装（120 req/min を想定）とモジュールレベルキャッシュによる ID トークン共有。
      - HTTP リトライ実装（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
      - 401 の場合は ID トークンを自動リフレッシュして1回リトライする仕組みを実装（無限再帰を防止）。
      - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存。
      - 型変換ユーティリティ _to_float / _to_int（不正値の安全な扱い）。
  - Data 層: ニュース収集（RSS）
    - src/kabusys/data/news_collector.py
      - RSS フィード取得と記事保存ワークフローを実装（fetch_rss、save_raw_news、save_news_symbols、run_news_collection 等）。
      - セキュリティ対策:
        - defusedxml による XML パースで XML Bomb を防御。
        - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートIP/ループバックの検知とブロック、リダイレクトハンドラでの事前検証。
        - レスポンスサイズ上限(MAX_RESPONSE_BYTES = 10MB)、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - 冪等性・効率化:
        - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し重複を防止。
        - INSERT ... RETURNING を用いて実際に挿入された行を正確に取得。
        - 挿入をチャンク化し、1 トランザクションでコミット/ロールバック。
      - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字の検出と known_codes によるフィルタリング）。
      - テスト用フック: _urlopen をモックして差し替え可能な設計。
  - Data 層: DuckDB スキーマ定義
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution レイヤを想定したスキーマ定義の一部を実装（raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む）。
      - データ型・チェック制約（CHECK / PRIMARY KEY）を定義しデータ整合性を担保。
  - Research（特徴量・ファクター）
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns（単一クエリで複数ホライズンを取得、ホライズンの検証）。
      - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク算出で実装、欠損・ ties 対応）。
      - ランク付けユーティリティ rank（同順位の平均ランク、丸め誤差対策）。
      - ファクター統計サマリー factor_summary（count/mean/std/min/max/median、None 除外）。
      - 標準ライブラリのみで実装、DuckDB の prices_daily テーブル前提で本番 API に依存しない設計。
    - src/kabusys/research/factor_research.py
      - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）、ボラティリティ/流動性（atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（per, roe）計算関数を実装。
      - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照して値を計算。データ不足時は None を返す扱い。
      - ウィンドウ・スキャン範囲や NULL 伝播に配慮した SQL 実装（cnt による不足判定、true_range の NULL 制御等）。
    - src/kabusys/research/__init__.py
      - 主要な研究用関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - Execution / Strategy / Monitoring
    - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py は存在し、将来の実装のためのパッケージ用意。

- Changed
  - なし（初回リリース）

- Fixed
  - なし（初回リリース）

- Security
  - news_collector において SSRF・XML Bomb・Gzip Bomb・大容量レスポンス等に対する複数の防御を実装。

注記 / 実装上の設計方針
--------------------
- DuckDB を中心としたローカルデータレイク設計（raw / processed / feature レイヤ）を採用。データ保存は冪等性を重視（ON CONFLICT / RETURNING）。
- 外部 API 呼び出し（J-Quants、RSS）はレート制御・リトライ・認証リフレッシュ等を備えた安全なクライアント実装。
- 研究モジュールは本番の取引 API にアクセスしないことを明確にしており、リサーチ環境での安全性を重視。
- テスト容易性を意識した設計（環境ロードの抑止フラグ、_urlopen の差し替え、明確な副作用境界など）。

破壊的変更
---------
- なし

今後の予定（未実装・想定）
-------------------------
- Execution（発注・ポジション管理）と Strategy（モデル実装）の具体的な実装。
- Feature レイヤの追加カラム・ETL パイプラインの整備。
- 追加のデータソース対応（SNS、追加RSS、ニュース全文検索など）。
- 単体テスト・統合テストの充実および CI パイプラインの整備。

もし特定ファイル／機能についてより詳細な変更履歴（関数ごとの変更理由や設計トレードオフなど）をご希望であればお知らせください。