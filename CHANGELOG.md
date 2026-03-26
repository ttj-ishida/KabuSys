CHANGELOG
=========

すべての注記は Keep a Changelog の形式に準拠しています。

0.1.0 - 2026-03-26
-----------------

Added
- 初回公開リリース。
- パッケージ概要:
  - kabusys: 日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供。
  - バージョン: 0.1.0
  - パブリックモジュール: data, research, ai, config, （および strategy / execution / monitoring を __all__ に含める記載あり）。
- 環境設定・自動 .env ロード:
  - 環境変数を扱う settings クラスを提供（kabusys.config.settings）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 複雑な .env パース実装（export 形式、クォート内のエスケープ、インラインコメントの扱い等）。
  - 以下の必須環境変数を検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック、is_live/is_paper/is_dev のユーティリティ）。
- AI ニュース・レジーム判定:
  - kabusys.ai.news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄別にニュースを LLM（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、記事/文字数制限、JSON Mode のレスポンスバリデーション、スコアの ±1.0 クリップ、部分書き込み（失敗時に他銘柄スコアを保護）を実装。
    - ネットワークエラー・429・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - テスト用に _call_openai_api をパッチ差し替え可能（unittest.mock.patch 用想定）。
  - kabusys.ai.regime_detector.score_regime:
    - ETF 1321（Nikkei225 連動）200 日移動平均乖離（重み 70%）と、上記ニュースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出・market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出（キーワードフィルタ）、OpenAI 呼び出し、リトライ / フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策: date 未満のデータのみ参照、datetime.today()/date.today() を直接参照しない設計。
- データ基盤（Data）:
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫性を確保。
    - カレンダー夜間更新ジョブ calendar_update_job を提供（J-Quants から差分取得、バックフィル・健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl.ETLResult を再エクスポート）。
    - 差分取得、保存（idempotent 保存: ON CONFLICT / executemany の扱いに配慮）、品質チェックの枠組みを実装するパイプライン基盤（jquants_client と quality モジュールを利用）。
    - DuckDB 固有の注意点を考慮した実装（executemany に空リストを渡さない等）。
- リサーチ機能（research）:
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日 MA 乖離）計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: PER（株価/EPS）、ROE を raw_financials と prices_daily から算出。
    - DuckDB 内で SQL ウィンドウ関数を用いて効率的に処理、データ不足時は None を返す挙動。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD 関数で一括取得。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - factor_summary / rank: 基本統計量・ランク計算（平均ランク、同順位は平均ランク）を提供。
- ドキュメント・設計方針の明記:
  - 各モジュールにルックアヘッドバイアス回避、フェイルセーフ（API失敗時のフォールバック）、テスト容易性（内部呼び出しの差し替え可能）など設計意図を詳細にコメント。

Security
- 特になし（初回リリース）。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Notes / Known limitations
- OpenAI を使用する機能（score_news, score_regime）は実行時に OPENAI_API_KEY が必要（api_key 引数で注入可能）。未設定時は ValueError を発生。
- デフォルトで使用するモデルは gpt-4o-mini（response_format JSON mode を利用）。
- DuckDB のバージョン差異により SQL バインドの振る舞いが異なるため、executemany の空パラメータ回避等の実装が含まれる（DuckDB 0.10 互換性を考慮）。
- .env 自動ロードはプロジェクトルート検出に依存（.git か pyproject.toml が必要）。プロジェクト配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止可能。
- ai モジュールは外部 API に依存するため、ネットワーク/API 制限により部分的に結果が取得できないことがある。その場合は該当処理をスキップし、他データへの影響を最小化するよう設計。

Upgrade notes
- なし（初回リリース）。将来的なリリースでは OpenAI SDK の変更や DuckDB バージョン差分に伴う互換性注記を追加予定。

Contributing
- バグ報告・機能要望はリポジトリの Issue へ。
- テスト容易性のため、OpenAI 呼び出し等はモジュール内で差し替え可能な設計になっています（unittest.mock.patch を想定）。

---