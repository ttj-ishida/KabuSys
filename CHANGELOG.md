CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
  - パッケージ公開情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パッケージ外部公開モジュール: data, strategy, execution, monitoring
  - 環境設定管理 (src/kabusys/config.py)
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パースの強化:
      - export プレフィックスの許容。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - インラインコメントや '#' の扱いルールの実装。
    - 環境変数取得ヘルパー _require と Settings クラス:
      - J-Quants / kabu API / Slack / DB パス等のプロパティを提供。
      - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証。
      - duckdb/sqlite のデフォルトパス取得。
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - 再試行処理（指数バックオフ、最大3回）。408/429/5xx を再試行対象に設定。
    - 401 発生時の ID トークン自動リフレッシュ（1回まで）とトークンキャッシュの共有。
    - ページネーション対応（pagination_key の処理）。
    - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ型変換ユーティリティ (_to_float, _to_int) を実装。
    - 取得時刻 fetched_at を UTC で記録し、Look-ahead バイアス対策を考慮。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードからのニュース収集と raw_news への保存機能。
    - 特徴:
      - デフォルト RSS ソース（Yahoo Finance）の定義。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
      - defusedxml を用いた XML パース（XML Bomb 対策）。
      - SSRF 対策:
        - http/https のみ許可するスキーム検証。
        - プライベートアドレス（ループバック等）へのアクセス拒否（DNS 解決含む）。
        - リダイレクト時にスキーム・ホストを検証するカスタムリダイレクトハンドラ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後の再検査。
      - テキスト前処理（URL除去・空白正規化）。
      - 銘柄コード抽出（4桁数字、known_codes に基づくフィルタ）。
      - DuckDB へのバルク挿入（チャンク、トランザクション、INSERT ... RETURNING を利用）:
        - save_raw_news は挿入された新規記事IDのリストを返す。
        - save_news_symbols / _save_news_symbols_bulk による記事と銘柄の紐付け（重複除去・トランザクション管理）。
  - DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution 層を想定したテーブル定義を追加。
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
    - 利用頻度を想定したインデックス定義を追加。
    - init_schema(db_path) によるディレクトリ自動作成と全DDL実行、get_connection の追加。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
    - ETL の設計に基づく差分更新・バックフィル・品質チェックのための基盤を追加。
    - ETLResult データクラス: ETL 実行結果の集約（品質問題・エラー情報含む）。
    - 市場カレンダー補正ユーティリティ (_adjust_to_trading_day) を実装。
    - テーブル最終取得日取得ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - run_prices_etl の導入（差分更新ロジック、バックフィル日数の扱い、jquants_client を利用した取得と保存の流れ）。
  - その他
    - パッケージ内に data, strategy, execution, monitoring のモジュール雛形を追加（将来拡張用）。

Security
- ニュース収集周りで以下のセキュリティ対策を導入:
  - defusedxml を使用して XML による攻撃を回避。
  - SSRF 対策（スキーム制限・プライベートIPチェック・リダイレクト検査）。
  - レスポンスサイズ上限や gzip 解凍後のサイズ確認によるリソース制限。

Notes / Known limitations
- 初期リリースのため、strategy / execution / monitoring の具象実装はまだ追加されていません（モジュールの雛形のみ）。
- run_prices_etl を含む ETL 周りは主要な機能を実装していますが、オプションの品質チェック（quality モジュール）や一部の運用ロジックは別途実装・統合が必要です。
- 単体テスト用のフック（例: news_collector._urlopen のモックポイントや config の KABUSYS_DISABLE_AUTO_ENV_LOAD）は用意されていますが、テストスイートは別途整備する必要があります。

-------------------

今後のリリースでは、strategy の実装、execution（kabuステーション連携）や監視/アラート（Slack連携）の統合、品質チェック自動化の強化、テストカバレッジ向上を予定しています。