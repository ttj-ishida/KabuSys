Keep a Changelog
=================
すべての重要な変更をこのファイルに記録します。  
このプロジェクトは、"Keep a Changelog" のガイドラインに従います。

フォーマット
-----------
各リリースは日付付きで記載し、Added / Changed / Fixed / Security 等のカテゴリで整理しています。

[Unreleased]
------------
（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------
初回リリース（初期実装）

Added
-----
- パッケージ基盤
  - kabusys パッケージの初期実装を追加（__version__ = 0.1.0）。
  - パッケージ公開 API として data, research, ai, config 等のモジュールを提供。

- 環境設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない読み込みを実現。
  - .env 行パーサ (_parse_env_line): export 構文、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応する堅牢なパーサを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の設定プロパティを取得可能（必須環境変数未設定時は ValueError を発生）。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算 (calc_news_window) が JST 時間帯（前日15:00〜当日08:30）を UTC に変換して処理。
    - 1チャンクあたり最大20銘柄のバッチ処理、1銘柄あたりの記事数／文字数上限、JSON バリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API エラー時は安全にスキップ（フェイルセーフ）。
    - レスポンスパースの頑健化（最外の {} を抽出するフォールバック）を実装。
    - DuckDB 互換性への配慮（executemany に空リストを渡さない等）。
  - regime_detector.score_regime: ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを実施。
    - ma200_ratio 算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）のリトライ・フォールバック実装（API 失敗時は macro_sentiment=0.0）。
    - レジーム合成ロジック、閾値（bull/bear）および idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データモジュール (kabusys.data)
  - calendar_management: market_calendar テーブルを用いた営業日判定・探索ロジックを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB 登録がない日については曜日ベース（平日のみ営業）でのフォールバックを実装し、DB がまばらでも一貫性を保つ設計。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API から差分取得 → 保存、バックフィル・健全性チェックを含む）。
  - pipeline.ETLResult: ETL 実行結果を保持する dataclass を追加（品質問題リスト／エラー一覧／to_dict 等を実装）。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチモジュール (kabusys.research)
  - factor_research: ファクター計算関数を追加
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日株価から PER（EPS が 0/欠損のケースは None）と ROE を計算。
    - DuckDB による SQL / ウィンドウ関数中心の実装で外部 API に依存しない。
  - feature_exploration: 解析補助関数を追加
    - calc_forward_returns: 指定ホライズン先（営業日ベース）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク相関 IC）を計算。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め誤差対策を含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - data.stats.zscore_normalize を re-export（research パッケージ初期公開）。

Design / その他の注記
-------------------
- ルックアヘッドバイアス対策:
  - 多くの関数（score_news, score_regime, calc_* 等）は内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を渡す設計としている。
  - DB クエリでは target_date 未満／排他条件を厳守することで先読みを防ぐ。
- フェイルセーフ設計:
  - 外部 API（OpenAI, J-Quants 等）での失敗時は可能な限り処理を継続し、安全な既定値（例: macro_sentiment=0.0）でフォールバックする。
  - DB 書き込みは冪等性/トランザクション（BEGIN/COMMIT/ROLLBACK）を考慮。
- ロギング:
  - 各モジュールは詳細なログ（INFO/WARNING/DEBUG）を出力するよう設計。
- DuckDB 互換性:
  - executemany の空リスト回避や日付型の扱い等、DuckDB のバージョン差分を考慮した実装上の注意をコメントに明記。

Known limitations / Notes
-------------------------
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する関数がある。
- 一部の DB 操作は DuckDB のバージョン差に依存する挙動があり、運用時は DuckDB の互換性確認を推奨。
- 現時点で PBR・配当利回りなどの一部バリューファクターは未実装（calc_value の注記参照）。
- news_nlp / regime_detector の OpenAI 呼び出しはテスト容易性のため内部呼び出し関数を patch 可能にしている（ユニットテストで差し替え可能）。

参考: 主要な公開 API（関数 / クラス）
-----------------------------------
- kabusys.config.settings (Settings)
  - jquants_refresh_token, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等のプロパティ
- kabusys.ai.news_nlp
  - calc_news_window(target_date)
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_management
  - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.pipeline.ETLResult
- kabusys.research.factor_research
  - calc_momentum, calc_volatility, calc_value
- kabusys.research.feature_exploration
  - calc_forward_returns, calc_ic, factor_summary, rank
- その他、内部ユーティリティ関数は各モジュールの docstring を参照してください。

----
今後の予定（例）
- 更なるファクター追加（PBR、配当利回り等）
- モデル学習用の特徴量保存/管理機能強化
- テストカバレッジ拡充（外部 API モックを用いた統合テスト）
- OpenAI 呼び出しの抽象化と複数プロバイダ対応検討

以上。