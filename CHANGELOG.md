CHANGELOG
=========
すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン
----------------
- Unreleased: —  
- リリース済みバージョン: 0.1.0（初回リリース） — 2026-04-04

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期実装: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py
    - パッケージのバージョンを定義（__version__ = "0.1.0"）し、公開サブパッケージを列挙。
- 環境設定／ロード機能
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および OS 環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）。
    - .env パース実装（export 句、シングル/ダブルクォート、エスケープ、コメント処理対応）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - protected 機能により OS 環境変数の上書きを防止。
    - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境などのプロパティを定義。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）と必須キー取得のユーティリティ。
- AI ニュース NLP / レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 時刻）計算。
    - バッチ処理（最大 20 銘柄 / バッチ）、記事・文字数トリム、JSON Mode のレスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで処理し、失敗時は個別チャンクをスキップするフェイルセーフ設計。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で書き込むレジーム判定機能を実装。
    - prices_daily からの MA 計算、raw_news からマクロキーワードでのフィルタ、OpenAI 呼び出し（gpt-4o-mini）、スコア合成とラベリング（bull/neutral/bear）。
    - API 呼び出しは最大リトライ、非致命的エラーは macro_sentiment=0.0 で継続。DB への書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で実装。
- データプラットフォーム（Data）関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の照会・更新ロジックを提供。
    - 営業日判定ユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベース（平日を営業日）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新する処理を実装（先読み・バックフィル・健全性チェックあり）。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスと ETL パイプラインのインターフェース（差分取得、保存、品質チェックの考え方）を追加。
    - _get_max_date などのユーティリティを含む ETL 基盤（J-Quants クライアント連携を想定）。
  - src/kabusys/data/__init__.py
    - public API の整備（pipeline の ETLResult を再エクスポート）。
- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ／流動性（20 日 ATR・平均売買代金・出来高比率）、バリュー（PER/ROE）などのファクター計算機能を実装。
    - DuckDB の SQL ウィンドウ関数を利用して効率的に計算。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman rank）計算（calc_ic）、rank ユーティリティ、factor_summary（統計サマリー）を実装。
    - pandas 等の外部依存を使わずに標準ライブラリ＋DuckDBで実装。
  - src/kabusys/research/__init__.py
    - 主要関数群のエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。
- 研究補助 / テストのためのフックや互換性考慮
  - DuckDB のバージョン差異（executemany の空リスト等）や API SDK の変化（status_code の有無）を考慮した互換性処理を導入。
  - API 呼び出し失敗時のフォールバック（例: macro_sentiment=0.0、チャンクスキップ、ログ出力）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数の取り扱いに配慮:
  - OS 環境変数を protected として .env による上書きを防止する実装。
  - OpenAI API キーや各種シークレットは Settings 経由で取得し、未設定時は ValueError を発生させて明示的な設定を要求。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードをテスト等で抑止可能。

Notes / 実装上の制約と設計方針
- ルックアヘッドバイアス防止:
  - AI スコアリングやレジーム判定、ファクター計算は内部で datetime.today()/date.today() を参照せず、target_date 引数に依存する設計。
  - DB クエリは target_date 未満／以前の条件を用いるなど、将来データの参照を避ける工夫を実装。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）の一部失敗は局所的にフォールバック（デフォルトスコア、チャンクスキップ）して処理継続する設計。
- テスト容易性:
  - OpenAI 呼び出し部分は内部の _call_openai_api をモック可能にしており、単体テストで外部依存を差し替えやすくしている。
- 未実装・制限:
  - ファクター: PBR・配当利回りは現バージョンでは未実装（calc_value に注記あり）。
  - monitoring サブパッケージは __all__ に含まれているが、この差分には具体実装ファイルが含まれていない（将来追加予定）。
  - DuckDB のバインドやバージョン差による挙動に注意（executemany の空リスト不可等）。

開発者向けメモ
- API キー取得:
  - OpenAI: api_key 引数を明示的に渡すか、環境変数 OPENAI_API_KEY を設定する必要あり（news_nlp/regime_detector 共通）。
- ログと診断:
  - 各モジュールは詳細な logger 呼び出しを行っているため、LOG_LEVEL を環境変数で調整するとデバッグが容易。
- DB 書き込み:
  - ai_scores / market_regime 等への書き込みは冪等化（DELETE → INSERT）されており、部分失敗が他データを不必要に上書きしないよう配慮している。

----

（この CHANGELOG は、提供されたソースコード内容からの推測に基づき作成しています。実際のリリースノートとして公開する前に、リリース日・追加機能の確定・実装差分をプロジェクトの公式記録と照合してください。）