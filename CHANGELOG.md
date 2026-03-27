CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグ付け済みリリース: 0.1.0（初回公開）。

Unreleased
----------

（現在のコードベースは初回リリース相当のため、未リリースの差分はありません。）

[0.1.0] - 2026-03-27
--------------------

Added
- 初期リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: パッケージのエントリポイント。バージョン "0.1.0"、公開モジュール一覧（data, strategy, execution, monitoring）を定義。
  - 設定 / 環境変数管理
    - src/kabusys/config.py:
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env 行パーサは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなどに対応。
      - 環境変数保護（既存 OS 環境変数を保護する protected set）および override ロジック実装。
      - Settings クラスで必須・任意の設定をプロパティで提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。値検証（env, log_level 等）と is_live/is_paper/is_dev ヘルパーを提供。
  - AI（LLM）関連
    - src/kabusys/ai/news_nlp.py:
      - ニュース記事（raw_news と news_symbols）を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄別センチメント（-1.0〜1.0）を評価。
      - チャンク処理（最大 20 銘柄/コール）、記事トリム（最大記事数・最大文字数）、レスポンスバリデーション、スコアの ±1.0 クリップ、DuckDB へ冪等的に書き込み（DELETE → INSERT）を実装。
      - リトライ戦略（429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ）。API 失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
      - 単体テストのため _call_openai_api を差し替え可能（unittest.mock.patch 推奨）。
      - calc_news_window(target_date) でニュース集計ウィンドウ（JST基準 → UTC转换）を提供。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
      - マクロニュース抽出、LLM 呼び出し（gpt-4o-mini + JSON mode）、リトライ/フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
      - ルックアヘッドバイアス防止のため datetime.today() を参照せず、prices_daily クエリは target_date 未満の排他条件を採用。
  - データ基盤（Data platform）
    - src/kabusys/data/calendar_management.py:
      - JPX カレンダー管理：market_calendar テーブルを基に営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）、SQ日判定（is_sq_day）を実装。
      - DBにカレンダーがない場合は曜日ベース（土日休み）でフォールバック。DB の NULL 値は警告しフォールバックを使用。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを含む）。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
      - ETLResult データクラスを公開（ETL 実行結果・メタデータ・品質チェック結果・エラー一覧を保持）。
      - ETL の差分更新、backfill、品質チェック（quality モジュール利用）、保存は jquants_client の save_* 関数を利用して冪等保存する設計（詳細は pipeline 内のユーティリティ実装）。
      - DuckDB のテーブル存在チェック、最大日付取得ユーティリティ実装。
    - src/kabusys/data/__init__.py と etl の再エクスポート。
  - リサーチ / ファクター分析
    - src/kabusys/research/factor_research.py:
      - モメンタム（1M/3M/6M）、ma200乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
      - データ不足時の None 処理、ログ出力、営業日スキャン範囲のバッファ設計などを実装。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns、可変ホライズン、範囲チェック）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - 外部依存（pandas等）を使わず標準ライブラリで実装。欠測・非有限値は除外。
    - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から再利用想定）。
  - 汎用・設計上の注意点
    - DuckDB を主要なローカル分析 DB として利用（関数は DuckDB 接続を受け取る設計）。
    - ルックアヘッドバイアス防止: 日時は外部引数（target_date）で与える設計、内部で date.today()/datetime.today() を参照しない。
    - LLM 呼び出しは JSON mode を利用し、レスポンスのバリデーションを厳密に実施。
    - 多くの箇所で冪等性（DELETE→INSERT、ON CONFLICT など）・ロールバックハンドリング（BEGIN/COMMIT/ROLLBACK）を明示的に実装。
    - テスト容易性のため、OpenAI 呼び出し箇所（_call_openai_api）やその他の副作用を差し替え可能に設計。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし（初回リリース）。

Removed
- 該当なし（初回リリース）。

Security
- 該当なし（初回リリース）。ただし環境変数に API キー等を格納する設計のため、運用時は OS / CI のセキュリティに注意。

注記（ユーザー向け/移行ガイド）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を用いる機能を使う場合は OPENAI_API_KEY が必要（score_news, score_regime にて引数で上書き可能）。
- 自動 .env ロードはデフォルトで有効。テストや特殊環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB/SQLite のデフォルトパスは Settings.duckdb_path / sqlite_path で定義。必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH を設定してください。
- LLM の呼び出しは外部ネットワーク・API レート制限の影響を受けます。大量データ処理時はレート管理・コストに注意してください。
- 単体テストでは _call_openai_api をモックすることで外部 API 呼び出しを回避できます。

今後の予定（示唆）
- strategy / execution / monitoring パッケージの具体実装（発注ロジック、監視・通知）を追加予定。
- jquants_client と quality モジュールの詳細実装・テストカバレッジ拡充。
- バッチ / スケジューラ統合や運用ドキュメント整備。

----