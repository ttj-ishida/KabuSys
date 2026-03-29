# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
版番号は semver に従います。

現行日付: 2026-03-29

Unreleased
----------
（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ公開:
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - top-level エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイル / 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - OS側の既存環境変数は保護され、上書きされない実装（protected set）。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出ロジック: __file__ から親ディレクトリを探索し .git または pyproject.toml を基準に特定（配布後も動作するよう設計）。
    - .env パーサは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを公開（settings インスタンス）。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値: KABUSYS_ENV=development, LOG_LEVEL=INFO。
    - 有効値検査: KABUSYS_ENV ∈ {development, paper_trading, live}、LOG_LEVEL は標準ログレベル。
    - DB パスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 利用補助プロパティ: is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - ニュースセンチメント集計: score_news (kabusys.ai.news_nlp)
    - 対象ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う（calc_news_window を提供）。
    - raw_news / news_symbols を集約して銘柄ごとにテキストを作成、最大記事数・最大文字数でトリム。
    - OpenAI（gpt-4o-mini）へバッチ（最大 20 銘柄/リクエスト）で送信、JSON Mode を使用して厳密な JSON レスポンスを期待。
    - エラー処理: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（設定可能な最大リトライ回数・初回待機秒数）。
    - レスポンス検証: JSON パース、"results" 配列、各要素の code と score チェック、スコアを ±1.0 にクリップ。
    - DB への書き込みは部分失敗を防ぐため、スコア取得済みコードのみを DELETE → INSERT で置換（トランザクション内、DuckDB executemany 空リスト回避済み）。
    - API 呼び出し箇所は _call_openai_api で抽象化され、テスト時に patch 可能。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定: score_regime (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジームを判定（bull/neutral/bear）。
    - MA 計算では target_date 未満のデータのみ使用してルックアヘッドを排除。データ不足時は中立(1.0)を採用。
    - マクロキーワードによる raw_news フィルタリングを実施し、最大記事数を制限。
    - OpenAI 呼び出しは独立実装でテスト差し替え可能。API エラー時は macro_sentiment=0.0（フェイルセーフ）にフォールバック。
    - 最終的な market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、書き込み失敗時は ROLLBACK を試行して例外を伝播。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルの有無に応じて DB 値を優先し、未登録日は曜日（平日）ベースでフォールバックする一貫したロジックを実装。
    - next/prev_trading_day は最大探索日数制限を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を更新、バックフィル（直近 _BACKFILL_DAYS 日）と健全性チェック（将来日付の異常判定）を実施。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、保存（jquants_client を利用した idempotent 保存）、品質チェック（quality モジュール）を想定した設計。
    - ETLResult に品質問題やエラーの要約を格納・辞書化するユーティリティを実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、market_calendar への適応ロジック等。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、ATR/価格の比率、20 日平均売買代金、出来高比率を計算。欠損時は None。
    - calc_value: raw_financials から直近の財務データを取得し PER/ROE を計算（EPS が 0 または欠損時に None）。
    - DuckDB のウィンドウ関数を活用し、パフォーマンスと精度に配慮した実装。
  - 特徴量探索・統計 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。horizons の検証を実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（同値処理は平均ランクを採用）。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクにする安定実装（比較前に round(v, 12) で丸め）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数を提供。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

Security
- なし（このリリース内でのセキュリティ修正はありません）。

Known issues / Notes
- OpenAI API への依存:
  - API キーが未設定の場合、score_news/score_regime は ValueError を送出する設計。
  - API の一部失敗はフェイルセーフ（スコア=0.0 やスキップ）で継続するが、運用上は監視が必要。
- .env パーサは一般的なケースに対応しているが、特殊な .env 表記（複雑なネスト・非標準拡張）では動作しない可能性あり。
- DuckDB の executemany に対するバグやバージョン差異を考慮して空リストパスを明示的に回避する実装を行っているが、将来の DuckDB バージョンで振る舞いが変わる可能性がある。
- 全体設計としてルックアヘッドバイアスを避けるため、内部で datetime.today() / date.today() を参照しない方針を採用しているが、calendar_update_job は実行時の date.today() を使用する（バッチ実行向け）。

Migration notes
- 初回リリースのため、マイグレーションはありません。

Authors
- KabuSys 開発チーム（コードベースから推測して作成）

README / Usage
- 各モジュールのトップに docstring と使用例コメントを配置しています。API キーや DB パス等は環境変数で設定してください。

以上。今後のリリースではバグ修正・APIの堅牢化・追加のファクタ/ストラテジー等を予定しています。