CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - 公開モジュール: data, strategy, execution, monitoring。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して検出）。
    - export KEY=val 形式やクォート、行末コメントのパースに対応する .env パーサを実装。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証
    - 必須変数未設定時は明確な ValueError を送出。

- AI 関連モジュール（OpenAI を用いたニュース解析 / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を入力に、銘柄ごとにまとめたテキストを OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ冪等的に保存する処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）と、1銘柄あたりの最大記事数/文字数トリムを実装。
    - バッチサイズ、リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップ処理を備える。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - フェイルセーフ設計: API失敗時は該当チャンクをスキップし続行、最終的に取得できた銘柄のみを置換（DELETE→INSERT）することで部分失敗時の既存データ保護。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLМセンチメント（重み30%）を合成して market_regime テーブルへ日次レジーム（bull/neutral/bear）を書き込む機能を実装。
    - prices_daily と raw_news を参照。ma200 は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードリストでフィルタ、LLM によるスコア取得は最大記事数制限、APIリトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。失敗時には ROLLBACK を試行し例外を上位へ伝播。

- Research（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）など複数ファクターの計算関数を実装。
    - raw_financials から PER / ROE を取得するバリュー系計算を実装。
    - DuckDB のウィンドウ関数を活用して営業日ベースのラグ/移動平均を計算。データ不足時の None ハンドリングを行う。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（horizons: デフォルト [1,5,21]）を提供（LEAD を利用）。
    - Spearman ランク相関（IC）計算、ランク化ユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリで実装。

- Data（データ取得・管理）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB にデータがない場合は曜日ベースのフォールバック（平日を営業日）を行う。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装。バックフィル・健全性チェック（将来日付が異常な場合スキップ）を備える。
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスおよび ETL パイプラインのユーティリティ関数（差分取得・バックフィル・品質チェック設計）を実装。ETL の結果と品質問題（quality.QualityIssue）を収集可能。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- 基盤・設計ノート（複数ファイルに跨る設計指針）
  - ルックアヘッドバイアス防止: モジュール内部で datetime.today() / date.today() を不用意に参照しない設計（target_date を明示受け取り）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT を想定）して部分失敗の副作用を最小化。
  - API に対してはリトライ・バックオフ・フェイルセーフ（代替値で継続）を採用。
  - DuckDB を想定した SQL を利用（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記 / 必要な外部設定
- 必須環境変数:
  - OPENAI_API_KEY（AI モジュールを使用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 利用）
  - KABU_API_PASSWORD（kabuステーション API 利用）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知機能利用）
- DuckDB を用いるため、ai/research/data モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取ります。期待されるテーブルスキーマ（prices_daily, raw_news 等）はコード内のクエリから参照してください。
- テスト支援:
  - OpenAI 呼び出しは内部で _call_openai_api を経由しており、unittest.mock.patch によって差し替えが可能です（テストでの API モック化を想定）。

既知の制約・設計的決定
- OpenAI への依存に関して、API エラー時は該当処理をスキップまたは中立値で継続する設計（外部障害がシステム全体停止に繋がらないようにする）。
- DuckDB executemany は空リストを受け付けない制約を考慮し、空の書き込みは回避する実装をしている。
- news_nlp / regime_detector は JSON mode を使用し、厳密な JSON 出力を期待するが、パース耐性（前後の余計なテキストから最外の {} を抽出する等）を持たせています。

互換性 / マイグレーション
- 初回リリースのため互換性破壊事項はありません。

作者
- kabusys コードベース（初回公開 v0.1.0）