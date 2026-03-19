CHANGELOG
=========
すべての変更は "Keep a Changelog" の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-03-19
-----------------

Added
- 初回リリース。日本株自動売買システムの基盤的モジュール群を追加。
  - パッケージ公開
    - パッケージメタ情報: kabusys.__version__ = "0.1.0"
    - kabusys パッケージは data / strategy / execution / monitoring を公開。

  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数の自動読み込み機能を実装。
      - 読み込み順序: OS 環境 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - プロジェクトルート検出は .git または pyproject.toml を基準に実施（__file__ 起点で探索）。
    - .env 解析ロジック:
      - export プレフィックス対応、クォートのエスケープ処理、行内コメント処理などを考慮。
    - Settings クラスでアプリケーション設定をプロパティ提供（J-Quants, kabu API, Slack, DB パス, 環境・ログレベル等）。
      - 必須環境変数のチェックと不正値検出（KABUSYS_ENV, LOG_LEVEL の検証）。
      - デフォルト DB パス: duckdb は data/kabusys.duckdb、sqlite は data/monitoring.db。

  - データ API クライアント (kabusys.data.jquants_client)
    - J-Quants API 用クライアントを実装。
      - 固定間隔のレートリミッタ（デフォルト 120 req/min）を実装。
      - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。
      - 401 受信時の自動トークンリフレッシュを一度だけ行う仕組み。
      - ページネーション対応（pagination_key の取り扱い）。
      - データ取得関数:
        - fetch_daily_quotes（株価日足の取得、ページネーション対応）
        - fetch_financial_statements（財務データの取得、ページネーション対応）
        - fetch_market_calendar（JPX マーケットカレンダーの取得）
      - DuckDB への保存関数（冪等）:
        - save_daily_quotes, save_financial_statements, save_market_calendar
        - 保存時に fetched_at を UTC で記録し、ON CONFLICT ... DO UPDATE で重複を解消
      - ユーティリティ: 型変換ヘルパー _to_float / _to_int

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードから記事収集し raw_news / news_symbols に保存する一連処理を実装。
    - 主な機能:
      - RSS フィード取得（gzip 対応、Content-Length と実読取サイズの上限チェック）
      - XML パースに defusedxml を利用して XML BOM 等の脅威を軽減
      - SSRF 対策:
        - リダイレクト先のスキーム検証、プライベート IP/ホスト判定（DNS 解決を含む）
        - リダイレクト時に事前検証を行うカスタムハンドラを実装
      - URL 正規化とトラッキングパラメータ除去（utm_* など）および記事 ID を SHA-256 (先頭32文字) で生成
      - テキスト前処理（URL 除去・空白正規化）
      - 銘柄コード抽出（4桁数字、既知コードのみ採用）
      - DB 保存はチャンク/トランザクション化、INSERT ... RETURNING により実際に挿入された件数を返す
      - run_news_collection により複数ソースを独立ハンドリングして一括収集可能
    - デフォルト RSS ソース: Yahoo Finance ビジネスカテゴリ等が設定済み

  - データスキーマ定義 (kabusys.data.schema)
    - DuckDB 用の DDL を定義（Raw / Processed / Feature / Execution 層の設計に基づく）。
    - 生データテーブル例:
      - raw_prices（date, code, open, high, low, close, volume, turnover, fetched_at, PK(date, code)）
      - raw_financials（code, report_date, period_type, eps, roe, fetched_at, PK(code, report_date, period_type)）
      - raw_news（id, datetime, source, title, content, url, fetched_at）
      - raw_executions（実行系テーブルのスキーマ定義の開始）
    - スキーマはデータの冪等性（PK + ON CONFLICT）を想定した構成。

  - 研究用モジュール (kabusys.research)
    - 特徴量探索 / ファクター計算関数を追加（DuckDB 接続を受け DB を参照して計算）。
    - feature_exploration:
      - calc_forward_returns（指定日の終値から各ホライズン先の将来リターンを一括取得）
      - calc_ic（ファクター値と将来リターンのスピアマンランク相関（IC）を計算）
      - factor_summary（基本統計量: count/mean/std/min/max/median を計算）
      - rank（同順位は平均ランクにする実装、丸めで ties 検出漏れを抑制）
      - 実装方針: DuckDB の prices_daily のみ参照、外部ライブラリに依存しない実装
    - factor_research:
      - calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev の算出）
      - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio の算出）
      - calc_value（per, roe を raw_financials と prices_daily を組み合わせて算出）
      - 設計上、必要な過去データを限定して SQL ウィンドウ関数で効率的に計算
    - research パッケージ __init__ で主要関数群を公開（zscore_normalize を data.stats からインポート）

Security
- ニュース収集モジュールで SSRF 対策を強化（スキームチェック、プライベートアドレス検出、リダイレクト検査）。
- XML パースは defusedxml を利用して安全性を向上。
- J-Quants クライアントは API レート・リトライ・トークンリフレッシュの扱いを明確化。

Notes / Usage
- DuckDB 接続が前提の関数が多く、事前に schema の初期化（DDL 実行）や DuckDB ファイルの配置が必要。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 環境切替: KABUSYS_ENV（development / paper_trading / live）
- .env の自動ロードを無効にしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research モジュールは外部ライブラリ（pandas 等）に依存しないよう設計されていますが、DuckDB が必要です。

Known issues / TODO
- schema ファイルの一部（raw_executions の続きなど）や Execution / Strategy / Monitoring の具象実装はまだ未完成/未実装。
- 一部の関数は DuckDB のテーブル命名（prices_daily 等）に依存するため、環境に合わせたマイグレーション/テーブル生成が必要。
- news_collector の URL 正規化は既知トラッキングパラメータプレフィックスに依存しており、追加のプレフィックスが必要となる場合がある。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- （上記の SSRF / XML ハードニングを参照）

---

補足:
この CHANGELOG は、提供されたコードベースの実装・設計・意図をコードから推測して作成しています。実際のリリースノートを作成する際は、コミット履歴や差分を参照して調整してください。