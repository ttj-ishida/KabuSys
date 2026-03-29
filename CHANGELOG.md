Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを採用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買／データ分析プラットフォームの基礎機能を追加。
  - パッケージ:
    - kabusys (バージョン 0.1.0)
  - コア:
    - パッケージ公開インターフェースを定義（__all__ に data, strategy, execution, monitoring）。
  - 設定/環境変数管理 (kabusys.config):
    - .env / .env.local の自動読み込み機能（プロジェクトルート探索: .git または pyproject.toml を基準）を実装。
    - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント判定をサポート。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - OS 環境変数を保護する protected 上書きロジック（.env.local は上書き可だが OS 変数は保護）。
    - 必須環境変数チェック関数 _require と Settings クラスを提供。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH のデフォルトパス
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev のユーティリティ
  - AI モジュール (kabusys.ai):
    - news_nlp:
      - raw_news と news_symbols をもとにニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメント評価。
      - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数・文字数でトリム、レスポンス検証、スコア ±1.0 にクリップ。
      - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時はスキップして継続）。
      - テスト用に _call_openai_api をモック可能（unittest.mock.patch に対応）。
      - score_news(conn, target_date, api_key=None): ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT、DuckDB executemany の空リスト対応考慮）。
      - ニュース収集ウィンドウ（JST基準）を calc_news_window で計算（前日15:00～当日08:30 JST の UTC 対応）。
    - regime_detector:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム判定（bull / neutral / bear）。
      - マクロニュース抽出はマクロキーワードリストに基づくタイトル検索、最大記事数制限、OpenAI 呼び出しは JSON レスポンスを想定。
      - API 再試行・5xx 判定・フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
      - score_regime(conn, target_date, api_key=None): market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - Data / ETL / カレンダー (kabusys.data):
    - calendar_management:
      - market_calendar を基にした営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar 未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
      - next/prev_trading_day の最大探索日数上限を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
    - pipeline / etl:
      - ETLResult データクラス（ETL の計測値、品質問題・エラーの収集、辞書変換メソッド to_dict）を実装・公開。
      - 差分取得、保存（idempotent）、品質チェックの設計方針を反映（詳細はモジュール内 docstring）。
    - DuckDB を前提とした SQL 実装と互換性配慮（日付変換ユーティリティ等）。
  - Research (kabusys.research):
    - factor_research:
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）などの定量ファクター計算を実装。
      - prices_daily / raw_financials のみを参照。結果は (date, code) を含む dict のリストで返す。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic、Spearmanランク相関）、rank、統計サマリー（factor_summary）を提供。
      - pandas 等外部依存を使わずに標準ライブラリで実装。
    - data.stats の zscore_normalize を再エクスポート。
  - その他の品質・設計上の配慮:
    - ルックアヘッドバイアス回避: date / target_date ベースの処理とし、datetime.today()/date.today() を参照しない設計を明記。
    - DB書き込みは冪等性を重視（DELETE→INSERT、トランザクション、ROLLBACK 保護）。
    - DuckDB 0.10 の制約（executemany に空リスト不可）への対策を組み込み。
    - ロギングと警告を多用し、異常系での情報を残す設計。

Fixed
- （初回リリースのため無し）

Changed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- OpenAI API キーや各種トークンは引数または環境変数で供給する必要あり。未設定時は ValueError を送出して安全に失敗する振る舞いを採用。
- .env 読み込み時に OS 環境変数を保護する実装を追加（重要な環境変数の意図しない上書きを防止）。

Notes / Known limitations
- 一部実装は J-Quants クライアント（kabusys.data.jquants_client）や外部 API を前提としている（本コード内に API クライアント本体は含まれない想定）。
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を前提とした実装。将来的な SDK 変更に伴う調整が必要になる可能性がある。
- ai/regime/news モジュールは API 失敗時のフォールバックを備えるが、長期間の API 全滅状態ではスコアが得られないことに注意。
- DuckDB のバージョン差異により一部の SQL バインド挙動が変わるため互換性注意（executemany 空リスト対応などの配慮を実装済み）。

ライセンス・著者情報等は別ファイル（pyproject.toml / LICENSE）を参照してください。