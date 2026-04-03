# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴:

## [0.1.0] - 2026-04-03
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = 0.1.0。
  - パッケージ公開時に利用する主要サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - ファイル読み込み失敗時は警告を出力して継続。
  - .env パース実装を独自に実装（export プレフィックス、クォート内エスケープ、インラインコメント処理等に対応）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）。
    - 必須 env 取得時に未設定は ValueError を送出する _require を実装。
    - is_live / is_paper / is_dev 等のユーティリティプロパティ。
  - デフォルト値・閾値を多数提供（CPU/MEM/DISK 閾値、DBパス等）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む処理 score_news を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 内の UTC タイムスタンプと比較）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3,000 文字にトリム。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大回数定義あり）。
    - レスポンスのバリデーション実装（JSON 抽出、results リスト検証、コード正規化、スコアの数値チェック、±1.0 でクリップ）。
    - DB 書き込みは部分失敗を考慮し、取得できたコードのみを DELETE→INSERT（冪等）で置換。
    - テスト容易性: OpenAI 呼び出しはモジュール内 private 関数に抽象化されておりモック可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - MA 計算は target_date 未満のデータのみを利用してルックアヘッドバイアスを回避。
    - マクロニュース抽出はタイトルベースでマクロキーワード群にマッチする記事を最大 20 件取得。
    - OpenAI（gpt-4o-mini）呼び出しと再試行・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - レジームスコアは clip と閾値判定を行い、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは news_nlp と独立した private 実装にしてモジュール結合を避ける設計。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB の SQL ウィンドウ関数を活用した実装。データ不足時は None を返す仕様。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
    - IC（Information Coefficient）計算 calc_ic(...)
    - rank ユーティリティ（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）
    - pandas 等外部ライブラリに依存しない純標準ライブラリ実装。
  - zscore 正規化ユーティリティを data.stats から再エクスポート。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar による営業日判定ロジック実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバック。
    - next/prev/get の探索は最大 _MAX_SEARCH_DAYS に制限し無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理（バックフィル、健全性チェック含む）。
  - ETL パイプライン（pipeline / etl）
    - ETLResult dataclass を公開（ETL の取得/保存数や品質問題を集約）。
    - pipeline モジュールを想定した差分更新・保存・品質チェックの方針（jquants_client と quality モジュールを使用）。
    - _table_exists, _get_max_date 等の内部ユーティリティを実装（DuckDB 前提）。
  - jquants_client との明確な連携フローを想定（実装は別モジュール参照）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

注記（設計上の重要点、運用メモ）
- LLM を用いる処理（news_nlp, regime_detector）はルックアヘッドバイアス防止のため内部で datetime.today() / date.today() を直接参照しない設計になっています。必ず target_date を明示して呼び出す必要があります。
- LLM 呼び出し部分はテスト容易性のためモック差し替えポイントを提供しています（モジュール内の _call_openai_api 等）。
- DuckDB をデータレイヤに想定しており、SQL クエリは DuckDB の機能（ウィンドウ関数など）に依存しています。
- .env パーサは一般的なケースに対応していますが、特殊な .env 構文がある場合は注意してください（.env.example を参照のこと）。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体実装（注文発行・実行監視・稼働監視）を順次追加予定。
- jquants_client, quality モジュールの詳細実装およびテストカバレッジ強化。
- LLM プロンプト・モデル評価や料金最適化の改善。

もし CHANGELOG に特に追加したい項目（例: リリース日を変更、より詳細なマイグレーション手順など）があれば教えてください。