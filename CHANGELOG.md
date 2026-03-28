# Changelog

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and aims to be semantic.

<!-- NOTE: 日付はこのリリース時点のものを記載しています。 -->

## [0.1.0] - 2026-03-28

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
- パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージ公開対象モジュールとして `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロード。
  - プロジェクトルート探索は実ファイル位置から親ディレクトリへ遡る方式で .git または pyproject.toml を検出。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動ロード制御用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - J-Quants / kabuステーション / Slack / データベースパス（duckdb/sqlite）/ 環境モード（development/paper_trading/live）/ ログレベル判定
  - 必須環境変数未設定時は ValueError を投げる `_require` 実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄毎にニュースをまとめて OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
  - ニュース収集ウィンドウ（JST 基準）計算ユーティリティ `calc_news_window`（UTC naive datetime を返す）。
  - バッチ/チャンク処理（1回あたり最大 20 銘柄）とトリム制御（最大記事数・文字数）実装。
  - OpenAI 呼び出しのエラーハンドリング（429/接続断/タイムアウト/5xx に対する指数バックオフリトライ）。
  - レスポンス検証ロジック（JSON パース、results 配列、code の照合、スコアの数値化・有限性チェック）。
  - ai_scores テーブルへの冪等的書き込み（取得済みコードのみ DELETE → INSERT を行い、部分失敗時に既存スコアを保護）。
  - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` は patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を算出。
  - prices_daily と raw_news を参照して ma200_ratio と macro_sentiment を算出し、合成スコアをクリップしてラベル判定。
  - OpenAI 呼び出しは gpt-4o-mini を利用。API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
  - API 呼び出しの再試行ロジック、タイムアウト、5xx の扱いなど堅牢なエラーハンドリング実装。
  - ルックアヘッドバイアス対策: datetime.today() / date.today() を内部で参照せず、target_date 引数に基づく決定を徹底。

- ETL / データパイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETL の公開インターフェース `ETLResult` を定義（dataclass）。ETL 実行結果の集約、品質問題一覧、エラー一覧、ヘルパー属性（has_errors, has_quality_errors）を提供。
  - ETL 実行中の差分フェッチ・保存・品質チェックに関する設計（差分更新、バックフィル、部分保存の安全性）に対応するユーティリティを整備。
  - DuckDB 上の最大取得日検査、テーブル存在チェック等の内部ユーティリティを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar を使った営業日判定 API を提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - カレンダー未取得時のフォールバックとして曜日ベース（平日 = 営業日）ロジックを実装。
  - カレンダー更新バッチ job（calendar_update_job）: J-Quants API から差分取得・バックフィル・健全性チェックを行い、冪等的に保存。
  - 最大探索日数・先読み・バックフィル等の安全パラメータを導入して無限ループや異常データを防止。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - calc_value: PER、ROE（raw_financials からの財務データ使用）
    - 計算は DuckDB の SQL を活用し、外部 API を呼ばない構成
  - 特徴量探索モジュール（feature_exploration）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: Spearman ランク相関（IC）計算（不足データは None を返す）
    - rank: 同順位を平均ランクとするランク付けユーティリティ（丸めにより ties を安定化）
    - factor_summary: カラム毎に count/mean/std/min/max/median を算出する統計サマリー

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の保護: .env の自動ロードでは既存 OS 環境変数を protected として上書き回避。自動ロードを無効化するオプションを追加。

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス対策を全 AI/研究処理で徹底（target_date ベース、内部で現在日時を参照しない）。
- OpenAI API 呼び出しは JSON Mode を想定し、レスポンスの頑健なパース処理と失敗時のフォールバック（0.0）を採用。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装を行い、互換性を確保。
- テスト容易性を考慮し、外部 API 呼び出しを差し替え可能に設計（各モジュールの `_call_openai_api` はパッチ可能）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・テストおよび統合テスト。
- J-Quants / kabu API クライアント周りの追加のエラーハンドリングとリトライ戦略の整備。
- ドキュメント（Usage guide、StrategyModel.md、DataPlatform.md）の拡充。