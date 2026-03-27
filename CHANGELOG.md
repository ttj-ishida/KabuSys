Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

記載ルール:
- 変更はバージョンごとにまとめ、最も新しいものを上に置きます。
- 可能な限り変更の理由・影響と設計上の注意点を記載します。

Unreleased
---------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- 初回公開。kabusys パッケージの初期実装を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
  - 設定・環境変数管理 (src/kabusys/config.py)
    - .env ファイル（.env, .env.local）と OS 環境変数の読み込み機能を実装。
    - プロジェクトルート検出機能（.git または pyproject.toml を起点）を実装し、CWD に依存しない自動ロードを実現。
    - export KEY=val 形式、クォート文字列、インラインコメント処理などに対応した .env パーサを実装。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, 環境モード、ログレベル等の取得とバリデーション）。
    - 必須環境変数未設定時は ValueError を送出する _require() を実装。
  - AI モジュール (src/kabusys/ai/)
    - ニュース NLP (src/kabusys/ai/news_nlp.py)
      - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
      - バッチ送信（デフォルト最大20銘柄/リクエスト）、1銘柄あたりのトークン上限（記事数・文字数でトリム）やレスポンス検証を実装。
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装。
      - レスポンスの堅牢なパース（前後余計なテキストが混入するケースも考慮）とスコアクリップ（±1.0）。
      - 成果を ai_scores テーブルへ冪等的に保存（DELETE → INSERT、部分失敗時に既存スコアを保護）。
      - テスト用に _call_openai_api を差し替え可能な実装になっている。
    - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - prices_daily / raw_news を参照し、OpenAI（gpt-4o-mini）により macro_sentiment を取得。
      - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
      - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
      - API 呼び出し実装は news_nlp 側と独立（モジュール結合を避ける設計）。
  - データプラットフォーム関連 (src/kabusys/data/)
    - カレンダー管理 (src/kabusys/data/calendar_management.py)
      - JPX カレンダー取得の夜間ジョブ実装（calendar_update_job）。J-Quants API 経由で差分取得し保存。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB にデータがない場合は曜日ベースのフォールバック（週末除外）を行う。
      - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）を採用し無限ループや過剰探索を防止。
    - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
      - ETLResult データクラスを定義し、ETL 実行結果（取得件数、保存件数、品質チェック結果、エラーメッセージ等）を集約。
      - 差分更新・バックフィル・品質チェックの設計に準拠したユーティリティ関数を実装（最終日取得、テーブル存在確認等）。
      - jquants_client と quality モジュールを利用して idempotent な保存と品質検査を行う想定の実装。
      - DuckDB 0.10 の executemany の制約（空リスト不可）に配慮した実装。
    - data パッケージに ETLResult を再エクスポート（src/kabusys/data/__init__.py）。
  - リサーチ（研究）モジュール (src/kabusys/research/)
    - ファクター計算 (src/kabusys/research/factor_research.py)
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または NULL の場合は None）。
      - DuckDB を用いた SQL 中心の実装で外部 API にアクセスしない設計。
    - 特徴量探索 (src/kabusys/research/feature_exploration.py)
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
      - calc_ic: Spearman ランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）時は None。
      - rank: タイ付きの平均ランク計算（丸め処理により ties の誤差を抑制）。
      - factor_summary: 各カラムの基本統計（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
  - 共通設計・運用上の配慮
    - ルックアヘッドバイアス防止のため各処理は datetime.today()/date.today() を直接参照しない（target_date を明示的に渡す）。
    - OpenAI 呼び出しに対してリトライ戦略（指数バックオフ）、レスポンス検証、失敗時のフォールバックを実装し、処理継続性を重視。
    - DB 書き込みは冪等性を重視（DELETE→INSERT の形や ON CONFLICT を想定）。
    - テスト容易性を考慮し、OpenAI 呼び出し点を差し替え可能にしている（モック化しやすい実装）。
    - ロギング（logger）を各モジュールで利用し、警告・情報の出力を充実。

Fixed
- 特になし（初回リリース）

Changed
- 特になし（初回リリース）

Security
- OpenAI API キーや各種トークン・パスワードは環境変数で管理。必須変数未設定時は明示的なエラーを返す。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能を提供（テスト時の秘匿対策に有用）。

Notes / Limitations
- jquants_client, quality モジュールや一部テーブル定義（prices_daily, raw_news, market_regime, ai_scores, raw_financials, news_symbols 等）は本リポジトリ内に含まれていないため、実行にはそれらの定義とデータが必要。
- news_nlp / regime_detector といった AI 関連は外部 API（OpenAI）に依存し、使用料・レート制限に注意が必要。
- DuckDB のバージョン依存（特に executemany の空リスト取り扱い）に注意。実装は互換性を考慮しているが、環境での確認を推奨。
- calendar_update_job 等は外部 API 呼び出しや日付基準（ローカルの today）を用いる部分があるため、本番運用時はジョブスケジューラや権限設定を適切に行うこと。

References
- 実装方針や設計コメントは各モジュールの docstring に詳述しています。必要に応じて各ファイルのドキュメントを参照してください。