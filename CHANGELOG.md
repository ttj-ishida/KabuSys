CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
形式は Keep a Changelog に準拠しています。

リリース方針:
- バージョン番号は semver に従います。
- 各リリースには追加（Added） / 変更（Changed） / 修正（Fixed）などのカテゴリで要約を記載します。

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0 を公開
  - パッケージ概要や公開モジュールを定義（src/kabusys/__init__.py）。
  - 主要サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ を通じて公開予定のモジュール群を明示）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
  - .env 行パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなし行でのインラインコメント（#）の取り扱いを改善（直前が空白/タブの場合にコメントとみなす）。
  - _load_env_file による読み込みで OS 環境変数を保護する protected 引数を導入（.env.local 上書き時も OS 変数は保持）。
  - Settings クラスを提供し、必要な設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証とユーティリティプロパティ（is_live 等）。
    - デフォルト DB パス: duckdb -> data/kabusys.duckdb, sqlite -> data/monitoring.db。

- AI モジュール（src/kabusys/ai/）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ（最大20銘柄）スコアリングを行う。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で厳密計算。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン膨張を制限。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx を対象）と指数バックオフを実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score 構造、未知コードの無視、スコアの ±1.0 クリップ）を実装。
    - DuckDB 互換性のため、書き込みは部分置換（DELETE → INSERT）で実行し、部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（_call_openai_api を patch で mock 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して
      市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする。
    - マクロ記事は news_nlp.calc_news_window と raw_news から取得、OpenAI による JSON 出力をパースして macro_sentiment を算出。
    - API失敗やパースエラーは macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - リトライ/バックオフ（最大試行回数と指数バックオフ）を実装。
    - DB 書き込みは明示的な BEGIN / DELETE / INSERT / COMMIT のパターンで冪等性を確保し、失敗時は ROLLBACK を試行。

- 研究（research）モジュール（src/kabusys/research/）
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - 全て DuckDB を用いた SQL ベース実装で、外部 API には依存しない。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で取得（horizons の検証と上限チェックあり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（Information Coefficient）を実装（有効レコードが3未満なら None）。
    - rank: 値をランクに変換（同順位は平均ランク、浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
  - research パッケージで必要関数を再エクスポート。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが無い／欠損時は曜日ベース（週末は非営業日）でフォールバックする一貫性のあるロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックあり。
  - pipeline.py / etl.py
    - ETLResult データクラスを導入して ETL 実行結果を統一表現（品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールを利用）。
    - DuckDB の最大日付取得などのユーティリティを提供。

Changed
- 一貫した設計方針を明記（各モジュール）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - OpenAI 呼び出しは各モジュールで独立実装。テスト可能性のため差し替え可能にしている（モジュール間でプライベート関数を共有しない）。

Fixed
- DuckDB のバージョン依存性に配慮した互換処理を導入
  - executemany に空リストを渡せない制約を回避するチェックを追加（ai/news_nlp.py の書き込み部など）。

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env による OS 上書きを防止）。

Notes / 使用上の注意
- OpenAI API の利用には API キーが必要（各関数は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照）。
- 主要な必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DuckDB ファイルパス: data/kabusys.duckdb（Settings.duckdb_path）
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われる。パッケージ配布後やテスト時に不要な自動読み込みを抑えるには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

今後の予定（短く）
- モジュール間のドキュメント補完（使用例、API レベルの docstring 充実）。
- jquants_client / quality / monitoring 等の統合テストと CI ワークフロー整備。
- 追加の研究用ユーティリティ（ファクター群拡充）と運用監視機能の実装。

----- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートに基づく正確な差分は、バージョン管理システムの履歴を参照してください。