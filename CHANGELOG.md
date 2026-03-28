Changelog
=========
すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
安定バージョンへ移行する際は、セマンティックバージョニング (MAJOR.MINOR.PATCH) を使用してください。

[Unreleased]
------------

- 今のところ未リリースの変更はありません。

[0.1.0] - 2026-03-28
-------------------

初回リリース — 基本機能群の実装とエンドツーエンドでの設計方針を含みます。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 設定・環境変数管理
  - robust な .env 読み込みロジック（src/kabusys/config.py）を実装。
    - プロジェクトルートを __file__ から探索して .env / .env.local を自動読み込み（.git または pyproject.toml を基準）。
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応するパーサ実装。
    - OS 環境変数を保護する protected パラメータ、override 制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを提供し、アプリケーションで使う設定値をプロパティ経由で取得可能に。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）と妥当性チェック（env / log_level の許容値）。
    - is_live / is_paper / is_dev のユーティリティフラグ。

- AI モジュール（OpenAI 統合）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - gpt-4o-mini（JSON Mode）へバッチ送信（最大 20 銘柄/チャンク）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフ実装。
    - レスポンス検証、スコアの ±1.0 クリップ、ai_scores テーブルへの冪等書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - calc_news_window(target_date) ユーティリティ（JST ウィンドウ定義）を提供。
    - score_news(conn, target_date, api_key=None) を公開：書き込んだ銘柄数を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定。
    - マクロキーワードで raw_news をフィルタ → gpt-4o-mini で JSON 応答（{"macro_sentiment": ...}）を期待。
    - API 呼び出しの堅牢化（リトライ、5xx 判定、フェイルセーフで macro_sentiment=0.0）。
    - レジーム合成ロジック、閾値に基づくラベル付与（bull/neutral/bear）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開：成功時に 1 を返す。
  - 共通設計方針
    - 両モジュールとも datetime.today() / date.today() を内部参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを防止。
    - OpenAI クライアントは明示的に作成（api_key 注入可能）。テストのための差し替えポイントを用意。

- データプラットフォーム関連
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーなどを集約）。
    - 差分取得、バックフィル、品質チェックの設計方針を反映。
    - pipeline の ETLResult を再エクスポート（data.etl）。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティを提供。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日（週末）ベースでフォールバックする一貫した設計。
    - calendar_update_job(conn, lookahead_days=...) により J-Quants API から差分取得して market_calendar を冪等更新（バックフィル / 健全性チェック含む）。
    - DuckDB からの型変換・テーブル存在チェック等のユーティリティを実装。

- リサーチ / ファクター
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None）。
    - calc_volatility(conn, target_date)：20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算。
    - calc_value(conn, target_date)：raw_financials から EPS/ROE を参照して PER, ROE を計算（EPS=0/欠損は None）。
    - 全関数とも DuckDB SQL を用いた実装で、外部 API へはアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None)：将来リターン（複数ホライズン）をまとめて取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）を計算。サンプル数不足時は None。
    - rank(values)：同順位を平均ランクで処理する安定的なランク化ユーティリティ。
    - factor_summary(records, columns)：count/mean/std/min/max/median の統計サマリを返す。
    - いずれも pandas 等非依存で標準ライブラリ + DuckDB を前提とした実装。

- テスト性・互換性メモ
  - OpenAI 呼び出し箇所は内部関数を patch することでユニットテストが可能（_call_openai_api を差し替え）。
  - DuckDB 0.10 の executemany の制約（空リスト不可）を考慮した実装になっている箇所あり（ai_scores 等）。

Changed
- 初版リリースのため「Changed」は該当なし。

Fixed
- 初版リリースのため「Fixed」は該当なし。

Security
- 初版リリースのため「Security」は該当なし。
- 注意: 必須環境変数（例: OPENAI_API_KEY 等）は外部に漏えいしないよう実運用での管理を推奨。

Notes / 運用上の注意
- 必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime 呼び出し時に必要）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings で参照）
- OpenAI モデルは gpt-4o-mini を想定、JSON Mode を利用するプロンプト設計になっているため API レスポンスのフォーマットに依存します。
- DuckDB をデータ層として前提。DB スキーマ（tables: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が整備されていることが必要です。
- ルックアヘッドバイアス対策として、日付は全て呼び出し側から与える target_date を使用する設計です。内部で date.today()/datetime.today() を参照しない点に注意してください。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの充実（実注文 API 連携・バックテスト・実時監視）。
- テストカバレッジ拡充と CI ワークフロー整備。
- OpenAI レスポンス検証の更なる強化（スキーマ検証・スキーマ違反時のリカバリ手段）。
- パフォーマンス改善（大量銘柄処理時のメモリ/トークン使用最適化）。

-----