CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
互換性のあるセマンティックバージョニングを使用しています: https://semver.org/

## [Unreleased]

## [0.1.0] - 2026-03-27

Added
- 初回リリース (バージョン 0.1.0)。
- パッケージのエントリポイントを追加:
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージを公開 (data, strategy, execution, monitoring)。
- 設定・環境変数管理:
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - 複雑な .env 行のパース機能（export プレフィックス、クォート、エスケープ、インラインコメント処理等）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得 helper (_require) と Settings クラスを提供。
    - デフォルト値: KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development）、LOG_LEVEL（INFO）等。
    - 有効な環境値チェック (KABUSYS_ENV、LOG_LEVEL) とユーティリティプロパティ (is_live/is_paper/is_dev)。
- AI 関連:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を算出。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数上限、JSON mode を使った出力想定、レスポンスの厳密バリデーションを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ、失敗時はフェイルセーフでスキップして継続。
    - calc_news_window(target_date) による JST ベースのニュース集計ウィンドウ計算（ルックアヘッド回避）。
    - score_news(conn, target_date, api_key=None) が ai_scores テーブルへ冪等的に書き込む（DELETE→INSERT）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して市場レジーム ('bull'/'neutral'/'bear') を判定。
    - ma200_ratio の計算、マクロキーワードでのニュースフィルタ、OpenAI 呼び出し（gpt-4o-mini）と JSON 解析、重み合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
- Research（ファクター計算・特徴量探索）:
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金・出来高比率等を計算。
    - calc_value: raw_financials の最新財務データと当日株価から PER・ROE を算出。
    - DuckDB を用いた SQL ベースの実装で、外部 API や取引 API へはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（例: 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: Spearman（ランク）に基づく IC を計算（必要レコード 3 件未満で None）。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めで ties の扱いを安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - re-export: src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize は kabusys.data.stats から）。
- Data プラットフォーム関連:
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルを用いた営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェックと冪等保存ロジック実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult dataclass を含む ETL パイプライン用ユーティリティ（差分取得、保存、品質チェックの設計思想を実装）。
    - ETL 結果の構造化（品質問題のサマリ変換等）。
  - jquants_client など外部クライアントの呼び出しは data パッケージ内で分離（モジュール設計）。
- ロギング/安全性/設計上の注意点（ドキュメント化）:
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接利用しない関数設計。
  - DuckDB に対する executemany の空パラメータ回避、ROLLBACK の保護ログ、非破壊的な部分書き換え（コード絞り込み）などの堅牢化。
  - OpenAI API 呼び出しは JSON mode を想定し、パース失敗・余計な前後テキスト混入などの復元処理を備える。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Security
- 該当なし（初回リリース）。ただし環境変数・APIキーの取り扱いに注意。

Notes / ユーザー向け移行・運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - これらは Settings プロパティ経由で取得され、未設定時は ValueError を送出する場合があります。
- 自動 .env 読み込み:
  - デフォルトでプロジェクトルートの .env と .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI:
  - デフォルトでモデル gpt-4o-mini を想定し、JSON mode のレスポンスを期待します。API 呼び出し失敗時は多くの場合フェイルセーフ（0.0 やスキップ）で継続しますが、APIキー未設定時は明示的に ValueError を送出します。
- データベースのデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 互換性:
  - 本リリースは内部で DuckDB を利用します。DuckDB のバージョンによる executemany の挙動差分（空リスト不可等）を考慮した実装になっていますが、運用時は DuckDB の互換性に留意してください。

Acknowledgements
- 本パッケージはデータ収集（J-Quants 想定）、DuckDB による分析、OpenAI によるニュース NLP を組み合わせた研究・運用向け基盤を提供します。今後のリリースで機能拡張・安定化・ドキュメント充実を予定しています。