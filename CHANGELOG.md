CHANGELOG
=========

すべての重要な変更は Keep a Changelog の原則に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

Unreleased
----------
（現時点で未リリースの予定・改善点）
- テストカバレッジの拡充（特に OpenAI 呼び出しや DuckDB 操作のモック）
- jquants_client のエラー処理・リトライ戦略の共通化
- execution / monitoring パッケージの公開 API 整備（__all__ に含まれるが実装拡充予定）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース（KabuSys 0.1.0）。
  - 日本株自動売買システムの基礎モジュール群を実装。
  - パッケージ公開インターフェース: kabusys.{data, research, ai, ...} を想定したモジュール構成。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定をロードする自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後でも安定）
  - .env パーサーを実装: export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱い等に対応
  - 読み込み時の上書き制御（override）および OS 環境変数を保護する protected set を実装
  - Settings クラスを公開（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定など）
    - env 値、log_level の検証（許容値チェック）を実装
    - パスは Path.expanduser() を使用してホーム展開を実施

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント集計（news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを算出
    - JSON Mode を使用し厳密な JSON 出力を期待。レスポンス不整合に対しては復元ロジック（最外の {} を抽出）を用意
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事トリム（最大 _MAX_CHARS_PER_STOCK=3000、記事数上限 _MAX_ARTICLES_PER_STOCK=10）
    - リトライ戦略: 429・接続断・タイムアウト・5xx を対象に指数バックオフでリトライ（最大 _MAX_RETRIES）
    - レスポンス検証ルールを厳格化（results リスト、各要素に code/score、未知コードを無視、数値検証、±1.0 にクリップ）
    - DuckDB への書き込みは部分失敗を許容する安全な置換（DELETE → INSERT）で冪等性を確保
    - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30）を calc_news_window() で提供（UTC 換算済）

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（_MA_WINDOW=200, weight 70%）とマクロニュース LLM センチメント（weight 30%）を合成し市場レジームを判定（bull/neutral/bear）
    - LLM 呼び出しは gpt-4o-mini、JSON mode、リトライ・エラーハンドリングを実装
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ動作
    - レジーム計算後は market_regime テーブルへトランザクションを用いた冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - lookahead バイアス回避のため内部で date.today()/datetime.today() を参照しない設計（target_date パラメータに依存）

- Research（ファクター計算・特徴量解析）（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離（ma200_dev）、ATR（20日）、平均売買代金・出来高比率などの定量ファクターを実装
    - DuckDB の SQL ウィンドウ関数を活用し、複雑な集計を効率的に取得
    - データ不足時の None ハンドリングを明示
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）の検証・入力チェックを実装
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（同順位は平均ランク）
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出
    - rank() 実装：同順位の平均ランク処理、丸め誤差対策（round(v,12)）

- Data（データプラットフォーム周り）（src/kabusys/data）
  - calendar_management.py
    - market_calendar テーブルを利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 未登録日は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録がある場合は DB 値を優先
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を導入して無限ループを防止
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し market_calendar に冪等保存。バックフィル・健全性チェック（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）を実装
  - pipeline.py / etl.py
    - ETLResult データクラスを公開し、ETL の取得数・保存数・品質問題・エラー一覧を返す仕組みを実装
    - 差分更新・バックフィル方針を実装（最終取得日の数日前から再取得する設計）
    - DuckDB テーブル存在チェックや最大日付取得などのユーティリティ実装
    - 品質チェックモジュール（quality）と連携するための基盤を提供

Changed
- 初期リリースにつき該当なし（新規実装が中心）。

Fixed
- 初期リリースにつき該当なし。

Security
- API キーの使用は引数注入も可能とし、環境変数からの参照のみを避けてテスト容易性を配慮（OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数から取得）。  
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を実装し、誤って上書きされることを防止。

Notes / Design decisions
- ルックアヘッドバイアス対策として、主要な処理はすべて target_date を引数に取り、内部で現在時刻を参照しない設計。
- DuckDB を主たるデータストアとして想定し、executemany の空リストバインド等の互換性問題に配慮した実装（空 params の場合は操作をスキップ）。
- OpenAI 呼び出しは JSON Mode を利用し厳格なフォーマットを期待する一方で、現実的な誤差（前後の余計なテキスト）に対する復元ロジックや堅牢なバリデーションを実装。
- 外部依存を最小化（pandas 等を使用せず標準ライブラリ + duckdb）しているため、Research モジュールは軽量に動作可能。

Authors
- 初期実装: KabuSys 開発チーム（コードベースのヘッダ・ドキュメントに基づき推定）

README 等の補足ドキュメントにて各関数の引数・戻り値（特に DB スキーマ）を明示することを推奨します。