# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

注: ここに記載する内容は、提供されたコードベースから実装内容・設計方針を推測して作成した初期リリースの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。トップレベルで data / research / ai 等のサブパッケージを提供する構成を定義。
  - バージョン: 0.1.0

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を起点に行われるため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local (.env を上書き) > .env（既存未設定キーのみセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護するための protected キー処理を実装。
  - .env パーサーは次の形式をサポート:
    - export KEY=VAL 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ
    - インラインコメント（クォートなしは '#' の直前が空白/タブであればコメントとして認識）
  - Settings クラスを提供し、主要設定プロパティを環境変数から取得:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（Path 型で返却）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev 補助プロパティ
  - 必須環境変数が未設定の場合は ValueError を送出する _require 関数を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って各銘柄のセンチメントスコアを算出する score_news を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理: 最大 20 銘柄/回、各銘柄は最大 10 記事・最大 3000 文字にトリム。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。失敗チャンクはスキップして他チャンクは継続。
    - レスポンスのバリデーション: JSON パース、"results" の存在、スコア数値化、既知コードのみ採用。スコアは ±1.0 にクリップ。
    - 成功したスコアのみ ai_scores テーブルへ置換的に書き込む（DELETE → INSERT、部分失敗時にも他コードを保護）。
    - テスト容易性: OpenAI 呼び出しの内部関数 _call_openai_api はパッチ差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200_ratio 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを回避。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（上限 20 件）して LLM で評価。
    - LLM（OpenAI）失敗時は macro_sentiment = 0.0 で継続するフェイルセーフを実装。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性: _call_openai_api の差し替えを想定。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）を元に営業日判定・前後営業日探索・期間内営業日取得を提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB のデータがない場合は曜日ベース（土日除く）でフォールバック。
    - next/prev_trading_day の探索は最大 _MAX_SEARCH_DAYS（安全上の上限）までで例外を投げることで無限ループを防ぐ。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新するバッチ処理を提供。バックフィル・健全性チェックを実装。
  - ETL / パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー一覧などを保持、to_dict メソッドあり）。
    - 差分更新のための内部ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - デフォルトのバックフィル日数、最小データ日付等の定義を含む。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- 研究用ユーティリティ (kabusys.research)
  - 再利用可能関数を公開:
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
      - モメンタム（1M/3M/6M、ma200乖離）、ATR（20日）、流動性指標、PER/ROE 等を DuckDB 上の SQL と Python で計算。
      - データ不足時の None 取り扱いやログ出力を実装。
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
      - 将来リターン（任意ホライズン）を一度のクエリで取得、スピアマン IC（ランク相関）、統計サマリー、ランク付けユーティリティを提供。
    - zscore_normalize を kabusys.data.stats から再エクスポート。
  - 設計方針により、研究用モジュールは DuckDB の prices_daily / raw_financials などの読み取りのみを行い、本番発注 API などへはアクセスしない。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能にし、環境変数依存を軽減（テストや鍵管理の柔軟性確保）。
- .env 自動読み込みは無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

### 互換性に関する注意 (Notes / Compatibility)
- DuckDB の挙動差（executemany に空リストを与えられない等）を考慮した実装が各所に導入されているため、DuckDB の古い/将来のバージョンでの互換性に注意。
- OpenAI 呼び出しに対するエラー処理は堅牢化されているが、API の将来の SDK 変更（例: 例外クラスや status_code の有無）に備えた防護が一部にある（getattr での取得など）。
- 日付処理はルックアヘッドバイアス回避のため、date.today() / datetime.today() の直接参照を避け、呼び出し側が target_date を明示的に渡す設計になっている点に注意。

---

今後のリリースでは、strategy / execution / monitoring 等の運用・発注関連モジュールの実装拡大、テストカバレッジの強化、ドキュメント追記（使用例・DB スキーマ）などが見込まれます。