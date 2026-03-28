CHANGELOG
=========

すべての変更は Keep a Changelog に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-28
------------------

最初の公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加。バージョンは `0.1.0`。
  - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル（プロジェクトルートの .env / .env.local）を自動読み込みする仕組みを実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため CWD に依存しない点が特徴。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護するための protected オプションをサポート。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途想定）。
  - .env 解析はシェル風の `export KEY=val`、シングル/ダブルクォートおよびエスケープ、行コメント（#）の扱いに対応。
  - `Settings` クラスを提供。主なプロパティ:
    - J-Quants / kabu ステーション / Slack / データベースパス等の取得（必須環境変数は未設定時に ValueError を投げる）。
    - `duckdb_path`, `sqlite_path` のデフォルトを設定。
    - `env`（development/paper_trading/live）、`log_level` のバリデーション。
    - `is_live`, `is_paper`, `is_dev` のユーティリティプロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols / ai_scores を対象に OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア付与を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime）を扱う `calc_news_window` を提供。
    - 1銘柄当たり最大記事数や最大文字数でトリミング（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 20 銘柄 / API コール）、JSON Mode でのレスポンス検証、スコア ±1.0 クリップ、堅牢な検証ロジックを実装。
    - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx を指数バックオフで再試行。非再試行エラーはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性と部分失敗時の保護を実現。

  - 市場レジーム判定 (`regime_detector.score_regime`)
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定し `market_regime` に書き込む処理を実装。
    - 判定ロジック: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）の合成によりスコア化。
    - LLM は gpt-4o-mini を利用、最大記事数やリトライ等はニュース NLP と同様の堅牢性を持つ。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から取得。未設定時は ValueError。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実施。失敗時は ROLLBACK。

- データモジュール (kabusys.data)
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由）。
    - 営業日判定ヘルパーを提供: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 安全策（最大探索日数、バックフィル、健全性チェック）を組み込み。

  - ETL パイプライン (`pipeline`)
    - 差分更新・保存・品質チェックのワークフローに沿った ETL の骨組みを実装。
    - ETL 実行結果を表す `ETLResult` データクラスを公開（kabusys.data.etl から再エクスポート）。品質問題・エラーの収集機構を持つ。
    - デフォルトの backfill やカレンダー先読み日数等の定数を定義。

  - jquants_client 経由の外部 API 連携を想定した設計（fetch / save の呼び出し点を用意）。

- Research モジュール (kabusys.research)
  - ファクター計算 (`research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）を DuckDB を用いて計算する関数を提供。
    - データ不足時の None 扱い、SQL ベースで高効率に計算する設計。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算（任意ホライズン）、IC（Spearman rank）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB で完結する実装。

- その他
  - kabusys.ai.__all__ で `score_news` を公開。
  - research パッケージで多くの関数をまとめて公開（zscore_normalize 再利用等）。
  - ロギングを各モジュールで適切に利用し、情報/警告/例外ログを充実させてデバッグ性を確保。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Security
- 初リリースのため該当なし。
- 注意: OpenAI API キーや各種トークンは環境変数経由で取り扱う設計。 .env の取り扱いに注意して運用してください。

Migration notes / Usage notes
- OpenAI を利用する機能（news_scorer / regime_detector）は `OPENAI_API_KEY` の設定（または関数引数）を必須とします。未設定時は ValueError が発生します。
- 自動で .env を読み込ませたくないテスト等の場面では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を想定したスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）が必要です。ETL / calendar_update_job / score_news / score_regime を実行する前にスキーマを準備してください。
- ai モジュールは外部 API 呼び出しに対しフェイルセーフ設計（API 失敗時はスコアを 0.0 にするかスキップ）を採用しています。運用時はログで失敗を監視してください。

開発者向けメモ
- テスト時には OpenAI 呼び出し部分（_call_openai_api）を patch してモック化することを想定した設計になっています。
- DuckDB に対する executemany に空リストを渡すとエラーとなるバージョンがあるため、コード中で空チェックを行っています。

Contributors
- 初期実装者（コードベースから推測）による最初の実装。

--- 

この CHANGELOG はコード内容からの推測に基づき作成しています。実際のリリースノート作成時は実際の変更履歴・コミットログ・担当者の記録を参照して更新してください。