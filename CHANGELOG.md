KEEP A CHANGELOG
すべての重要な変更をこのファイル（Keep a Changelog 準拠）に記録します。

フォーマット:
- 各リリースに対して Added / Changed / Fixed / Deprecated / Removed / Security 等の見出しで要点を記載します。
- 日付はリリース日を示します。

Unreleased
- （現時点なし）

0.1.0 - 2026-03-31
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開 API: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]
  - バージョン定義: kabusys.__version__ = "0.1.0"

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - オプション/デフォルト: KABU_API_BASE_URL, DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション（許容値を限定）
    - is_live / is_paper / is_dev のユーティリティプロパティを提供

- AI 関連機能 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのセンチメント ai_score を計算し ai_scores テーブルへ書き込む score_news 関数を実装。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - OpenAI（gpt-4o-mini）を JSON mode で利用、バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、トークン肥大対策（_MAX_CHARS_PER_STOCK）を実装。
    - エラー耐性: 429 / ネットワーク / タイムアウト / 5xx サーバーエラーを指数バックオフでリトライ、最終的に部分失敗を許容して他銘柄データを保護する設計（部分書き換えロジック）。
    - レスポンス検証ロジックを実装（JSON 抽出、results 配列チェック、コード照合、スコア数値検証、±1.0 にクリップ）。
    - テスト容易性: _call_openai_api をパッチ可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（70%）とマクロニュースの LLMセンチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - prices_daily, raw_news, market_regime テーブルを利用し、冪等的に market_regime に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数共有しない）で、API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - API リトライ・バックオフ/レスポンスパース妥当性チェックを実装。

- データプラットフォーム (kabusys.data)
  - ETL インターフェース (kabusys.data.pipeline, etl)
    - ETLResult データクラスを公開し（ETL の集計・品質問題・エラーの保持）、to_dict によるシリアライズを提供。
    - 差分取得、バックフィル、品質チェックの基盤設計を実装（J-Quants クライアント経由の差分保存を想定）。
    - DuckDB 互換性に配慮した実装（executemany の空リスト回避等）。
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値を優先しつつ、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを実装。
  - jquants_client を使ったデータフェッチ / 保存の想定で設計（実装は jquants_client モジュールに依存）。

- 研究（research）モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算。
    - DuckDB 上で SQL と Python を組み合わせた高効率実装。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
    - calc_ic: ランク相関（Spearman ρ）を実装（結合・欠損処理・最小レコード制約あり）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（round を用いた同値対策）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数。
  - zscore_normalize を data.stats から再エクスポート。

- 設計方針 / 共通実装上の特徴
  - ルックアヘッドバイアス対策: 各所で datetime.today()/date.today() を直接参照しない実装（target_date を引数で渡す設計）。
  - DuckDB を中心にテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）前提で動作。
  - DB 書き込みは冪等性・トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - OpenAI 呼び出しに対して堅牢なエラー/リトライ/パース保護を追加。
  - ログ出力により不足データ・API エラー等を可視化。

Changed
- （初版なので該当なし）

Fixed
- （初版なので該当なし）

Deprecated
- （初版なので該当なし）

Removed
- （初版なので該当なし）

Security
- .env の読み込みで OS 環境変数を保護するため protected set を導入（.env/.env.local の上書き制御）。
- 必須シークレット（OpenAI API キー・Slack トークン等）は明示的に必須扱い（未設定時は ValueError）。

Notes / Known limitations
- OpenAI 依存: score_news / score_regime は OpenAI API（gpt-4o-mini）を利用。API キーは api_key 引数または環境変数 OPENAI_API_KEY が必要。
- DB スキーマ依存: 複数関数は特定のテーブル・カラムを前提（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar 等）。スキーマが一致しない場合はエラーとなる。
- 部分失敗許容設計: AI 呼び出し失敗時はスコア計算をスキップして残りの銘柄や既存データを保護する戦略を採用。これは堅牢性重視の設計であるが、完全性を保証するものではない。
- DuckDB 互換性: executemany の使用やリストバインドに関する実装は DuckDB のバージョン差分に配慮しているが、古い/新しいバージョンで挙動差が出る可能性がある（explicit な注釈あり）。
- strategy / execution / monitoring パッケージはパッケージ公開対象に含まれるが、本リリース内での実装状況はモジュール全体の一部のみ（将来的な実装拡張を想定）。

Contributors
- 初版コードベースに基づく自動生成の変更履歴（実際の貢献者情報はソース管理のコミットログを参照してください）。

--- 
（注）本 CHANGELOG は提示されたソースコードの内容・コメント・設計記述から推測して作成しています。実際のコミット履歴や外部ドキュメントに基づく正式な履歴付けがある場合はそちらを優先してください。