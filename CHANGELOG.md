# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
https://keepachangelog.com/ja/1.0.0/

なお、以下は提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です（実際のコミット履歴がないため実装内容を要約・整理しています）。

## [0.1.0] - 2026-04-03

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードするユーティリティを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に .env/.env.local を検索して自動ロード（CWD に依存しない）。
  - .env パーサーは以下に対応:
    - コメント行、空行の無視
    - export KEY=val 形式の処理
    - シングル・ダブルクォート、バックスラッシュエスケープの処理
    - 行内コメント（クォートなし・直前に空白がある '#' をコメントとみなす）
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定取得: _require() による未設定時の ValueError
  - Settings クラスでアプリケーション設定をプロパティ提供:
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）/監視用設定（pid/killswitch 関連）/リソース閾値/環境（development/paper_trading/live）/ログレベル
  - 設定値のバリデーション（env, log_level の列挙チェック）

- AI コンポーネント (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたニュース記事の銘柄別センチメント評価機能を実装。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30、DBはUTCで保存されている想定）。
    - 銘柄ごとに記事を集約し（最大記事数・文字数でトリム）、最大20銘柄をバッチでAPI送信。
    - 再試行/指数バックオフ実装（429・接続断・タイムアウト・5xx を対象）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code と score の型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
    - 部分失敗に備え、ai_scores テーブルへの書込みは対象コードのみ DELETE → INSERT（既存スコア保護）。
    - テスト容易性を考慮し、API 呼び出しは _call_openai_api を通す設計でモック可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - 日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - 判定ロジック:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロニュースは news_nlp の calc_news_window に基づくウィンドウで取得し、OpenAI を用いて JSON 出力で macro_sentiment を取得。
      - API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
      - 結果は冪等に market_regime テーブルへ保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API 呼び出しやエラー処理、リトライの実装（RateLimit/接続/タイムアウト/5xx の処理とバックオフ）。

- データ層 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを管理するユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - market_calendar がない場合は曜日ベース（平日）でフォールバックする設計。
      - DB 登録データ優先、未登録日は曜日フォールバックで一貫した振る舞いを保証。
      - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等更新、バックフィル、健全性チェックを実装。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラーの集約、辞書化ユーティリティ）。
    - pipeline モジュールは差分更新、保存（jquants_client の save_* を利用）、品質チェック（quality モジュール）を意識した設計。
    - ETL の設計方針: 差分取得、バックフィル、品質チェックは集約して呼び出し元が対処可能な形で結果を返す。
    - データベース（DuckDB）を前提とした存在確認・最大日付取得等のユーティリティを実装。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum, Value, Volatility, Liquidity に関する定量ファクターを実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）。データ不足時は None。
      - calc_volatility: atr_20（20日ATR）/ atr_pct / avg_turnover / volume_ratio。必要行数未満は None。
      - calc_value: 最新財務データ（raw_financials）と価格を組み合わせて PER / ROE を算出（EPS 欠損や 0 の場合は None）。
    - DuckDB 上の SQL + Python で計算し、(date, code) 単位の辞書リストを返す。
    - 本番口座や発注 API にはアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズンの将来リターンを一括取得可能（ホライズン引数、入力検証あり）。
    - IC（Information Coefficient）計算 (calc_ic): Spearman ランク相関に基づくファクター有効性評価（有効レコード数が少ない場合は None）。
    - rank ユーティリティ: 同順位は平均ランクで処理（丸めで ties 検出の堅牢化）。
    - factor_summary: count/mean/std/min/max/median を算出する集計ユーティリティ。
    - 依存ライブラリを最小化（標準ライブラリのみで実装）し、DuckDB への依存を前提に設計。

### 変更
- なし（初期公開相当の実装を一掃して追加）。

### 修正 / 強化
- AI レスポンスの堅牢性向上:
  - JSON モードでも余計な前後テキストが混入する可能性に対して外側の {} を抽出してパースを試みるロジックを追加。
  - レスポンスパース失敗や API 例外は例外伝播させずログを出してフォールバック（フェイルセーフ）する設計。
- DB 書き込み時の堅牢性:
  - DuckDB の executemany の挙動に合わせて空パラメータ時には実行をスキップする安全対策を適用。
  - market_regime / ai_scores への書き込みを冪等に行う（既存行削除後挿入）ことで部分失敗時のデータ保護を実現。
- 設計上の注意点を明記:
  - すべての関数で datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは内部専用関数経由にしてテスト時にモック可能にした。

### セキュリティ
- なし（注記: OpenAI API キー、J-Quants トークン、Kabu API パスワードなどは環境変数で管理することを推奨）。

### 互換性 / マイグレーション
- 環境変数の追加／必須項目:
  - OPENAI_API_KEY（AI モジュール利用時に必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 利用）
  - KABU_API_PASSWORD（kabuステーション API 利用）
  - 各種パス（DUCKDB_PATH, SQLITE_PATH）や監視関連（PID_FILE_PATH, KILL_FLAG_PATH）にはデフォルト値が設定されているが、運用環境では .env で適切に上書きしてください。
- DB スキーマ:
  - 本実装は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを前提としています。既存 DB を利用する場合はスキーマの整合性確認を行ってください。

---

（注）上記は提供されたソースコードの実装内容から推測して作成した CHANGELOG です。実際の変更履歴（コミットやリリースノート）がある場合は、それに合わせて調整してください。必要ならば、各機能ごとにさらに詳細なリリースノート（既知の制約、既知のバグ、例: LLM レスポンスのパース制限や DuckDB バージョン依存の注意点等）を追記できます。