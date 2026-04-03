CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに準拠して記載します。  
日付は本コードスナップショットの作成日（2026-04-03）です。

フォーマット
------------
- すべてのリリースはカテゴリ別（Added / Changed / Fixed / Security / Removed / Deprecated / Internal）で記載しています。
- 本リポジトリは初回公開（0.1.0）相当の内容を含むため、主に「Added」項目で構成されています。
- 実装や設計上の注意点・既知の制約も併記しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - ルートパッケージ定義（src/kabusys/__init__.py）を追加。公開モジュール: data, strategy, execution, monitoring。
- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env と .env.local の優先順序を実装（OS 環境変数を保護する protected 機構を採用）。
  - 複雑な .env 行のパース実装:
    - export VAR=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどに対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェック _require() と Settings クラスを提供。J-Quants / kabuAPI / LINE / DB パス /監視閾値 /実行環境（development/paper_trading/live）等のプロパティを定義。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値は ValueError を送出）。
- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄別にニュースを集約して OpenAI（gpt-4o-mini）にバッチ送信し、ai_scores テーブルへ書き込む score_news() を実装。
    - JST基準のニュースウィンドウ計算（前日15:00〜当日08:30、UTCへ変換）を calc_news_window() として実装。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたり記事数 / 文字数のトリム、JSON Mode 出力のバリデーション（results リスト・型チェック・コード照合・数値検証）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行を実装。致命的でない場合はスキップして処理継続（フェイルセーフ設計）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime() を実装。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）にタイトル群を渡して macro_sentiment を評価（記事がない場合は LLM 呼び出しを行わず 0.0 を使用）。
    - API エラーに対するリトライ、JSON パース失敗時は 0.0 にフォールバックするフェイルセーフを実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB 登録値優先、未登録日は曜日（週末）フォールバックを採用。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間ジョブ calendar_update_job() を実装。バックフィル、健全性チェックを実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - 差分取得・保存・品質チェックを想定した ETL 設計（J-Quants client 連携 / backfill 対応 / 品質チェックの収集継続方針）。
    - 内部ヘルパー: テーブル存在チェック、最大日付取得などを実装。
- Research（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。DuckDB 上の SQL と窓関数を活用して計算。
    - 設計上、prices_daily / raw_financials のみ参照し、発注や外部 API にアクセスしないことを明示。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient、Spearman の ρ）計算 calc_ic。
    - ランク変換ユーティリティ rank（同順位の平均ランク処理、丸めによる ties 対応）。
    - ファクター統計 summary を返す factor_summary。
  - research パッケージ初期公開インターフェース（__init__.py）で主要関数を再エクスポート。
- DuckDB を主要なデータ格納 / 集計エンジンとして想定。多数のモジュールが DuckDB 接続を引数として受ける設計。
- 依存を最小化: pandas 等の外部ライブラリを使用しない設計（標準ライブラリ + openai + duckdb 想定）。

Security
- API キー管理に関する注意:
  - OpenAI API キーは各 AI 関数（score_news, score_regime）で引数 api_key または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して失敗を明示。
  - .env 自動読み込みはデフォルトで有効。テストや安全措置で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
- 環境変数の上書きルール:
  - OS 環境変数は protected として .env の上書きから保護される（.env.local は上書き可能だが protected は除外）。

Internal / Design notes
- ルックアヘッドバイアス防止:
  - AI モジュール・research・ETL など多くの関数は内部で datetime.today() / date.today() を参照せず、必ず target_date を引数で受け取る設計。
- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api）をモジュールローカルで定義し、unittest.mock.patch による差し替えを想定した設計。
- フェイルセーフ方針:
  - OpenAI の失敗や API 一時エラーは基本的に再試行し、最終的に取得できない場合はスキップして処理継続（例: macro_sentiment=0.0、スコア未取得の場合は該当銘柄を除外）。
- DuckDB の executemany に関する互換性考慮（空リストを渡さないガード）。

Known limitations / Notes
- DuckDB のスキーマ（テーブル名 / カラム）は本実装前提で記述されており、事前に該当テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を用意する必要があります。
- OpenAI とのやり取りは gpt-4o-mini（JSON Mode）を想定しているため、API の挙動変更や SDK バージョン差異に注意が必要です。
- execution / monitoring / strategy パッケージの具体実装はこのスナップショットに含まれていないか限定的です（パッケージ公開インターフェースには含むが、実装は別途提供想定）。
- 一部処理は DuckDB のバージョン依存（配列バインドや executemany の挙動）を考慮した実装になっています。DuckDB の古い/新しいバージョンで差異がある場合は注意してください。

Upgrade / Migration notes
- 初回リリースのためアップグレード手順は不要。ただし既存環境で動かす際は以下を確認してください:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（使用する機能に依存）。
  - OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定。
  - DuckDB のデータベースファイル（DUCKDB_PATH）や監視 DB（SQLITE_PATH）等のパスを設定するかデフォルト（data/ 以下）を作成。

開発者向けメモ
- テストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑制すると安定。
- OpenAI への呼び出しはモジュール内の _call_openai_api を patch することで外部 API をモック化できます（unit テスト推奨）。
- ログ出力レベルは Settings.log_level で制御。無効な値は ValueError を投げるため設定ミスを早期に検出できます。

----

（以降のリリースでは Changed / Fixed / Removed / Deprecated セクションを追加して更新してください）