# Keep a Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従っています。  
非破壊的でない変更（将来的に互換性が壊れる可能性があるもの）は Breaking Changes セクションに明記します。

## [0.1.0] - 2026-04-02

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主に以下のサブパッケージ・モジュールを含みます。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - 公開サブパッケージを __all__ で宣言（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local を自動読み込みするユーティリティを実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env パース（export 構文、クォート・エスケープ、インラインコメントの取り扱い）に対応する堅牢なパーサを提供。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / ログレベル等の設定をプロパティ経由で取得可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 環境変数未設定時の明示的なエラー（_require）やバリデーション（KABUSYS_ENV, LOG_LEVEL）の実装。

- AI（自然言語処理・市場判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事をまとめて OpenAI（gpt-4o-mini）に投げて銘柄別センチメントを算出し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算（calc_news_window）。
    - 記事集約、API バッチ送信（チャンク化、最大20銘柄/チャンク）、レスポンス検証、スコアの ±1.0 クリップ、DuckDB への冪等的書き込み（DELETE→INSERT）を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライ・フォールバックの実装。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api の位置を想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - MA 計算（_calc_ma200_ratio）、マクロ記事抽出（_fetch_macro_news）、LLM 呼び出しとリトライ（_score_macro）を実装。
    - レジームスコア合成・閾値判定・market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入（引数 or OPENAI_API_KEY）をサポート。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベースでフォールバックするロジックを実装。
    - calendar_update_job による J-Quants からの差分取得 & 冪等更新（バックフィル・健全性チェック含む）を実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプライン設計に沿った基盤実装（差分取得、保存、品質チェックの枠組み）。
    - ETLResult データクラス（src/kabusys/data/pipeline.py 内）を追加。処理結果の集約・シリアライズ（to_dict）を提供。
    - DuckDB の存在チェック・最大日付取得等のユーティリティを実装。
    - デフォルトのバックフィル/カレンダー先読み等の設定値を定義。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートして公開インターフェースを簡略化。

  - src/kabusys/data/__init__.py
    - data サブパッケージの基礎ファイル（空だがパッケージ化）。

- リサーチ（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL と窓関数を多用し、ルックアヘッドバイアスを防ぐ実装。
    - 想定テーブル: prices_daily, raw_financials。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic, Spearman ρ）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使わず標準ライブラリのみで実装。

  - src/kabusys/research/__init__.py
    - 研究向け API を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize など）。

- 研究用ユーティリティの再エクスポート
  - src/kabusys/research/__init__.py は kabusys.data.stats の zscore_normalize を再エクスポート。

### 改良 (Changed)
- 設計上のセーフガードとテスト性向上
  - AI モジュール・研究モジュール・ETL の各所で「datetime.today()/date.today() を参照しない」方針を採用し、ルックアヘッドバイアスを回避。
  - OpenAI 呼び出しのラッパー関数をモジュール内で分離し、ユニットテストでモックしやすくした（news_nlp._call_openai_api と regime_detector._call_openai_api は独立実装）。
  - DuckDB の executemany に対する注意（空リスト不許可）や SQL の互換性を考慮した実装が多数導入。

- 冪等性・フォールバック
  - DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 想定）。
  - 外部 API 失敗時は処理を中断せずフェイルセーフ（デフォルトスコアやスキップ）で継続する設計。

### 修正 (Fixed)
- （初期リリースのため主に実装完了項目。既知の軽微な取り扱い上の注意をログで明示する実装を多数含む）
  - market_calendar の is_trading_day が NULL の場合に警告を出しフォールバックする挙動を明確化。
  - OpenAI API のエラー種別（429, ネットワーク, タイムアウト, APIError の status_code による 5xx 判定等）に基づくリトライロジックを整備。

### 既知の制約 (Known issues)
- DuckDB バインド挙動やバージョン差異に依存する箇所があるため、DuckDB のバージョン互換性に注意が必要（特に executemany の空リスト取り扱い）。
- OpenAI のレスポンスが必ず JSON のみで返るとは限らないため、news_nlp/respose のパースでは前後テキスト混入時の復元処理を行っているが、稀に期待通りにパースできない場合は当該チャンクをスキップする。
- 一部モジュールの外部依存（J-Quants クライアントや jquants_client.save_* 等）は別途実装が必要。

### セキュリティ (Security)
- API キーは引数経由または環境変数（OPENAI_API_KEY 等）で注入する方式。コード中でハードコーディングは行っていません。
- .env 自動読み込み時に既存 OS 環境変数を保護する仕組みを導入（protected set）。

----

今後の予定（例）
- strategy / execution / monitoring サブパッケージの詳細実装（現状はパッケージエクスポートに含むが実装ファイルは別途）。
- テストカバレッジ拡充、CI による DuckDB バージョン互換テスト、OpenAI 呼び出しの契約上の安定化対策。
- ドキュメント（API リファレンス、運用手順、データスキーマ）の追加。

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース目的に合わせて適宜補正してください。）