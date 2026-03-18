CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース。基本的な日本株自動売買システムの骨組みを実装。
  - パッケージ情報:
    - src/kabusys/__init__.py にてバージョン "0.1.0" を設定。
  - 環境変数 / 設定管理:
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み（優先順位: OS > .env.local > .env）。プロジェクトルートの探索は .git または pyproject.toml を基準に行うため、CWD に依存しない読み込みを実現。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト時に利用可能）。
      - .env ファイルの堅牢なパース実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント取り扱い）。
      - Settings クラスで各種必須値を取得・検証（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など）。KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
      - デフォルト DB パス（DuckDB / SQLite）の取得と Path 正規化。

  - J-Quants API クライアント:
    - src/kabusys/data/jquants_client.py
      - レート制限制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
      - 冪等かつ堅牢な HTTP リクエスト実装:
        - 再試行（指数バックオフ）ロジック（最大 3 回、対象ステータス 408/429/5xx）。
        - 401 の場合はリフレッシュトークンから id_token を再取得して 1 回リトライ（無限再帰防止）。
        - ページネーション対応（pagination_key）、ページ間で id_token を共有するモジュールキャッシュを実装。
        - JSON デコードエラーハンドリングとログ。
      - データ取得関数:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供（ページネーション対応、取得件数ログ）。
      - DuckDB への保存関数（冪等）:
        - save_daily_quotes, save_financial_statements, save_market_calendar を実装。いずれも ON CONFLICT（PK）で更新することで冪等性を担保。
        - fetched_at を UTC タイムスタンプで保存し、データの「いつ知り得たか」を記録（Look-ahead バイアス対策）。
      - 型変換ユーティリティ (_to_float / _to_int) を実装し、不正値を安全に扱う。

  - ニュース収集モジュール:
    - src/kabusys/data/news_collector.py
      - RSS フィード収集パイプラインを実装（デフォルトソースに Yahoo Finance を追加）。
      - セキュリティ・堅牢性:
        - defusedxml を用いた XML パース（XML Bomb 等への対策）。
        - SSRF 対策: リダイレクト時にスキーム検証・ホスト（IP）検証を行う _SSRFBlockRedirectHandler を実装。初回 URL も事前にプライベートアドレス検査を行う。
        - URL スキームは http/https のみ許可。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェックを行い、メモリ DoS を防止。
      - テキスト前処理:
        - URL 削除、空白正規化を行う preprocess_text。
      - 記事ID生成と重複除去:
        - URL 正規化（tracking パラメータ除去、クエリソート、フラグメント削除）を行い、正規化後の SHA-256（先頭32文字）で記事 ID を生成。
        - save_raw_news ではチャンク分割、トランザクション、INSERT ... RETURNING により実際に挿入された新規記事 ID を返す設計（ON CONFLICT DO NOTHING）。
      - 銘柄紐付け:
        - テキスト中から 4 桁数字（日本株銘柄コード候補）を抽出し、既知コードセットによるフィルタリングで news_symbols に紐付け。_bulk 保存関数で一括挿入（ON CONFLICT DO NOTHING）し、実際に挿入された数を返す。
      - fetch_rss / save_raw_news / save_news_symbols / run_news_collection を通じた統合ジョブを提供。

  - DuckDB スキーマ管理:
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の各レイヤーのテーブル DDL を定義。
      - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
      - features, ai_scores 等の Feature レイヤー。
      - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤー。
      - 適用しやすいインデックス群を定義（頻出クエリ向け）。
      - init_schema(db_path) により親ディレクトリ自動作成、DDL/インデックスの冪等実行、DuckDB 接続を返す。":memory:" 対応。
      - get_connection(db_path) による既存 DB 接続取得。

  - ETL パイプライン:
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題、エラー一覧）を構造化して返却。
      - 差分更新ロジック:
        - raw_prices/raw_financials/market_calendar の最終取得日を元に差分取得を行うユーティリティ（get_last_price_date 等）。
        - backfill_days（デフォルト 3 日）を使い最終取得日の数日前から再取得して API の後出し修正を吸収する設計。
      - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day) を実装。
      - run_prices_etl（差分 ETL の一部）を実装（fetch -> save の流れ、ログ出力）。id_token の注入でテスト容易性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサーに defusedxml を採用、SSRF 対策（リダイレクト検査・プライベート IP 拒否）、レスポンスサイズ制限、URL スキーム制限等を追加し外部入力からの攻撃リスクを軽減。

Notes / Implementation details
- 多くの保存処理は DuckDB の ON CONFLICT 機構を使い冪等性を確保しているため、再実行可能な ETL 設計。
- ネットワーク呼び出しは再試行とレート制限で耐障害性を高めている。429 に対しては Retry-After ヘッダを尊重する実装。
- モジュール内の一部関数（例: _urlopen, fetch_*）はテスト時にモックしやすいように設計されている。
- news_collector の記事 ID はトラッキングパラメータ削除後にハッシュ化することでトラッキング付きURLの重複登録を防止。

破壊的変更 (BREAKING CHANGES)
- なし（初回リリース）

---

今後の予定（例）
- 品質チェック quality モジュールとの連携強化（pipeline での品質チェック結果の自動集計・エラー分類）。
- execution レイヤーの実稼働連携（kabu ステーション API 経由の注文送信 / 約定反映ロジック）。
- ニュースの言語解析 / 感情分析（ai_scores テーブルの利用例）