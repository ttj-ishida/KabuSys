CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
https://keepachangelog.com/ja/1.0.0/

注: この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴（コミット単位）ではなく、初期公開相当の機能一覧と設計上の注意点をまとめたものです。

[Unreleased]
------------

なし

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
  - パッケージメタデータ: __version__ = "0.1.0"、公開モジュール群を __all__ で定義。
- 環境設定管理 (kabusys.config)
  - .env ファイル／環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルートの探索ロジックを実装（.git または pyproject.toml を起点）。
  - .env パーサーを実装（コメント行、export プレフィックス、クォート文字列、エスケープ対応、インラインコメントルール）。
  - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 環境変数保護機構（OS 環境変数は protected として上書きを防止）。
  - Settings クラスを提供し、主要設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
      SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。
  - 設定値のバリデーション（KABUSYS_ENV／LOG_LEVEL の有効値チェック）、未設定時は ValueError を送出する _require() を実装。
- AI 関連 (kabusys.ai)
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（ai_scores）を生成して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window() で提供。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）・1 銘柄あたりの最大記事数/文字数制限、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - リトライ方針: 429/ネットワーク断/タイムアウト/5xx を指数バックオフで再試行。その他のエラーはスキップして継続（フェイルセーフ）。
    - DuckDB executemany の互換性考慮（空パラメータ群は送らない）。
    - テストのために _call_openai_api を patch できる設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベース（複数キーワード定義）で titles を取得し、OpenAI (gpt-4o-mini) により -1.0〜1.0 のマクロセンチメント評価を行う。
    - API 呼出しのリトライ/バックオフ、API 失敗時の安全フォールバック（macro_sentiment=0.0）。
    - DuckDB に対するクエリ実装、無データ/データ不足時の中立扱い（ma200_ratio=1.0）。
    - テスト用に _call_openai_api を差し替え可能。
- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを使った営業日判定ユーティリティ群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合の曜日ベースフォールバック（原則：土日非営業）。
    - next/prev_trading_day 等は検索上限 (_MAX_SEARCH_DAYS) を設けて無限ループを回避。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルや健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーログ等を集約）。
    - 差分取得・保存・品質チェックの方針とユーティリティを実装（J-Quants クライアント連携を想定）。
    - データベース最終日取得ユーティリティやテーブル存在チェックを提供。
- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB SQL を活用し、date と code をキーにした結果リストを返す設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（任意ホライズン）、IC（Spearman ρ）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。
  - 研究用の小ユーティリティを公開（zscore_normalize の re-export 等）。
- 監視・実行・その他
  - package の公開 API 組織化（__all__ 等）および多くの機能に対するログ出力を追加。

Changed
- n/a（初期リリースのため変更履歴はなし）

Fixed
- n/a（初期リリースのため修正履歴はなし）

Notes / 重要事項
- 必須環境変数:
  - OPENAI_API_KEY: news_nlp.score_news / regime_detector.score_regime を呼ぶ際に必要（引数で上書き可能）。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などは Settings 経由で必須チェックあり。未設定時は ValueError が発生します。
- 自動 .env ロード:
  - デフォルトでパッケージ import 時にプロジェクトルートの .env/.env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください（テスト時推奨）。
- DuckDB 互換性:
  - DuckDB の executemany が空リストを受け付けないバージョン（例: 0.10）の挙動を考慮した実装になっています（空パラメータ時は呼ばない）。
- ルックアヘッドバイアス対策:
  - AI / 研究系処理はすべて内部で datetime.today()/date.today() を参照しない設計（target_date ベースで明示的に処理）。prices_daily のクエリは target_date 未満／等の条件でルックアヘッドを防止。
- フェイルセーフ設計:
  - OpenAI API 呼び出し失敗時は多くのケースで例外を上位へ伝えずフェイルセーフ（0.0 やスキップ）へフォールバックする実装。DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を担保し、失敗時は ROLLBACK を試みる。
- テストサポート:
  - _call_openai_api の差し替え（unittest.mock.patch）により API 呼び出しをモック可能。自動環境ロードの無効化フラグもテストに役立ちます。

今後の改善案（参考）
- ai モジュールのモデルやバッチ設定を Settings 経由で外部化（現在は定数としてコード内に定義）。
- より詳細なエラー分類とモニタリング（Slack 通知等）を追加。
- ETL ワークフロー（pipeline）を CLI やスケジューラへ接続するためのラッパー実装。

以上