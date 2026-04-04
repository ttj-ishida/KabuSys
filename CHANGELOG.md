Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
すべての変更は後方互換性や設計上の注意点をコードベースから推測して記載しています。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-04-04
-------------------

Added
- 基本パッケージ
  - kabusys パッケージ初期リリース。__version__ = "0.1.0" を設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントルールに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabu API / LINE / DBパス / 監視閾値 / システム環境 等のプロパティを提供。
  - KABUSYS_ENV, LOG_LEVEL の検証を導入（有効値チェック、無効時は ValueError を送出）。
  - 必須環境変数未設定時の _require() による明確なエラー（ValueError）。

- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へ送信してセンチメントスコアを ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST基準）を calc_news_window として提供。
    - バッチ処理（1回最大 20 銘柄）・トークン肥大対策（記事数・文字数トリム）・JSON レスポンス検証・スコアの ±1.0 クリップを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行、その他はスキップするフェイルセーフ。
    - DuckDB の executemany に対する互換性考慮（空リストバインド回避）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。

  - 市場レジーム検出 (regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロ記事のフィルタリング（キーワードリスト）と OpenAI 呼び出し、再試行、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジーム閾値（bull/neutral/bear）を定義しログ出力。
    - DuckDB トランザクション制御（BEGIN/DELETE/INSERT/COMMIT）とエラーハンドリング（ROLLBACK 試行）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日MA乖離を計算。
    - calc_volatility(conn, target_date): 20日 ATR、ATR比率、平均売買代金、出来高比を計算。
    - calc_value(conn, target_date): latest 財務情報に基づく PER / ROE を計算（raw_financials と prices_daily を結合）。
    - DuckDB SQL を活用した実装（外部 API には接続しない）と不足データの扱い（None 戻し）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）による IC 計算を実装（有効レコード 3 未満は None）。
    - rank(values): 同順位は平均ランクを採るランク付け実装（丸めによる ties 対応）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - すべての関数はルックアヘッドバイアスを防ぐ設計（date.today()/datetime.today() を直接参照しない）。

- データ基盤 / ETL (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録がない場合は曜日ベースでフォールバック（休日判定）。最大探索範囲を定義し無限ループを防止。
    - calendar_update_job(conn, lookahead_days): J-Quants クライアント経由で差分取得→保存（バックフィル・健全性チェック・例外処理を含む）。
  - pipeline:
    - ETLResult dataclass を導入（取得件数・保存件数・品質チェック・エラー一覧・ユーティリティメソッド to_dict）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した ETL 設計。致命的品質問題は収集して呼び出し元に委ねる方針。
    - DuckDB テーブル存在チェック等のユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート。

- テスト/デバッグしやすさ
  - OpenAI 呼び出し部分は内部関数をモック/patch できるようにしており、ユニットテストで外部 API を置き換えやすい設計。

Fixed / Hardening
- OpenAI の JSON mode のレスポンスで前後に余計なテキストが混ざる場合に備え、最外の {} を抽出して復元する寛容なパースを追加。
- DuckDB の挙動（executemany に空リストを与えられない）に対する回避処理を追加。
- 各種 API エラー処理で 5xx と非5xx を分けてリトライ判定するなど堅牢性を強化。
- 各モジュールで「欠損データ発生時は None を返す」「API失敗時は該当処理をスキップして継続（フェイルセーフ）」という方針を明確化。

Notes / その他設計上の注記
- 全体方針として「ルックアヘッドバイアス防止」や「DB への冪等書き込み」「部分失敗時に既存データを守る（コード絞り込み）」を重視。
- OpenAI API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を投げる明示的な挙動。
- jquants_client 等の外部 API 呼び出し部分は別モジュールとして分離される想定（calendar/pipeline から呼び出し）。
- ログメッセージと警告を多用して運用時のトラブルシュートを容易にする実装。

Breaking Changes
- なし（初期リリース）。ただし Settings の KABUSYS_ENV / LOG_LEVEL の不正値は ValueError を送出するため運用環境変数の整合性に注意。

Authors
- コードベースからの推測に基づく CHANGELOG（自動生成的記述）。

--- 

（注）本 CHANGELOG は提示されたソースコードを基に機能と設計意図を推測して作成しています。実際の変更履歴やリリースノートが存在する場合はそちらを優先してください。