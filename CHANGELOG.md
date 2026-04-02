CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
-------------

- （現在なし）

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数の自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用）。
  - .env のパース機構を実装（export 形式、クォート・エスケープ、インラインコメント処理に対応）。
  - 環境変数取得ユーティリティ Settings を提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - CPU/MEMORY/DISK の閾値、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL
  - 未設定の必須環境変数に対して明示的に ValueError を送出。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントをスコアリング。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事上限・文字数トリム、JSON Mode を利用。
    - 再試行（429, 接続断, タイムアウト, 5xx）に対する指数バックオフを実装。
    - レスポンスの厳格なバリデーション実装（JSON パース、results リスト、code/score の検証、数値の有界化）。
    - スコアを ±1.0 にクリップして ai_scores テーブルに冪等的に書き込む（DELETE → INSERT）。
    - ルックアヘッドバイアス防止のため datetime.now 等を参照しない設計（target_date ベース）。
    - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロ記事抽出を実施。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価を実装（JSON レスポンス期待）。
    - API 呼び出しの再試行とフェイルセーフ（API 失敗時は macro_sentiment=0.0 にフォールバック）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK 後に例外を再送出。
    - ルックアヘッドバイアス防止に配慮したデータフィルタリング。

- データプラットフォーム関連 (src/kabusys/data/)
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを提供。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェックあり）。
    - 探索範囲の上限 (_MAX_SEARCH_DAYS) やバックフィル期間などを定義し無限ループや異常データに対処。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装（ETL 実行結果の構造化: 取得数・保存数・品質問題・エラー等）。
    - 差分更新、バックフィル、品質チェック、idempotent 保存 (jquants_client を介した ON CONFLICT 相当) を想定した設計。
    - ETLResult.to_dict() により品質問題を辞書化してログ等に出力可能。

  - jquants_client との連携を想定（fetch/save 関数を呼び出す箇所を実装）。DuckDB を主要 DB として利用。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン・200日 MA 乖離）、Volatility（20日 ATR）、Liquidity（20日平均売買代金等）、Value（PER, ROE）を計算する関数群を実装。
    - DuckDB の SQL を活用して prices_daily / raw_financials から直接集計。
    - 欠損やデータ不足時の None 返却、結果は [{"date","code",...}, ...] 形式を返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB を利用する実装。
    - calc_ic はスピアマンのランク相関を手作り実装し、データ不足時は None を返す。

Other notable implementation details
- 全体で DuckDB を主要な分析 DB として採用。多くのモジュールが DuckDB 接続（DuckDBPyConnection）を引数に受ける設計。
- ロギングを各モジュールで活用し、情報・警告・例外ログを明示的に出力するよう実装。
- LLM 呼び出し部分はテスト容易性を考慮し、内部 _call_openai_api を patch して差し替え可能な設計。
- ルックアヘッドバイアス防止のため、すべての「日付基準処理」は target_date を引数で受け、内部で date.today() を直接参照しない方針。
- データベース書き込みは可能な限り冪等性を確保（DELETE→INSERT や ON CONFLICT 相当の想定）。

Security
- なし（初回リリース）。ただし OpenAI API キー・各種トークンは環境変数で扱う前提。

Deprecated
- なし

Removed
- なし

Migration notes（初回リリース向けの注意）
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能のために OPENAI_API_KEY を設定するか、各 API 呼び出しに api_key を渡す必要があります。
- 必要な DuckDB テーブル（想定）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。
- 自動で .env/.env.local を読み込む動作はプロジェクトルート (.git または pyproject.toml を基準) を探して行います。CI/テスト環境で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

脚注
- 実装はコードベースから推測して記載しています。実運用・他環境への導入前に設定、DB スキーマ、外部 API（J-Quants、OpenAI、kabuステーション 等）の準備を行ってください。