CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under semantic versioning.

[Unreleased]
------------

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリースを追加。
- パッケージメタ情報
  - パッケージのバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - パッケージ公開用 __all__ を定義（data, strategy, execution, monitoring）。
- 設定・環境変数管理（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。
  - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、行末コメント処理）。
  - OS 環境変数を保護する protected パラメータや override ロジックを実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを実装してアプリケーション設定（J-Quants、kabu API、Slack、DB パス、環境モード、ログレベルなど）を提供。
  - 環境変数の必須チェック（未設定時は ValueError を発生）。
  - env/log_level の検証（許容値セットを明示）。
- AI モジュール（src/kabusys/ai/）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基にニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントをスコア化し、ai_scores テーブルへ書き込む機能を実装。
    - ニュースの対象時間ウィンドウ計算（JST → UTC の変換）を提供（calc_news_window）。
    - バッチ処理（1回あたり最大 _BATCH_SIZE 銘柄）、記事トリム（_MAX_CHARS_PER_STOCK）と1銘柄あたりの最大記事数制限を実装。
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーション（JSON パース復元処理、results 配列・code/score 検証、スコアのクリップ）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - DuckDB の executemany に空リストを渡せない制約に配慮した保存ロジック（DELETE→INSERT、params の空チェック）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出のキーワードリストと LLM 呼び出し、リトライ・フォールバック（API失敗時は macro_sentiment=0.0）を実装。
    - Look-ahead バイアス防止設計（datetime.today()/date.today() を使用しない、prices_daily クエリは target_date 未満のデータのみ使用）。
    - OpenAI クライアント呼び出し独立化（news_nlp とは別実装でモジュール結合を抑制）。
- 研究（Research）モジュール（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース実装。
    - データ不足時の None 処理やログ出力を考慮。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - horizons 引数の検証、スピアマン相関（ランク相関）実装、同順位の平均ランク処理を実装。
  - research パッケージの __all__ を整備して主要関数を再エクスポート。
- データ（Data）モジュール（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した振る舞い、探索上限（_MAX_SEARCH_DAYS）など設計。
    - calendar_update_job による J-Quants からの差分取得と冪等保存処理の流れとバックフィル・健全性チェックを実装（jquants_client 経由）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装して ETL 実行結果と品質チェック結果・エラー情報を保持。
    - 差分更新・バックフィル・品質チェック設計に基づく ETL 実装方針（jquants_client と quality モジュールの統合を想定）。
    - etl.py で pipeline.ETLResult を再エクスポート。
  - DuckDB をデータ基盤として想定した実装（多くの関数が DuckDB 接続を受け取る設計）。
- 実装全体
  - Docstring による設計意図・処理フロー・フェイルセーフ挙動の明記（テスト性・ルックアヘッドバイアス対策など）。

Changed
- 初回リリースのため該当なし。

Fixed / Robustness improvements
- .env パーサの強化により、クォート内のエスケープ、export プレフィックス、コメント判定の曖昧さに対応。
- OpenAI 呼び出しに対する堅牢なリトライ・バックオフ実装（429/ネットワーク/タイムアウト/5xx）と、API 異常時のフォールバック（マクロセンチメントやニューススコアは 0.0 とみなして継続）。
- OpenAI レスポンスの JSON パースで余分なテキストが混入するケースへの復元処理（最外の {} を抽出）を追加。
- DB 書き込みでのトランザクション管理（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK の安全な実行、ROLLBACK 失敗時のログ出力。
- DuckDB の executemany に空リストを渡せない点への対応（書き込み前に空チェック）。
- market_calendar の NULL 値ハンドリングと警告ログ出力。
- ルックアヘッドバイアスを避けるため、すべてのスコア・集計関数が外部から渡される target_date に基づいて処理する設計。

Security
- API キーやトークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は必須として Settings クラスで取得し、未設定時は明示的にエラーを出すことで安全性を確保。

Documentation
- 各モジュール・関数に詳細な docstring を追加して処理フロー・設計意図・例外ハンドリング方針を明記。

Notes / Known limitations
- 一部モジュール（例: jquants_client, quality モジュールや strategy/execution/monitoring の具体実装）はこのリリースに含まれない／参照のみ（インタフェース依存）。本 CHANGELOG は提供されたソースコードから推測可能な変更点を記載しています。
- OpenAI API に依存する機能は外部 API の制約（レート制限・コスト）に左右されるため、本実装では堅牢化（リトライ・フォールバック）を行っているが、運用時の監視とレート制御は必要。

References
- 各モジュールの詳細は該当する docstring を参照してください（src/kabusys/**）。