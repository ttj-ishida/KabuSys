# Changelog

すべての変更は Keep a Changelog の仕様に従って記載します。  
安定したリリースはセマンティックバージョニングを使用します。

## [Unreleased]
- （現時点のコードベースはバージョン 0.1.0 を示しています。今後の変更はここに記載してください。）

## [0.1.0] - 初回リリース
初期実装。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。主に以下のサブパッケージ・機能を追加しています。

### 追加
- パッケージ全体
  - パッケージ情報 (src/kabusys/__init__.py)
    - バージョン: 0.1.0
    - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 環境変数自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの実装:
    - export KEY=val 形式、クォートやエスケープ対応、インラインコメント処理。
  - Settings クラス（settings インスタンスを提供）:
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL 等）をプロパティで取得。
    - 値の検証（有効な env 値・ログレベルのチェック）と必須値チェック（未設定時は ValueError）。

- Data サブパッケージ（src/kabusys/data/）
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出し用ユーティリティと高レイヤー関数を実装。
    - 特徴:
      - レート制限遵守（固定間隔スロットリング: 120 req/min 相当の RateLimiter）。
      - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
      - ページネーション対応の fetch_{daily_quotes, financial_statements}。
      - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
      - 型変換ユーティリティ (_to_float, _to_int) と fetched_at の UTC 記録。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードからの記事取得と DuckDB への保存処理を実装。
    - 特徴:
      - RSS パースは defusedxml を使用して XML 関連の脆弱性に配慮。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）。
      - SSRF 対策:
        - リダイレクト時のスキーム検証・プライベートホスト検出（_SSRFBlockRedirectHandler, _is_private_host）。
        - fetch_rss 前にホストの検査を行い、プライベートアドレスへのアクセスを拒否。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後のチェック（Gzip bomb 対策）。
      - テキスト前処理（URL 除去・空白正規化）。
      - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
      - DB 保存はチャンク化して一つのトランザクションで行い、INSERT ... RETURNING によって実際に挿入された件数を取得。
      - 銘柄コード抽出ユーティリティ（4桁コード抽出）とニュース⇄銘柄紐付け処理（save_news_symbols, _save_news_symbols_bulk）。
      - デフォルト RSS ソース（Yahoo Finance のカテゴリ RSS）を定義。
  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - Raw Layer の初期 DDL を追加:
      - raw_prices, raw_financials, raw_news, raw_executions（raw_executions はファイル切断点あり、スキーマ定義を含む）。
    - Data 層のテーブル定義と初期化用の DDL を備える。

- Research サブパッケージ（src/kabusys/research/）
  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
      - DuckDB の prices_daily テーブルを参照し、複数ホライズンをまとめて取得する高効率クエリを実装。
      - horizons の検証（正の整数かつ <= 252）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
      - Spearman の ρ（ランク相関）を標準ライブラリのみで計算する実装。
      - 値の無効／欠損処理、最小有効レコード数チェック（3 件未満で None）。
      - ランク計算ユーティリティ rank(values)（同順位は平均ランク、浮動小数丸め対策あり）。
    - ファクター統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）
    - 設計方針: DuckDB (prices_daily) のみ参照、外部 API にはアクセスしない、標準ライブラリのみで実装。
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクターの計算関数:
      - calc_momentum(conn, target_date)
        - mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離率）を計算。
        - 必要な過去データが不足する場合は None を返す仕様。
      - calc_volatility(conn, target_date)
        - atr_20（20 日 ATR の平均）, atr_pct, avg_turnover, volume_ratio を計算。
        - true_range の NULL 伝播を適切に扱い、カウント不足時は None を返す。
      - calc_value(conn, target_date)
        - raw_financials から最新の財務データを取得し per（株価 / EPS）や roe を計算。
        - price と財務データの LEFT JOIN を行う設計。
    - 設計方針: prices_daily / raw_financials のみ参照、出力は (date, code) をキーとする dict のリスト。
  - research パッケージ __init__ で主要関数をエクスポート（calc_momentum 等、zscore_normalize も re-export）。

### 改善（設計上の配慮）
- 安全性
  - news_collector で SSRF 対策、XML パースの安全化、レスポンスサイズ制限を実装。
  - jquants_client でトークン管理・再取得の仕組みとリトライ（429 の Retry-After を尊重）。
- 冪等性とトランザクション
  - DuckDB への保存処理は ON CONFLICT による更新またはスキップ、トランザクション管理、チャンク挿入で効率化。
- パフォーマンス
  - DuckDB のウィンドウ関数を活用してファクター計算を SQL 側で集約的に実行（scan 範囲のカレンダーバッファを設定）。
  - API 呼び出しはモジュールレベルの固定間隔スロットリングでレートを保つ。
  - ニュース保存はチャンク化してプレースホルダ一括挿入。

### 既知の制約・注意点
- research モジュールは外部ライブラリ（pandas 等）に依存せず純粋な標準ライブラリ実装を目指しているため、データ量や使い勝手において pandas ベースの実装と差異がある可能性があります。
- jquants_client の _BASE_URL は実装内でハードコードされていますが、settings からの上書きは未実装（将来的に設定化を検討）。
- schema.py の raw_executions 定義はソースが途中で切れているため、完全な Execution 層スキーマは今後追加される予定です。
- 設定の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は未設定の場合 ValueError を送出するため、実行前に .env を用意してください。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

### 互換性（Breaking Changes）
- 初回リリースのため破壊的変更はありません。今後のメジャーアップデートで API/スキーマ変更が発生する可能性があります。

---

（注）本 CHANGELOG は与えられたコードベースの内容から推測して作成した初期リリースノートです。将来の実装追加や変更に応じて適宜更新してください。