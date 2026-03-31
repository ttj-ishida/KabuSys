CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に従い、Semantic Versioning を使用します。
<!-- 参考: https://keepachangelog.com/ja/1.0.0/ -->

[Unreleased]

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パッケージの公開 API:
  - top-level: data, strategy, execution, monitoring を __all__ でエクスポート。
  - ai: score_news を公開（kabusys.ai）。
  - research: calc_momentum / calc_value / calc_volatility / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を公開。
  - data.etl: ETLResult を再エクスポート。
- 環境設定管理モジュール (kabusys.config):
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - インラインコメント判定のルールを実装（クォートなしの '#' は直前が空白/タブ の場合のみコメント扱い）。
  - Settings クラスを提供（J-Quants・kabu API・Slack・DBパス・環境/ログレベル判定などのプロパティを用意）。
  - 環境変数の必須チェック時には明示的な ValueError を発生させる _require 実装。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値の集合を定義）。
- AI 関連（kabusys.ai）:
  - ニュースNLP スコアリング (news_nlp.score_news):
    - raw_news / news_symbols から記事を銘柄別に集約して OpenAI (gpt-4o-mini) にバッチ送信し、ai_scores に書き込む。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30）を計算するユーティリティ calc_news_window を提供（UTC naive datetime を返す）。
    - バッチサイズ、記事トリム、文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx）などの堅牢な実装。
    - レスポンスバリデーション機構（JSON の抽出、results 配列と各要素の code/score 検証、スコアの ±1.0 クリップ）。
    - API 呼び出し部分は内部関数 _call_openai_api として分離しており、テスト時に差し替え可能。
    - 処理はフェイルセーフ設計（API 失敗時は該当チャンクをスキップ、全処理継続）。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し market_regime に書き込む。
    - マクロキーワードによる raw_news のフィルタリング、LLM 呼び出し、スコア合成、閾値判定（bull/neutral/bear）を実装。
    - OpenAI 呼び出しのリトライ・バックオフ、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - DB 書き込みはトランザクションで冪等に（BEGIN / DELETE / INSERT / COMMIT）、失敗時に ROLLBACK を試行。
- Data モジュール（kabusys.data）:
  - カレンダー管理 (calendar_management):
    - market_calendar を元に営業日判定とヘルパーを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダーデータがない場合は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新するジョブ（バックフィル / 健全性チェックを含む）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー要約などを格納）。
    - 差分更新・バックフィル・品質チェックを想定した設計で、J-Quants クライアント経由の保存処理を呼び出す仕組みを前提に実装（詳細ロジック・保存は jquants_client へ委譲）。
- Research モジュール（kabusys.research）:
  - ファクター計算 (factor_research):
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR, 相対ATR）、流動性（20日平均売買代金/出来高比率）、バリュー（PER/ROE）を DuckDB の SQL と Python の組合せで計算する関数を提供。
    - データ不足時の挙動（None を返す）や、スキャン範囲バッファの説明を含む。
  - 特徴量探索 (feature_exploration):
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）、ホライズンの妥当性チェック（1..252）。
    - IC（calc_ic）：Spearman のランク相関の実装（最小サンプル数チェック）。
    - factor_summary / rank：統計サマリー（count/mean/std/min/max/median）とランク計算ユーティリティ。
- 実装方針・品質:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をスコア計算内部で安易に参照しない設計を徹底。
  - 外部ライブラリ（pandas 等）に依存せず、標準ライブラリ + duckdb で実装することを意図。
  - DuckDB 固有の制約（executemany の空リスト不可など）に配慮したコード。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照する方式。未設定時は明示的に例外を出すことで誤用を低減。

Notes / 開発者向け補足
- テスト容易性のため、OpenAI への実際の HTTP 呼び出しは内部関数（各モジュールの _call_openai_api）を unittest.mock.patch で差し替え可能にしている。
- DB 書き込み時は可能な限り冪等性を保つ（DELETE→INSERT、トランザクション）ようにしており、部分失敗時に既存データを不用意に消去しない設計になっている。
- news_nlp と regime_detector は OpenAI の JSON Mode を前提としたレスポンス処理を行い、レスポンスに余計な前後テキストが混入した場合でも中央の JSON 部分を抽出して復元するロジックを持つ。

リンク
- ソース: リポジトリ内の各モジュール（src/kabusys/...）を参照してください。