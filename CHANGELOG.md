# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。  
現在のパッケージバージョンは src/kabusys/__init__.py に基づき 0.1.0 です。

---

## [Unreleased]

- なし

---

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加点は以下の通りです。

### 追加
- パッケージの基本構成
  - kabusys パッケージ初期化（__version__ = "0.1.0"、主要サブパッケージのエクスポート定義）。
  - strategy, execution のパッケージスケルトンを用意（将来の戦略・発注ロジック実装箇所）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を探索）によりカレントワーキングディレクトリに依存しない自動読み込み。
  - .env / .env.local の読み込み順序と上書きルールの実装（OS 環境変数の保護、.env.local は上書き許可）。
  - 行解析の強化（export プレフィックス対応、シングル/ダブルクォートおよびエスケープ、インラインコメントの扱い）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト時などに使用）。
  - Settings クラスを提供し、必須環境変数取得メソッド（_require）や各種設定プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル判定等）を実装。
  - env 値の妥当性検証（development / paper_trading / live）とログレベルの検証。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装：
    - 固定間隔の簡易レートリミッタ（120 req/min 倍率）。
    - HTTP リクエストラッパー（urllib）による JSON パース、最大リトライ（指数バックオフ）処理。
    - 401 受信時の ID トークン自動リフレッシュ処理（1 回のみリトライ）とトークンキャッシュ共有。
    - ページネーション対応の fetch API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を利用した更新（upsert）を行い重複を排除。
    - データ型変換ヘルパ（_to_float, _to_int）で不正値を安全に扱う。
    - 取得時間（fetched_at）を UTC ISO 形式で記録し、look-ahead bias を軽減。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能の実装（fetch_rss, run_news_collection）：
    - RSS の取得・XML パース（defusedxml を利用）と記事抽出（title, content, pubDate, link）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事 ID（SHA-256 の先頭32文字）生成で冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - SSRF 対策：取得前にホストのプライベート判定、リダイレクト先のスキーム/ホスト検査を行うカスタムリダイレクトハンドラを採用。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍時のサイズチェック（Gzip bomb 対策）。
    - DB 保存時はチャンク化してトランザクションをまとめ、INSERT ... RETURNING で実際に挿入された新規記事 ID を返す（save_raw_news）。
    - 記事と銘柄コードの紐付け処理（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。銘柄抽出は単純な 4 桁数字パターンに基づき known_codes によるフィルタを行う。
    - デフォルトソースとして Yahoo Finance のビジネスカテゴリ RSS を定義。

- 研究用分析モジュール（kabusys.research）
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）：DuckDB の prices_daily を参照し、指定ホライズン（デフォルト 1/5/21 営業日）に対する将来リターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：ファクター値と将来リターンのスピアマン順位相関を実装。データ不足や同順位の扱いに配慮。
    - 基本統計サマリ（factor_summary）とランク関数（rank）。
    - 外部ライブラリに依存しない純粋 Python 実装（pandas 等を使わない設計）。
  - factor_research:
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - ボラティリティ・流動性（calc_volatility）：20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - バリュー（calc_value）：raw_financials から直近の財務データを取得し PER（EPS を用いる）、ROE を計算。prices_daily と結合して当日の株価ベースで計算。
    - 各計算は DuckDB のウィンドウ関数／集計を活用し、必要なスキャン範囲は概ね緩衝（カレンダー日 ×2）を取っている。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 向けのテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等の雛形）。
  - Raw / Processed / Feature / Execution 層に分ける設計ドキュメント方針に基づいた初期定義を用意。

### 変更
- （新規リリースのため該当なし）

### 修正
- （新規リリースのため該当なし）

### セキュリティ
- RSS パーサに defusedxml を利用し XML Bomb 等を軽減。
- RSS 取得時にホストがプライベート IP の場合は拒否、リダイレクト時も同様の検査を行って SSRF を防止。
- ニュース URL 正規化によりトラッキングパラメータを排除し、記事 ID による冪等化で重複登録を防止。

### 注意事項 / 既知の制約
- DuckDB への操作は DuckDB の Python API に依存するため、実行環境に duckdb が必要です。
- research モジュールは prices_daily / raw_financials 等のテーブルが適切に整備されていることを前提とします（データ不足時は None を返す設計）。
- jquants_client は urllib ベースの実装であり、より高機能な HTTP クライアント（例: requests）への置換は将来的な改善候補です。
- news_collector の銘柄抽出は単純な 4 桁数値パターンに依存しているため、誤抽出や文脈に依存した抽出漏れが発生する可能性があります。より高度な NER や辞書ベースの拡張が今後の課題です。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して手動で設定することを推奨します。

---

今後の予定（例）
- execution / strategy の実装（発注ロジック、ポジション管理、Paper/Live 切替）。
- テストカバレッジの充実（ユニット／統合テスト）。
- J-Quants クライアントのエラー監視・メトリクス収集強化。
- ニュース処理の自然言語処理強化（日本語固有表現抽出、学習済みモデル統合）。

--- 

作成者: コードベースの実装内容に基づき自動生成。詳細は各モジュールの docstring / ソースを参照してください。