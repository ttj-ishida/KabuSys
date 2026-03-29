# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

- 変更履歴はセマンティックバージョニングに従います: MAJOR.MINOR.PATCH  
- 初回リリース: 0.1.0

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys — 日本株自動売買 / リサーチ用ライブラリ。
  - パッケージバージョンは src/kabusys/__init__.py の `__version__ = "0.1.0"`。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を検出して読み込む（配布後も CWD に依存しない探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動読み込みを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパースを堅牢化:
    - コメント行・空行の無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の実装。
  - Settings クラスを提供（settings = Settings()）:
    - 必須環境変数取得時に未設定だと ValueError を送出する `_require()` を採用。
    - J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証を含むプロパティを提供。
    - env 値と log_level の検証（許容値セット）を実装。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し、ai_scores テーブルへ書き込む機能を実装。
    - 処理の流れ: タイムウィンドウ算出 → 銘柄ごと記事集約（最大記事数・文字数でトリム） → 最大 _BATCH_SIZE=20 銘柄ずつのバッチで API 送信 → レスポンス検証 → スコアを ±1.0 にクリップ → idempotent に DB 置換（DELETE→INSERT）。
    - JSON Mode を使った API 応答のパースと、前後に余分なテキストが混ざるケースの復元ロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他エラーはスキップしてフェイルセーフに継続。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - ユーティリティ: calc_news_window(target_date)（ニュース収集ウィンドウ算出）。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。API キー解決は引数または環境変数 `OPENAI_API_KEY`。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせ、日次で市場レジーム（bull/neutral/bear）を判定。
    - 処理の流れ: MA200 乖離算出 → マクロキーワードで raw_news を抽出 → OpenAI で macro_sentiment を評価 → スコア合成（クリップ）→ market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラーやパース失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - OpenAI 呼び出しは内部実装で、テスト時は差し替え可能（モジュール間の結合を避ける意図）。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キー未指定時は ValueError。

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定／取得ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - DB 登録値優先、未登録日は曜日ベースでフォールバック。探索は安全上の最大日数制限（_MAX_SEARCH_DAYS）あり。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得 → jq.save_market_calendar で idempotent 保存。バックフィル/健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL の高レベル設計に基づくユーティリティと ETLResult dataclass を提供。
      - ETLResult: target_date, fetched/saved カウント、quality_issues、errors 等を格納。to_dict() による辞書化対応。
    - 差分更新、backfill、品質チェック（quality モジュールとの連携）を想定した設計（実装の一部）。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティを実装。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日 MA 乖離率）を計算。データ不足時は None を返す設計。
    - calc_volatility(conn, target_date): 20日 ATR、ATR 比率、20日平均売買代金、出来高比率等の算出。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER/ROE を算出（EPS が 0/欠損なら None）。
    - いずれも DuckDB SQL ベースで効率的に実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）をまとめて取得。horizons の検証あり（正の整数かつ <=252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を実装（結合・None 除外・有効レコードが 3 未満なら None）。
    - rank(values): 同順位は平均ランクを返す実装（浮動小数の丸めで ties 対策）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージの __all__ に主要関数をエクスポート。

- パッケージ公開インターフェース
  - src/kabusys/ai/__init__.py: score_news を公開。
  - src/kabusys/research/__init__.py: 主要ファクター計算・ユーティリティを公開。
  - src/kabusys/data/__init__.py および etl 再エクスポートにより ETLResult を公開。

### Changed
- 初回リリースのため該当なし（初回導入機能）。

### Fixed
- 初回リリースのため該当なし（初回導入機能）。

### Notes / 実装上の注意点
- データベース: 主に DuckDB を前提に実装。DuckDB バージョン差分（例: executemany に空リスト不可）に対する互換性処理を所々に導入。
- OpenAI: gpt-4o-mini を利用（JSON Mode）。API エラーやパースエラーに対する堅牢なフォールバック（スコア 0.0、空スキップ）を実装。API キーは引数で注入可能（テスト容易化）。
- ルックアヘッドバイアス対策: AI / リサーチ系モジュールは内部で datetime.today() / date.today() を参照しない設計（外部から target_date を明示的に渡す）。
- DB 書き込みは可能な限り冪等（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK 管理）を志向。
- .env 自動読み込みはデフォルトで有効。テスト時や特殊な配布形態で無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の取得箇所あり。これらが未設定だと Settings プロパティアクセス時に ValueError を送出する。

### Known limitations / TODO（今後の候補）
- PBR・配当利回りなどバリューファクターの拡張は未実装（calc_value の注記）。
- 一部の jquants_client / quality モジュールは外部依存を前提（実装の統合やモック化検討）。
- テスト用のモックや CI 向けのテストスイート整備（OpenAI 呼び出しのモック化はコードで想定済み）。

---

今後のリリースでは、バグ修正（Fixed）や機能追加（Added）、API 変更（Changed）を明確に分けて記載します。README やドキュメントに含める設定・運用手順と合わせてご利用ください。