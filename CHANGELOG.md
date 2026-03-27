CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-27
------------------

初回公開リリース。

Added
- パッケージ基礎
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサー強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートとバックスラッシュエスケープに対応。
    - インラインコメント判定ロジック（クォート有無での扱い差分）実装。
  - .env の読み込み優先度: OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として上書き回避。
  - Settings クラスを導入し、アプリ設定をプロパティ経由で提供:
    - J-Quants / kabuステーション / Slack / DB パス等の必須・デフォルト設定を提供。
    - KABUSYS_ENV のバリデーション (development/paper_trading/live) と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のブールヘルパー。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI(gpt-4o-mini) の JSON Mode を使ってセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（デフォルト 20 銘柄/コール）、記事数・文字数トリム（最大記事数・最大文字数）を実装。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx）を実装（指数バックオフ）。
    - レスポンスの堅牢なバリデーションとスコアのクリップ（±1.0）。
    - スコアは ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - calc_news_window(target_date) を公開し、JST ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime に変換するユーティリティを提供。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは独立実装でモジュール結合を避け、失敗時は macro_sentiment=0.0 でフェイルセーフにフォールバック。
    - リトライ・バックオフ、OpenAI API のエラー種別別ハンドリングを実装。
    - テストで差し替え可能な _call_openai_api を用意。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を使った営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日（土日）ベースでフォールバック。
    - next/prev/search における探索上限（_MAX_SEARCH_DAYS）や健全性チェックを導入。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新するバッチ処理を実装（バックフィル・健全性チェック含む）。
    - jquants_client を通じた fetch/save の呼び出しを利用し、API エラー時は安全にログを残して処理を中断。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入して、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化。
    - 差分更新・バックフィル（デフォルト backfill_days=3）・品質チェックの設計方針を実装（詳細はモジュール内 docstring）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- 研究用モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）等のファクター計算を実装。
    - DuckDB SQL を主体に実装し、prices_daily / raw_financials のみ参照。結果は (date, code) をキーとする辞書リストで返却。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman ランク相関）、rank、factor_summary（基本統計量）等の探索用ユーティリティを実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。

Changed
- なし（初回リリースのため全て追加項目）

Fixed
- なし（初回リリース）

Security
- 環境変数の上書きに関する配慮:
  - 自動 .env ロード時に OS 環境変数を protected として上書きを回避。
  - 必須値を取得する _require() は未設定時に ValueError を投げて安全に失敗させる。

Notes / Design decisions
- ルックアヘッドバイアス防止:
  - 全ての日時計算で datetime.today()/date.today() を関数内部で直接参照しない方針（target_date を明示的に渡す設計）。
- 可観測性:
  - 各処理に適切な logger 呼び出しを追加（info/warning/debug）。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）失敗時は例外を必要以上に投げず、ログを残して安全に継続または中断する戦略を採用。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部関数を patch して差し替え可能にし、ユニットテスト容易性を確保。

今後の予定（想定）
- strategy / execution / monitoring モジュールの具体実装と統合テスト。
- J-Quants / kabu API クライアントの安定化とエラーハンドリング強化。
- ドキュメント・使用例・CI テストの整備。

ライセンス、貢献方法、詳細な使用法はリポジトリの README や各モジュールの docstring を参照してください。