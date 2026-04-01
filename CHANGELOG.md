CHANGELOG.md

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

[Unreleased]
（なし）

[0.1.0] - 2026-04-01
Added
- 初回公開リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- パッケージ初期化:
  - src/kabusys/__init__.py: __version__ と主要サブパッケージ（data, research, ai, ...）の公開設定。
- 環境設定 / ロード:
  - src/kabusys/config.py:
    - .env/.env.local または環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース直前の # をコメント扱い）等に対応。
    - OS 環境変数は protected として上書きから保護する挙動を実装（.env.local は既存 OS 環境を保護しつつ上書き可）。
    - Settings クラスを提供（J-Quants トークン、kabu API、Slack 設定、DB パス、監視閾値、環境・ログレベル判定ユーティリティ等）。
    - 必須環境変数取得時は未設定で ValueError を送出。
- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を UTC 変換して使用。
    - バッチ処理（最大20銘柄/回）、1銘柄あたり記事数・文字数上限（記事数:10、文字数:3000）によるトリム。
    - OpenAI API 呼び出しは JSON Mode を期待し、JSON パース失敗時は本文から最外の {} を抽出して復元を試みる耐性あり。
    - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。API エラー（非再試行対象）はスキップして継続（フェイルセーフ）。
    - DuckDB 0.10 互換性考慮: executemany に空リストを与えないガードを実装（部分書込で既存スコア保護のため DELETE→INSERT の置換方式を採用）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等に書き込む。
    - マクロキーワードで raw_news をフィルタして最大20件を LLM に渡す。LLM モデルは gpt-4o-mini。
    - API 呼び出しはリトライ・バックオフ実装。API失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - レジームスコアはクリップ処理および閾値に基づくラベリングを行う。
- データプラットフォーム / ETL / カレンダー:
  - src/kabusys/data/pipeline.py:
    - ETLResult dataclass を実装し、ETL の取得数／保存数／品質チェック結果／エラー概要を集約可能にした（to_dict で品質問題の簡易表現に変換）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装対象として定義。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を公開（再エクスポート）。
  - src/kabusys/data/calendar_management.py:
    - market_calendar を用いた営業日判定 API を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録有無に応じたフォールバック（登録値優先、未登録日は曜日ベース）で一貫性を保つ実装。
    - calendar_update_job: J-Quants API から差分取得して冪等保存。バックフィルと健全性チェックを実装（直近の再フェッチ / 最大未来日検査）。
    - jquants_client 経由で外部 API を呼び、例外発生時は安全に失敗を処理（0 を返す）。
- 研究（Research）:
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value / Liquidity 系ファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: 財務データ（raw_financials）と株価を組合せて PER / ROE を算出。
    - DuckDB 内でのウィンドウ関数等を活用し、外部 API 呼び出しは行わないように設計。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- いくつかの __init__ により公開 API を整備（research.__init__, ai.__init__ など）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env のパース挙動や OpenAI レスポンスのパース耐性など、現実の運用で想定されるケースに対する堅牢性を実装（quoted value のエスケープ対応、JSON modeで余計な前後テキストが混入した場合の復元等）。

Security
- OpenAI API キーおよび各種トークンは環境変数参照。Settings は必須キー未設定時に ValueError を投げることで、安全な初期化を促す。
- 自動 .env 読み込みはテストや CI のために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known issues / TODO
- src/kabusys/data/pipeline.py の末尾付近に実装上の未完成箇所が見られます（_get_max_date 関数の最後で return date.fro のような未完の記述）。実行時エラーの原因となるため、修正が必要です。
- src/kabusys/data/__init__.py は現状空のプレースホルダです。モジュール公開ポリシーの整理を推奨します。
- DuckDB 依存: executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を想定した互換性処理を含むため、実行環境の DuckDB バージョン差異に注意してください。
- OpenAI SDK については例外クラスの属性差（status_code 等）を考慮した実装を行っていますが、将来的な SDK の変更に備えたテストが必要です。
- Automated tests はソース内に見当たらないため、ユニットテスト／統合テストの追加を推奨します。

Required environment variables (主なもの)
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定（必須）
- OPENAI_API_KEY — OpenAI API 呼び出し時に使用（news_nlp / regime_detector を使う場合必須）
- KABUSYS_ENV — 環境指定（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 各種パス・監視閾値（任意 / デフォルトあり）

Contributors
- コードベースから推測して実装チームによる初期実装。

References
- 内部ドキュメント参照: StrategyModel.md, DataPlatform.md（コード内コメントに準拠した設計方針・処理フローを実装）

このリリースはシステムの初期コア機能（データ ETL、カレンダー管理、リサーチ用ファクター計算、AI によるニュースセンチメント／市場レジーム判定、設定管理）を提供します。上記 Known issues の修正、テスト追加、ドキュメント整備を行ったうえで次のマイナー／パッチリリースを予定してください。