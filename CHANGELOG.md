# Keep a Changelog

すべての重要な変更履歴をここに記載します。フォーマットは Keep a Changelog に準拠します。

履歴はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - バージョン文字列: 0.1.0。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を探索（CWDに依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント取り扱い（クォート有無でのコメント認識）に対応。
    - .env 読み込み時の protected キーサポート（OS環境変数を上書きさせない）。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants, kabuステーション, Slack, DB パスなどのプロパティ（必須項目は未設定時に ValueError）。
    - env (development/paper_trading/live) と log_level のバリデーション。
    - Path を返す DB パスプロパティ（duckdb/sqlite）と便利な is_live/is_paper/is_dev。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを生成。
    - タイムウィンドウ計算 (前日15:00 JST〜当日08:30 JST) を calc_news_window で提供。
    - バッチング、1チャンク当たり最大銘柄数（_BATCH_SIZE=20）、記事文字数トリム（_MAX_CHARS_PER_STOCK）や記事数上限を実装。
    - JSON Mode を使用して厳密な JSON レスポンスを期待し、レスポンスの堅牢なバリデーション (_validate_and_extract) を実装。スコアは ±1.0 にクリップ。
    - API 呼び出しで 429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - テスト容易性: _call_openai_api をパッチ差し替え可能に実装。
    - ai_scores テーブルへの冪等的な書き込み（取得したコードのみ DELETE → INSERT）を実装。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出のためのキーワードリストと最大記事件数を実装。
    - OpenAI 呼び出しでのリトライ、エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime を更新。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などの営業日判定ユーティリティを実装。
    - market_calendar テーブルがない場合は曜日ベースのフォールバックを採用（土日は非営業日）。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理を実装（バックフィル日数、先読み、健全性チェック含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分取得、保存、品質チェックの考え方に基づくユーティリティ基盤を実装。
    - ETLResult をデフォルトで公開（kabusys.data.ETLResult）。
  - DuckDB 連携の小ユーティリティ: テーブル存在確認や最大日付取得など。

- リサーチ / ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。データ不足時の挙動（None）明記。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を用いて PER/ROE を計算（EPS が 0/欠損時は None）。
    - 設計方針として DuckDB の SQL を中心に実装、外部 API にはアクセスしない。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損や ties 考慮）。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めて ties 判定）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 一部ユーティリティ再エクスポート (src/kabusys/research/__init__.py)
    - zscore_normalize を kabusys.data.stats から再エクスポート。
    - 主要関数を __all__ にて公開。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 既知の注意点 / 実装ノート
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定、ファクター計算は内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満 / 以前のデータのみ参照するよう配慮。
- フェイルセーフ設計:
  - OpenAI API 呼び出しの失敗は基本的に例外を上位に投げず、該当部分をフォールバック（0.0 やスキップ）して処理を継続する方針。
- テストしやすさ:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）はテスト時にパッチ差し替え可能に実装。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョンへ配慮して事前チェックを行う実装あり。
- .env のパースは POSIX ライクだが完全なシェル互換ではない点に注意（意図的に簡潔実装）。

### 将来の改善候補（備考）
- news_nlp / regime_detector の LLM プロンプトやモデルは将来的に設定可能にする余地あり（現状は定数化）。
- quality モジュールによる詳細な問題分類と ETL の自動アクション（通知／ロールバック等）の検討。
- jquants_client の抽象化・モックインターフェース整備でテスト容易性向上。

---

以上がこのコードベース（バージョン 0.1.0）の主要な変更点・実装内容のまとめです。必要であれば各モジュールごとの詳細なリリースノートや、API 使用例・互換性注意点を追記できます。どの情報を優先して追加しますか？