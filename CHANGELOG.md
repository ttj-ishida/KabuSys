# Changelog

すべての notable な変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」準拠、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28

### 追加
- 初回リリース。パッケージ名: kabusys（日本株自動売買システム向けユーティリティ群）。
- パッケージ公開情報
  - バージョン: 0.1.0
  - パッケージ初期 __all__ として data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの設定自動読み込みを実装。
  - 実行時にプロジェクトルート (.git または pyproject.toml) を探索して .env を探す仕組みを導入し、CWD に依存しない自動読み込みを実現。
  - .env パーサーを実装（export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用途）。
  - Settings クラスを提供し、以下の環境変数をプロパティとして取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live / is_paper / is_dev ヘルパーメソッドを実装。
  - 必須値未設定時は ValueError を送出することで早期検出を容易化。

- AI 関連機能 (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を基にニュースを銘柄毎に集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出し ai_scores に保存する処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数制限を導入（トークン肥大化対策）。
    - JSON Mode を利用した厳格なレスポンス期待と、レスポンスの復元ロジック（前後余分テキストの抽出）。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ、リトライ上限の実装。
    - レスポンスのバリデーション（results 配列・code の照合・スコア数値化・クリッピング）。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）や DuckDB の executemany 空リスト注意点への対策。
    - API キー未設定時は ValueError を送出。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
    - ニュース抽出は news_nlp.calc_news_window を使用し、マクロキーワードでフィルタしたタイトルを LLM に渡して評価。
    - OpenAI 呼び出しは独自実装でモジュール結合を避け、429/ネットワーク/タイムアウト/5xx に対してリトライ実装を導入。失敗フェイルセーフとして macro_sentiment=0.0 にフォールバック。
    - MA 計算はルックアヘッドバイアスを避けるため target_date 未満のデータのみを使用し、データ不足時は中立（1.0 相当）を使用。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を保証。失敗時は ROLLBACK を試みエラーを上位へ伝播。

- データ関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の一貫した判定 API。
    - market_calendar テーブルが未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫性、検索範囲上限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - calendar_update_job により J-Quants から差分取得し冪等保存。バックフィルと健全性チェックを実装。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（ターゲット日付・取得/保存件数・品質検査結果・エラー集約）。
    - 差分更新、バックフィル、品質チェックといった設計方針を反映した ETL モジュールの主要ユーティリティを実装（jquants_client 経由の取得と保存、quality モジュールとの連携想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、営業日調整等。

- リサーチ / ファクター (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200日 MA 乖離（ma200_dev）、ATR 基盤のボラティリティ、流動性指標、バリューファクター（PER/ROE）を DuckDB 上で計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、出力は (date, code) をキーとする dict のリスト。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を独自実装で算出（同順位は平均ランク）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を返すユーティリティを追加。
    - ランク関数（rank）は丸めによる ties の扱いを考慮。

### 改善
- 全体
  - ルックアヘッドバイアス対策を各所で導入（datetime.today()/date.today() を内部ロジックで直接参照せず、target_date を明示的に受け取る設計）。
  - OpenAI 呼び出し部分はテスト容易性のため差し替え可能（内部関数を patch で置換可能）に設計。
  - DuckDB を想定した SQL 実装で互換性・パフォーマンス（ウィンドウ関数等）を考慮。

### 修正
- なし（初回リリースのため既知のバグ修正履歴はなし）。

### セキュリティ
- API キー未設定時に明示的にエラーを発生させることで秘密情報の漏れや無効な実行の早期検出を促進。

---

今後のリリースでは、strategy / execution / monitoring モジュールの具体的な発注ロジック、運用監視・アラート機能、より詳細な品質検査ルールの追加などを予定しています。