CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース。パッケージ名: kabusys（バージョン 0.1.0）。
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__="0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理:
  - src/kabusys/config.py を追加。
    - .env / .env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント等に対応。
    - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH 等）を取得。
    - KABUSYS_ENV と LOG_LEVEL の検証ロジック、便利なプロパティ is_live / is_paper / is_dev を実装。

- AI 関連:
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事件数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON mode を想定したレスポンス処理、応答のバリデーション（results 配列、code・score のチェック）、スコアは ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他はフォールバックでスキップ。
    - DuckDB executemany の空リスト問題に対する保護（空の場合は処理スキップ）。
    - テスト容易性のため OpenAI 呼出しラッパー（_call_openai_api）を patch 可能に設計。
    - タイムウィンドウは JST ベース（前日15:00 JST ～ 当日08:30 JST）で calc_news_window を提供。

  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース抽出はキーワードベース（日本語・英語混在キーワード群）。
    - OpenAI 呼び出し（gpt-4o-mini）結果は JSON 期待、リトライ・バックオフ・5xx ハンドリングを実装。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）を実装。
    - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を参照しない設計。prices_daily クエリは target_date 未満のデータのみを使用。

- Research（因子・特徴量）:
  - src/kabusys/research/factor_research.py を追加。
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を計算する関数群:
      - calc_momentum(conn, target_date)
      - calc_value(conn, target_date)
      - calc_volatility(conn, target_date)
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照する設計。
    - データ不足時は None を返す等の堅牢な取り扱い。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
    - IC（Spearman の ρ）計算 calc_ic(...)
    - ランク変換ユーティリティ rank(values)
    - 統計サマリー factor_summary(records, columns)
    - pandas 等外部ライブラリに依存しない実装。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- Data（データプラットフォーム）:
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar テーブルの管理、営業日判定ロジック、next/prev/get_trading_days、is_sq_day、夜間バッチ calendar_update_job を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - J-Quants クライアントを用いた差分取得・バックフィル・健全性チェックを実装。
  - src/kabusys/data/pipeline.py を追加。
    - ETL パイプラインの骨組み（差分フェッチ、save_* による冪等保存、品質チェックの収集）を提供。
    - ETLResult dataclass を定義（取得件数、保存件数、quality_issues、errors 等を含む）。
    - _get_max_date 等のユーティリティを実装。
  - src/kabusys/data/etl.py で ETLResult を公開。
  - jquants_client との連携点（fetch/save 関数）を想定した設計。

- パッケージ設計方針・実装上の特徴:
  - DuckDB を主要なストレージとして利用する設計を前提に、直接 SQL を用いた処理を採用。
  - ルックアヘッドバイアス防止のため、現在日時を直接参照しない（target_date を明示的に渡す設計）。
  - OpenAI API 呼び出しに対して堅牢なリトライ・バックオフ戦略を実装し、API 失敗時は例外を投げずにフォールバックする（多くの箇所で macro_sentiment=0.0 やスコア取得スキップ）。
  - テスト容易性のため、API 呼び出しを差し替え可能（モジュール内 private 関数を patch）な設計。
  - 外部解析に pandas 等を使用せず、標準ライブラリと duckdb だけで完結する実装方針。
  - ロギングを各モジュールで活用し、異常時の警告・情報出力を充実させている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated / Removed / Security
- （該当なし）

注意事項（ドキュメント的補足）
- OpenAI API を利用する機能（news_nlp, regime_detector）は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照します。API キーが未設定の場合は ValueError を送出します。
- DuckDB の executemany に関するバージョン差分に配慮した実装（空リストを渡さない）を行っています。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml から探します。パッケージ配布後やテスト時に挙動を変更したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

貢献・バグ報告
- バグや改善提案があれば issue を立ててください。README / ドキュメントに追記のうえ次バージョンで反映します。

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや公開日付は運用ポリシーに合わせて調整してください。）