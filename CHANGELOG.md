Keep a Changelog 形式に準拠した変更履歴（日本語）
※この CHANGELOG はソースコードの内容から推測して作成しています。

全般ルール:
- フォーマットは「Keep a Changelog」に準拠しています。
- バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に基づいています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
-------------------

Added
- 初期リリース: 日本株自動売買／データプラットフォーム用ライブラリ kabusys を追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"
  - 公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ に基づく）
- 環境設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む機能を実装。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応したパーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
  - 必須環境変数取得用 _require と Settings クラスを提供。主な設定項目:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
- AI モジュール (kabusys.ai)
  - news_nlp.score_news: raw_news / news_symbols を集約して OpenAI Chat（gpt-4o-mini、JSON Mode）で銘柄別センチメントを算出し ai_scores テーブルへ書き込む。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり最大記事数/文字長でトリムする仕組みを実装。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）を指数バックオフで処理。失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスのバリデーションと ±1.0 のクリッピングを実施。
    - calc_news_window 関数で JST のニュースウィンドウ（前日15:00〜当日08:30）を UTC naive datetime で計算。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタ、最大 _MAX_MACRO_ARTICLES 件を LLM に渡して macro_sentiment を算出。
    - OpenAI 呼び出しは専用の内部実装で、API失敗時は macro_sentiment=0.0 として処理を継続（フェイルセーフ）。
    - ルックアヘッドバイアス対策として date 比較において target_date 未満のデータのみ使用し、datetime.today() を直接参照しない設計。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等の計算を実装。
    - calc_value: raw_financials から最新財務データを取得して PER・ROE を計算（EPS が 0/欠損だと PER は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）までの将来リターンを計算。ホライズン検証（1〜252日）あり。
    - calc_ic: スピアマンランク相関（IC）の計算。サンプル数が少なければ None を返す。
    - rank: 同順位は平均ランクで処理（浮動小数点誤差を防ぐため round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar を用いた営業日判定・next/prev/get_trading_days/is_sq_day）を実装。
    - カレンダーが未取得の場合は曜日ベース（平日のみ営業日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して市場カレンダーを更新（バックフィル・健全性チェック対応）。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行結果の集約、品質チェック問題の収集、エラーフラグ等）。
    - pipeline モジュールに ETL 補助関数（テーブル存在チェック、最大日付取得、トレーディング日調整等）を実装。
  - jquants_client / quality などの外部クライアント連携を前提とした設計（実装は別モジュールとして想定）。
- 設計と実装上の注意点（ドキュメント化）
  - 各種関数はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない方針。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK を使用）。
  - DuckDB（kabusys は DuckDB 接続を引数に取る関数が多数）を想定した SQL 実装。
  - OpenAI への問い合わせは JSON Mode を使う想定で、レスポンスの厳密な JSON を期待（だがパース耐性を持たせる）。
  - API 呼び出しに対してはリトライ／バックオフや 5xx の挙動判定など堅牢化を実施。

Changed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Fixed
- 該当なし（初期リリース）。

Security
- 環境変数の自動ロード時、既存の OS 環境変数を protected セットとして上書きから保護する実装あり（.env/.env.local の読み込みロジック）。
- OpenAI / J-Quants / Kabu API 等の秘密情報は必須環境変数として明示。自動ロードを無効化する環境変数も提供。

Notes / Known Requirements
- 必須外部サービス／環境変数:
  - OPENAI_API_KEY（news_nlp.score_news / regime_detector.score_regime 利用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD, KABU_API_BASE_URL（ローカルテスト用デフォルト指定あり）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトのローカル DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI モデル: gpt-4o-mini を想定（JSON mode での利用）。
- DuckDB クエリはバージョン差分に敏感なため（例: executemany に空リスト不可等）、互換性に配慮した実装となっている。

開発者向けメモ（実装上の設計決定）
- OpenAI 呼び出し用の内部関数はモジュール毎に独立実装しており、テスト時は該当関数を patch して差し替え可能。
- LLM の失敗はフェイルセーフとして 0.0（中立）やチャンクスキップで継続する方針。
- DB 書き込みは部分失敗時に既存データを不必要に削らない（対象コードを限定して DELETE→INSERT）設計。

References
- 各モジュールの関数名や定数はソースコードコメントや docstring を参照して推測しています（例: calc_news_window, score_news, score_regime, calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, calendar_update_job, ETLResult など）。

もし CHANGELOG に追加したい別の観点（例: 重要な使用例、API レベル互換注意点、リリース後に予定している改善点など）があれば教えてください。追記・修正して反映します。