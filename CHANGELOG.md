# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

変更ログはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-04-03

初回リリース — KabuSys: 日本株自動売買・調査プラットフォームの基盤機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 `kabusys` を追加。主要サブモジュールをエクスポート（data, research, ai, execution, monitoring, strategy 相当のエントリを意図）。
  - バージョン情報 `__version__ = "0.1.0"` を設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出を __file__ から行い、.git または pyproject.toml を基準に探索するため CWD に依存しない自動ロード。
  - .env のパース機能を実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープシーケンス処理
    - インラインコメント処理（クォート無しの場合、'#' の直前がスペース/タブならコメントとして扱う）
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意（テスト用途想定）。
  - 必須環境変数取得 `_require()` と `Settings` クラスを追加。J-Quants / kabu / LINE / DB /監視設定 / システム設定をプロパティで提供。
  - 環境変数のバリデーション（KABUSYS_ENV / LOG_LEVEL の有効値チェック）とユーティリティ（is_live / is_paper / is_dev）を実装。
  - デフォルトファイルパス（DuckDB / SQLite / PID / kill flag 等）を設定。

- ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news テーブルからニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して `ai_scores` に書き込む `score_news` を実装。
  - 処理の主な特徴:
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を `calc_news_window` で提供（DB 比較は UTC naive datetime を使用）。
    - 銘柄ごとに最新の最大記事数 / 文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつをバッチ（_BATCH_SIZE）で API へ送信。
    - JSON Mode を利用した厳密な JSON レスポンス期待とレスポンス検証（存在チェック、型検証、未知コードの無視、数値変換と有限性チェック）。
    - API 呼び出しはリトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで行う。その他エラーはスキップして継続（フェイルセーフ）。
    - 書き込みは冪等性を意識し、対象コードのみ DELETE → INSERT を実行（部分失敗で既存データを保護）。DuckDB の executemany の仕様に配慮した空リストチェックあり。
    - テスト容易性: API 呼び出し内部関数は差し替え可能（unittest.mock.patch 用意）。

- 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定する `score_regime` を実装。
  - 処理の主な特徴:
    - DuckDB から 1321 の終値を用い、厳密に target_date 未満のデータのみを使用して MA200 乖離（ルックアヘッド防止）。
    - マクロキーワードで raw_news のタイトルをフィルタし、OpenAI によるマクロセンチメント評価（JSON 出力）を行う。記事がない場合は LLM 呼び出しをスキップして 0.0 を採用。
    - API 呼び出し失敗時は再試行（指数バックオフ）し、最終的に失敗した場合は macro_sentiment=0.0 で継続（例外を投げないフェイルセーフ）。
    - 結果は `market_regime` テーブルに対してトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み。
    - API キーは引数から注入可能で、なければ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算群を実装・公開:
    - `calc_momentum` : 1M/3M/6M リターン、ma200_dev（200日 MA 乖離率）。データ不足時は None。
    - `calc_volatility` : 20日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio。
    - `calc_value` : raw_financials から最新財務を取り出し PER / ROE を計算（EPS=0や欠損で None）。
  - 特徴量探索:
    - `calc_forward_returns` : 指定ホライズンの将来リターン（複数ホライズン対応・ホライズン検証）。
    - `calc_ic` : ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード < 3 の場合 None）。
    - `rank` : 同順位は平均ランクとするランク変換（丸めで ties の検出漏れを防止）。
    - `factor_summary` : count/mean/std/min/max/median などの基本統計量集計。
  - 方針: DuckDB に対する SQL+Python 実装で外部 API に依存せず、ルックアヘッドバイアスを避ける設計。

- データ基盤 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダー管理用ロジックを実装:
      - 営業日判定 (`is_trading_day`)、次/前営業日取得（`next_trading_day` / `prev_trading_day`）、期間内営業日列挙（`get_trading_days`）、SQ日判定（`is_sq_day`）。
      - DB（market_calendar）にデータがある場合は DB 値を優先。未登録日は曜日ベースのフォールバック（平日=営業日）を使用し、一貫性を確保。
      - 最大探索日数（_MAX_SEARCH_DAYS）で無限ループを防止。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装。J-Quants クライアントから差分取得して `market_calendar` を冪等に更新。バックフィル・健全性チェックあり。
  - ETL / パイプライン (`pipeline`, `etl`)
    - ETL 実行結果を表すデータクラス `ETLResult` を実装（取得数・保存数・品質問題・エラー等を保持）。
    - ETL モジュールは差分取得、冪等保存、品質チェック（`quality` モジュール参照）を想定した設計で、id_token 注入や backfill に対応。
    - `etl` パッケージは `ETLResult` を公開（再エクスポート）。

- DuckDB を主要なストレージとして使用する一貫したインターフェースを提供。SQL は DuckDB のウィンドウ関数等を利用。

### 変更 (Changed)
- 設計・実装ポリシーとして明示的に次を採用:
  - ルックアヘッドバイアス防止: datetime.today()/date.today() の直接参照を避け、target_date に基づく明示的な計算を行う。
  - フェイルセーフ原則: OpenAI API 等外部依存は失敗時にスキップまたは中立値で続行する設計（例: macro_sentiment=0.0、score_news のスキップ等）。
  - テスト可能性の確保: API 呼び出し箇所の差し替え（モック）を想定した実装。
  - DuckDB 互換性への配慮（executemany の空リスト扱いなど）。

### 修正 (Fixed)
- この初回リリースでは既知のバグ修正履歴はありません（初期実装）。

### 注意 (Notes)
- OpenAI API 依存部分は API キー（引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は関数が ValueError を投げます。
- .env パーサは多くの実用ケース（quoted values、エスケープ、export prefix、コメント）に対応しますが、極端に特殊な .env 構成では挙動が異なる可能性があります。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials など）はこのコードの期待に沿って事前作成されている必要があります。
- 実行ログは各モジュールで logger を使って出力されます。LOG_LEVEL は Settings.log_level で制御できます。

----

今後の予定（例）
- execution / monitoring / strategy 部分の実装拡張（自動発注ロジック、監視アラート、戦略定義の具体化）
- jquants_client の具体実装と ETL の実稼働確認
- 単体テスト・統合テストの充実、CI 設定およびドキュメントの整備

上述はソースコードから推測した初期実装の要約です。必要であれば各モジュールの関数一覧や使用例を追加で出力できます。