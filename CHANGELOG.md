KEEP A CHANGELOG
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

（現時点の差分は特になし。次回リリースに向けた変更はここに記載します。）

[0.1.0] - 2026-03-19
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ基底:
    - src/kabusys/__init__.py にてパッケージ名・バージョン（0.1.0）・主要サブパッケージを公開。
  - 設定管理:
    - src/kabusys/config.py
      - .env ファイルと環境変数を統合して読み込む自動ロード実装（プロジェクトルート検出: .git または pyproject.toml）。
      - .env と .env.local の優先順位（OS 環境変数 > .env.local > .env）と .env.local による上書き機能。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
      - export KEY=val 形式やクォート/コメントの扱いに対応した堅牢な .env パーサー。
      - 必須値チェックを行う Settings クラス（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* 等のプロパティ）、環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL）と便宜プロパティ（is_live / is_paper / is_dev）。
  - Data レイヤー:
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。ページネーション対応、レート制限 (120 req/min) を守る固定間隔レートリミッタを内蔵。
      - 再試行（指数バックオフ、最大 3 回）および 401 受信時のトークン自動リフレッシュ対応。
      - fetch_* 系（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）により API データ取得を提供。
      - DuckDB への保存用関数（save_daily_quotes、save_financial_statements、save_market_calendar）を提供し、ON CONFLICT による冪等保存を実現。
      - 型変換ユーティリティ（_to_float、_to_int）で不正データや空値を安全に扱う。
    - src/kabusys/data/news_collector.py
      - RSS ベースのニュース収集器。RSS 取得、前処理、ID 生成、DuckDB への冪等保存、記事と銘柄の紐付けを実装。
      - セキュリティ/健全性対策:
        - defusedxml を利用した XML パース（XML Bomb 等に耐性）。
        - HTTP(S) スキームのみ許可。URL 正規化とトラッキングパラメータ除去。
        - SSRF 対策: リダイレクトハンドラでリダイレクト先のスキームとプライベートアドレス判定を実施。初期 URL と最終 URL の検査。
        - レスポンスの最大受信バイト数制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
      - save_raw_news/save_news_symbols/_save_news_symbols_bulk はチャンク挿入、トランザクション管理、INSERT ... RETURNING を用いて実際に挿入された件数を正確に返す実装。
      - extract_stock_codes によりテキスト中の 4 桁銘柄コード抽出（known_codes によるフィルタ）を提供。
      - run_news_collection により複数 RSS ソースの一括収集と DB 保存、銘柄紐付けを行うオーケストレーションを提供。
    - src/kabusys/data/schema.py
      - DuckDB 用スキーマ定義（Raw レイヤーのテーブル DDL: raw_prices、raw_financials、raw_news、raw_executions 等の作成文を含む）。（プロジェクトの DataSchema.md に基づく定義）
  - Research レイヤー:
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: DuckDB の prices_daily を参照して指定日から各ホライズン先の将来リターンを一括取得。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。ties に対する平均ランク処理を実装し、データ不足時の None ハンドリング。
      - rank: 同順位を平均ランクに変換するユーティリティ（丸め処理で浮動小数誤差を防止）。
      - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算する統計サマリ。
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M モメンタム、200 日移動平均乖離率 (ma200_dev) を計算（ウィンドウ内データ不足は None を返す）。DuckDB のウィンドウ関数を活用。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true range の NULL 伝播を正しく扱う実装。
      - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し、PER/ROE を計算（EPS 0/欠損時は None）。
    - src/kabusys/research/__init__.py にて主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。
  - その他:
    - 設計文書に対応した実装方針と詳細な docstring を各モジュールに付与（データ参照範囲、外部アクセス禁止の旨、パフォーマンス考慮など）。

Security
- RSS ニュース収集での SSRF 対策、defusedxml による XML ハンドリング、レスポンスサイズ制限、URL 正規化・トラッキング除去などを導入し外部入力に対する安全性を強化。
- J-Quants クライアントはトークン自動更新、HTTP エラーに対する再試行・バックオフを実装し堅牢性を向上。

Notes
- すべてのデータ取得/計算関数は本番口座の発注 API 等にはアクセスせず、DuckDB の prices_daily / raw_financials テーブルのみを参照することを設計上の前提としています（Research モジュール）。
- DuckDB への挿入は ON CONFLICT を用いた冪等処理を基本としているため、定期実行ジョブでの重複挿入を避けられます。
- .env の自動読み込みはパッケージ使用時に自動で行われますが、テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

未解決 / 今後の改善候補
- Data/schema.py に Execution レイヤー等の DDL が途中まで記載（コード切れ）となっているので、完全なスキーマ定義の追加・検証を推奨。
- 単体テスト・統合テストの整備（API モック、ネットワーク失敗時の挙動確認、DuckDB 初期化テストなど）。
- performance: 大規模データでの DuckDB クエリ最適化やニュース収集の並列化（SSRF 検査を保ちつつ）の検討。

----