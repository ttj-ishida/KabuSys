# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回公開リリース。

### 追加
- 全体
  - 日本株自動売買システムの初期パッケージ "kabusys" を追加。
  - パッケージバージョンを 0.1.0 に設定。

- 設定 / 環境変数 (kabusys.config)
  - Settings クラスを提供し、環境変数から各種設定値を取得するプロパティを実装（J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等）。
  - .env / .env.local 自動ロード機能を実装。読み込み優先順位は OS 環境 > .env.local > .env。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント処理などに対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェック用の _require ユーティリティを実装。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。

- AI モジュール (kabusys.ai)
  - news_nlp モジュールを追加:
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode で銘柄別センチメントを算出し、ai_scores テーブルへ書き込む。
    - calc_news_window(target_date)：JST ベースのニュース収集ウィンドウ計算を提供（UTC naive datetime 出力）。
    - バッチ処理（最大 20 銘柄/コール）、記事トリム（文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証・スコアクリップ（±1.0）を実装。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - regime_detector モジュールを追加:
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース（重み 30%）の LLM センチメントを合成して market_regime テーブルへ冪等書き込み。
    - 1321 の MA200 比率計算（_calc_ma200_ratio）、マクロ記事抽出（_fetch_macro_news）、OpenAI 呼び出しと再試行処理（_score_macro）およびスコアのクリッピングを提供。
    - マクロキーワード一覧やシステムプロンプトなどを定義。
    - API の失敗時はフェイルセーフで macro_sentiment=0.0 を採用。

- Data モジュール (kabusys.data)
  - calendar_management を追加:
    - JPX マーケットカレンダー管理と営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダー情報がない場合は曜日ベース（平日＝営業日）でフォールバック。
    - calendar_update_job(conn, lookahead_days=...)：J-Quants API から差分フェッチして market_calendar を冪等保存する夜間ジョブを実装。バックフィル日数・健全性チェックあり。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行のメタ情報・品質チェック問題・エラー保管、has_errors / has_quality_errors プロパティ、to_dict を実装）。
    - data.etl で ETLResult を再エクスポート。
  - quality / jquants_client 参照点（ETL 実装方針に準備）。

- Research モジュール (kabusys.research)
  - factor_research を追加:
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)：20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。データ不足時は None を返す。
    - calc_value(conn, target_date)：raw_financials から最新財務を参照して PER/ROE を計算（EPS が 0/欠損時は None）。
    - いずれも DuckDB SQL を用いた実装で、外部 API 呼び出しなし（安全に研究用途で利用可能）。
  - feature_exploration を追加:
    - calc_forward_returns(conn, target_date, horizons=None)：複数ホライズンの将来リターンを一括取得可能。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）を計算。
    - rank(values)：同順位は平均ランクとするランク化ユーティリティ（丸めで ties 対応）。
    - factor_summary(records, columns)：count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージ __all__ に主要関数を公開。

### 変更（設計／実装上の重要点）
- DuckDB を主要なローカル分析 DB として利用。多くの集約・ウィンドウ処理は SQL（DuckDB）側で実行。
- データベース書き込みは可能な限り冪等化（DELETE して INSERT、BEGIN/COMMIT/ROLLBACK）して部分失敗時の安全性を確保。
- AI 呼び出しまわりは以下ポリシーを採用:
  - JSON Mode を使い厳密な JSON レスポンスを期待するが、万が一前後の余計なテキストが混ざる場合は最外側の {} を抽出して復元を試みる。
  - 429・ネットワーク切断・タイムアウト・5xx は指数バックオフでリトライ。その他のエラーはスキップして処理継続（フェイルセーフ）。
  - テスト可能性のため、内部の API 呼び出し関数（_call_openai_api）を patch できる設計。
  - LLM の出力は数値に変換し、所定範囲にクリップして扱う（安定化）。
- ルックアヘッドバイアス対策:
  - score_news / score_regime / 研究系関数は内部で datetime.today() / date.today() を参照せず、必ず target_date を引数で与えて処理することを想定（ただし calendar_update_job はバッチ実行のため date.today() を使用する）。
- カレンダーロジック:
  - market_calendar が部分的にしか登録されていない場合でも、DB 登録日は優先し未登録日は曜日ベースでフォールバックする方針で next/prev/get_trading_days に一貫性を持たせている。
- 環境設定:
  - .env パーサは実運用でありがちなクォート・エスケープ・コメントのパターンに対応。

### 修正（バグ修正等）
- 初回リリースのため過去のバグ修正はなし。

### セキュリティ
- 初期リリース。OpenAI API キーや各種パスワードは環境変数で扱う前提。機密情報の取り扱いは .env の運用ルールに従ってください。

### 既知の注意点 / マイグレーション
- DuckDB の executemany で空リストを渡すと失敗するバージョンがあるため、空チェック（if params:）を入れている点に注意してください。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、将来の SDK 変更に対して status_code の有無等に配慮した実装になっていますが、実稼働前に API レスポンスの検証を行ってください。
- calendar_update_job は内部で date.today() を使うため、リプロデュース可能なバッチ実行のためには実行日時の管理に注意してください。

---

今後のリリースでは、発注（execution）・監視（monitoring）・データ保存の詳細や GUI/CLI ツール、より豊富な品質チェックやモニタリング連携を追加する予定です。