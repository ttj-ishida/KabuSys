# Changelog

すべての重要な変更履歴を記載します。本ファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理
  - .env ファイルおよび環境変数から設定を自動ロードする機能を追加（src/kabusys/config.py）。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - .env パースは export プレフィックス対応、クォートとエスケープの扱い、インラインコメント対応など堅牢な実装。
    - .env 上書き時に OS 環境変数を保護する protected 機構を導入。
  - Settings クラスを提供（settings インスタンスで利用可能）。
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live） / ログレベル検証等のプロパティを提供。
    - env / log_level は有効値検証を行い、不正値時には ValueError を送出。

- AI（ニュースNLP / レジーム判定）
  - ニュースセンチメント解析（score_news）
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）にバッチ送信する機能を実装（src/kabusys/ai/news_nlp.py）。
    - バッチサイズ、記事数・文字数上限、タイムウィンドウ（JST 基準を UTC に変換）を設定。デフォルトで 20 銘柄単位のバッチ処理。
    - API 呼び出し時のリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の型検証、既知コードのみ採用、数値性と有限値チェック）。
    - スコアは ±1.0 にクリップ。スコア取得後は ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT）して部分失敗時の保護を実現。
    - テスト容易性のため _call_openai_api をモック差し替え可能に実装。
    - ルックアヘッドバイアスを防ぐ設計（datetime.today()/date.today() を直接参照しない）。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに書き込む機能を実装（src/kabusys/ai/regime_detector.py）。
    - prices_daily から過去データを用いて ma200_ratio を計算。データ不足時は中立（1.0）とする保護ロジック。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出し、OpenAI により macro_sentiment を取得（記事が無い場合は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI 呼び出しは専用の _call_openai_api 実装を用い、news_nlp と共有しないことでモジュール結合を防止。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。リトライロジックあり。
    - 最終的な regime_score を計算し、"bull"/"neutral"/"bear" ラベルを決定して market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。失敗時は ROLLBACK を試みる。

- データ / ETL / カレンダー
  - ETL パイプライン基本（src/kabusys/data/pipeline.py）
    - 差分取得、バックフィル、品質チェックの設計に基づく ETLResult データクラスを提供（ETL の実行結果を集約）。
    - DuckDB を前提にしたテーブル存在チェックや最大日付取得ユーティリティを実装。
    - 品質チェックはエラーを収集するが、致命的な問題があっても ETL は継続させ呼び出し元に判断を委ねる設計（Fail-Fast ではない）。
    - ETLResult.to_dict() により品質問題をシリアライズ可能。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）の夜間更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で差分取得し保存（バックフィルと健全性チェックあり）。
    - 営業日判定ユーティリティを複数提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。DB 登録が無い場合は曜日ベースのフォールバック（週末除外）で一貫性を保つ。
    - 最大探索範囲上限を設け無限ループを防止。

- リサーチ（ファクター計算・特徴量探索）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB と SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理や行ウィンドウ制御を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、および列の統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB のみで実装。
  - research パッケージのエクスポートを整備（__init__.py）。

- データ API 抽象
  - ETLResult を data.etl から再エクスポート（src/kabusys/data/etl.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API キー未設定時に明示的な ValueError を送出することで、意図しない無認証呼び出しや誤用を防止（score_news, score_regime）。

### Notes / 設計上の注意
- ルックアヘッドバイアス回避: ほとんどの処理で date / target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計。分析・バックテスト利用時に重要。
- OpenAI 呼び出しには JSON Mode を想定した厳格なレスポンスパースとフォールバック処理を実装。レスポンス不整合時はログを残してスキップ／フォールバックする方針。
- DuckDB バインドの互換性（executemany の空リスト制約など）に配慮した実装がされている。
- テスト容易性: _call_openai_api の差し替え（unittest.mock.patch）や KABUSYS_DISABLE_AUTO_ENV_LOAD による環境制御など、ユニットテストを考慮したフックを用意。

もしこのリリースノートに記載してほしい追加の観点（例: 特定ファイル単位の変更点、API 使用例、後続予定の機能など）があれば教えてください。