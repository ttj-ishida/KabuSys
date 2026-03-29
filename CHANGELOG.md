CHANGELOG
=========

すべての変更は Keep a Changelog の原則に従って記述しています。  
セマンティックバージョニングを採用しています。詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース: kabusys パッケージ（__version__ = 0.1.0）。
- 環境設定:
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）による .env / .env.local の自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env ファイルパースの堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - Settings クラスを提供し、必須環境変数の取得、KABUSYS_ENV / LOG_LEVEL の検証、データベースパス（DUCKDB_PATH/SQLITE_PATH）などを公開。
- AI（NLP）:
  - kabusys.ai.news_nlp:
    - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄単位のセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む機能を実装。
    - ニュース収集ウィンドウの厳密定義（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチサイズ制御、記事数・文字数トリム、JSON モードレスポンスの検証・復元（前後テキスト混入対策）を実装。
    - リトライ（指数バックオフ）、429 / ネットワーク断 / タイムアウト / 5xx の扱い、API 失敗時のフェイルセーフ（スキップ）を実装。
    - テスト用に _call_openai_api を patch 可能（単体テスト容易化）。
    - DuckDB の executemany の制約を考慮した DELETE→INSERT の冪等書き込みロジック。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離とマクロニュース（LLM）を重み付け合成し、市場レジーム（bull / neutral / bear）を日次判定する score_regime を実装。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロキーワードによる記事抽出、LLM 呼び出し（gpt-4o-mini）と再試行ロジックを実装。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- データプラットフォーム:
  - kabusys.data.pipeline / ETL:
    - ETLResult データクラスを実装して ETL の収集結果（取得件数・保存件数・品質問題・エラーメッセージなど）を整理。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client 経由の差分取得、idempotent 保存、品質検出は集計して呼び出し元に委ねる）。
  - kabusys.data.calendar_management:
    - market_calendar を扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索範囲の安全策、バックフィル・健全性チェックを実装。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新するジョブを実装（バックフィル・サニティチェック付き）。
- リサーチ（ファクター計算・特徴量探索）:
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB SQL を用いて価格・財務データからモメンタム／ボラティリティ／バリュー指標を計算。
    - 欠損やデータ不足時の取り扱い（None を返す等）を明確化。
  - kabusys.research.feature_exploration:
    - calc_forward_returns, calc_ic（Spearman の ρ ランク相関）, rank, factor_summary を実装。
    - pandas 等に依存しない純標準ライブラリ実装で、IC 計算や統計サマリーを提供。
  - research パッケージで必要関数を __all__ 経由で再公開。
- パッケージ公開インターフェース:
  - kabusys.__all__ に主要サブパッケージ（data, strategy, execution, monitoring）を設定（将来拡張を想定）。
- ロギングとデバッグ:
  - 各モジュールで詳細なログ出力（info/debug/warning/exception）を配置し、失敗時の挙動を明示。
- テスト容易性:
  - OpenAI 呼び出しまわりに patch 可能なホックを用意（ユニットテストで外部依存を差し替え可能）。

Changed
- （初回リリースのため該当なし）

Fixed
- レスポンスパースや API エラー処理に関する堅牢化を多数実装:
  - OpenAI API の APIError に対して status_code を安全に取得するため getattr を使用。
  - JSON mode で前後テキストが混入した場合に外側の {} を抽出して復元するロジックを実装。
  - LLM が数値でなく整数や別型でコードを返すケースに備えて code を文字列化して照合。
  - DuckDB からの戻り値の日付変換ユーティリティ (_to_date) を実装して互換性を確保。
  - True Range / ATR 計算で NULL の伝播を明示的に扱いカウントの過大評価を防止。

Security
- 環境変数を必須にするキー（OpenAI / Slack / KabuStation など）は Settings 経由で取得し、未設定時は ValueError を発生させることで明示的なエラーを出力（誤設定を早期発見）。
- .env 読み込み時に OS 環境変数を protected として上書きを防止する挙動を採用。

Notes / Design decisions
- すべてのスコアリング・ファクター計算は datetime.today() / date.today() 等の実行時現在時刻参照を避け、target_date を明示的に受け取る設計によりルックアヘッドバイアスを排除。
- 外部 API 呼び出し失敗時は原則フェイルセーフ（ゼロやスキップ）で継続するようにし、ETL/スコアの一部失敗が全体停止を引き起こさないよう配慮。
- DuckDB のバージョン差分や API の制約（executemany の空リスト不可など）を考慮した実装上の互換性対応を行っている。

今後の予定（例）
- strategy / execution / monitoring 実装の追加（現状はパッケージ公開のプレースホルダあり）。
- 単体テストの充実（モックを使った OpenAI / J-Quants / KabuStation の CI テスト）。
- ドキュメント整備（使用例・運用手順・ETL/job の運用スケジュール）。

--- 

変更点に不明点や補足の希望があれば、どのモジュールについて詳述するか教えてください。