# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
安定リリースの準備段階として、コードベースから推測される初期リリースの変更点を記載しています。

全体方針:
- 日付は本CHANGELOG作成日 (2026-03-29) を使用しています。
- 各項目はソースコードの実装・ドキュメント文字列から推測して記載しています。

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システムの基盤機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 `kabusys` を導入。モジュール群（data, research, ai, monitoring, strategy, execution 等）の分離を想定したエクスポートを行う。
  - バージョン情報 `__version__ = "0.1.0"` を定義。

- 環境設定 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用可能）。
  - .env の堅牢なパーサ実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみコメント扱い）。
  - Settings クラスを提供し、主要な設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / データベースパス (DuckDB / SQLite) / 環境 (development/paper_trading/live) / ログレベル等。
  - 必須環境変数未設定時は ValueError を投げる `_require` を使用。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとの記事を OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - バッチサイズ、記事/文字数のトリム、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ、その他はスキップ（フェイルセーフ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で実施。部分失敗時に既存データを保護する実装。
    - ニュースウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して計算する `calc_news_window` を提供。
  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュースの抽出はキーワードベース（日本・米国／グローバル）でフィルタ。
    - OpenAI API 呼び出しは独立実装。API失敗時は macro_sentiment=0.0 として継続する安全設計。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを参照。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを扱うユーティリティ群を実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar が未取得のときの曜日ベースフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）。
    - 探索上限 `_MAX_SEARCH_DAYS` を設けて無限ループを防止。
  - ETL パイプライン (pipeline, etl)
    - 差分取得・保存・品質チェックのための ETL 構成を実装。
    - ETL 実行結果を格納するデータクラス `ETLResult` を公開。
    - デフォルトのバックフィル日数や calendar lookahead などの運用パラメータを設定。

- リサーチ／ファクター (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR/流動性/出来高指標、PER/ROE の計算ロジックを実装。
    - DuckDB の SQL ウィンドウ関数を利用して効率的に集計。
    - データ不足時（行数不足等）は None を返す保守的な挙動。
  - feature_exploration:
    - 将来リターン計算（horizons: デフォルト [1,5,21]）、IC（Spearman rank）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク付け関数を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。
  - これらは取引・発注 API にアクセスしない解析専用実装。

- その他
  - DuckDB を想定した接続型インタフェースを広く採用（型注釈で DuckDBPyConnection を参照）。
  - ロギングを各モジュールで活用し、重要イベントや警告を出力。

### 変更 (Changed)
- （初回リリースのため該当なし。ただし以下の設計判断が含まれる）
  - すべての分析関数はルックアヘッドバイアス防止の観点から datetime.today()/date.today() を直接参照しない実装方針を採用。
  - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するプロンプト設計を採用。

### 修正 (Fixed)
- データベース操作の堅牢化
  - ai_scores / market_regime への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、例外時は ROLLBACK を実行。ROLLBACK 失敗時は警告ログを出す。
  - DuckDB の executemany が空リストを受け付けない挙動に対して、空パラメータのケースをハンドリングして実行をスキップする保護を追加。
- OpenAI レスポンス処理の堅牢化
  - JSON 解析失敗時に最外の {} を抽出して復元を試みるフォールバックを導入。
  - API の多様なエラー（RateLimit, APIConnectionError, APITimeoutError, APIError 5xx 等）に対する再試行・ログ出力戦略を実装し、最終的にフェイルセーフ（0.0）にフォールバックする実装。

### セキュリティ (Security)
- OpenAI 利用に関する注意
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数 `OPENAI_API_KEY` の設定を必須とする。未設定時は ValueError を発生させる。
- 環境変数の保護
  - .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。`.env.local` は既存 OS 環境を上書きしないよう保護されるキーを考慮して読み込まれる。

### 既知の注意点 / 動作上のポイント (Notes)
- デフォルトの OpenAI モデル: gpt-4o-mini を使用。JSON Mode の利用に依存しているため、将来的なモデル/SDK 変更に注意が必要。
- ニュース集約ウィンドウ:
  - JST 基準で前日 15:00 ～ 当日 08:30 の記事を対象。内部では UTC（naive datetime）に変換して比較。
- ETF レジーム判定:
  - 1321（日経225連動ETF）の 200 日 MA 乖離を主要指標とする（重み 70%）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
- ログレベルと環境設定:
  - KABUSYS_ENV は development/paper_trading/live のいずれかでないと ValueError を送出。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかでないと ValueError を送出。
- テスト容易性:
  - OpenAI 呼び出しの内部ラッパー関数（各モジュール内の _call_openai_api）は unittest.mock.patch により差し替え可能に設計。

---

今後のリリースで想定される改善点（例、未実装/拡張領域）
- 追加ファクター（PBR、配当利回り等）の実装。
- モデル切替・API レスポンス仕様変更への追従テストの追加。
- 監視・アラート機能（Slack 通知等）の明示的実装（Settings にトークンは定義済み）。
- ドキュメント・運用マニュアルの充実。

（以上）