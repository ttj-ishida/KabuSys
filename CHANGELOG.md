# Changelog

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

## [0.1.0] - 2026-03-29

### Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョン定義 __version__ = "0.1.0" と主要サブパッケージの公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env は上書きされない、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export KEY=val 形式やクォート、インラインコメントのパースに対応する独自パーサを実装。
    - OS 環境変数を保護する protected 機構（.env による上書きを防ぐ）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを定義。値検証（許容される env 値・log level）を実装。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST 〜 当日08:30 JST を UTC に変換）を calc_news_window() として公開。
    - 1チャンク最大銘柄数 _BATCH_SIZE=20、記事トリム長 _MAX_CHARS_PER_STOCK=3000、1銘柄当たり最大記事数 _MAX_ARTICLES_PER_STOCK=10。
    - API レスポンスの厳密なバリデーションと JSON 抽出ロジック（余計な前後テキストが混じる場合の復元処理）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。失敗時は対象銘柄をスキップし処理継続（フェイルセーフ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護する実装）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime() を追加。
    - マクロニュース抽出（マクロキーワードリスト） → OpenAI（gpt-4o-mini）への投げ込み（最大 _MAX_MACRO_ARTICLES=20）→ 合成スコア化。
    - API エラー時は macro_sentiment=0.0 で継続するフェイルセーフ、LLM 呼び出し専用の内部実装（news_nlp と共有しない）によりモジュール結合を低減。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、DB 書き込み失敗時はロールバックを試行。
- データ管理（Data Platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理、営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバック処理を提供。
    - 夜間バッチ更新ジョブ calendar_update_job() を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）やバックフィル日数等の安全策あり。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基盤を実装。差分更新、J-Quants への保存（idempotent）、品質チェック（quality モジュールと連携）を行う設計。
    - ETLResult データクラスを追加（target_date、取得/保存レコード数、quality_issues、errors 等）および to_dict() によるシリアライズ。etl モジュールは ETLResult を再エクスポート。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整などを実装。
- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value / Liquidity 系のファクター計算関数を追加:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（必要行数未満は None）
      - calc_value: per, roe（raw_financials から直近財務データを参照）
    - DuckDB のウィンドウ関数を多用した実装で、外部 API を呼び出さない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（calc_ic）計算（Spearman の ρ）、
      ランク関数 rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を追加。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - src/kabusys/research/__init__.py にて主要関数を公開。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

注記 / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 全てのバックデータ処理で datetime.today() / date.today() を直接参照しない設計。target_date を明示的に渡し、DB クエリでは排他的条件（date < target_date や date = target_date など）を使用。
- OpenAI 呼び出し周りはフェイルセーフ指向:
  - エラー時は例外を上位に伝搬させず（スコアは 0.0 にフォールバック、あるいは銘柄スキップ）処理を継続する箇所が多い。
  - ただし、API キー未設定の場合は ValueError を投げて明示的に失敗させる。
- テスト容易性:
  - ai モジュールの OpenAI 呼び出しは内部関数（_call_openai_api）に分離しており、unittest.mock.patch によって差し替え可能。
- DuckDB 互換性考慮:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約）や list 型バインド回避のための個別 DELETE 実行など、互換性に注意した実装。
- 環境設定の上書き保護機構により、CI/CD や本番環境で OS 環境変数が .env によって意図せず上書きされることを防止。

お問い合わせや不明点があれば、どのモジュール／関数について詳細が必要か教えてください。コードコメントに基づく補足説明や使用例（呼び出し方、期待されるスキーマ等）も用意できます。