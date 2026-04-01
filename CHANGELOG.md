Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

ルールの簡単な説明:  
- バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security 等のカテゴリで記載します。  
- 日付はリリース日を示します。

[Unreleased]
------------

- 今後の変更はここに記載します。

[0.1.0] - 2026-04-01
--------------------

Added
- 新規ライブラリ初回リリース。
- パッケージ公開:
  - パッケージルート: kabusys (src/kabusys/__init__.py)。__version__ = "0.1.0"。パッケージ外部に data, strategy, execution, monitoring を公開。
- 環境設定 / 自動 .env ロード:
  - kabusys.config: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装: export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。保護された OS 環境変数を上書きしない仕組みを実装。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定をプロパティ経由で取得。必須値未設定時は ValueError を送出する厳格な挙動。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを追加（許容値集合を定義）。
- データ処理（DuckDB ベース）:
  - kabusys.data.pipeline: ETLResult データクラスを公開。ETL 実行結果の構造化（フェッチ数・保存数・品質問題・エラー等）。
  - kabusys.data.etl: ETLResult の再エクスポートを追加。
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル）: 営業日判定、前後営業日取得、期間内営業日リスト取得、SQ 日判定などを提供。
    - calendar_update_job: J-Quants からカレンダー差分取得して冪等的に保存するバッチジョブを実装（バックフィル、健全性チェックあり）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末休場）を行う堅牢なロジックを設計。
    - テーブル存在チェック等のユーティリティを実装。
- 研究用モジュール（Research）:
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、ログ出力を含む設計。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic: スピアマンρ）、ランク変換、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等非依存で標準ライブラリ + DuckDB で完結。
  - 研究用ユーティリティとして zscore_normalize を data.stats から再利用している点を公開。
- AI（OpenAI）連携:
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols をソースにして、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価を行い ai_scores テーブルへ書き込む score_news を実装。
    - チャンク処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数上限・文字数トリム、レスポンス検証、±1.0 クリッピングを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時は部分スキップして処理継続（フェイルセーフ）。
    - JSON mode のレスポンスに前後テキストが混ざるケースへ対処する復元ロジック（最外の {} を抽出してパース）。
    - テスト容易性のため _call_openai_api を patch 置換できるように設計。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API リトライ（指数バックオフ）、API エラー種別ごとの扱い、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を設計。
    - OpenAI 呼び出しは news_nlp と独立した実装とし、モジュール結合を避ける設計。
- DuckDB 互換性対策:
  - executemany に空リストを渡すと失敗する（DuckDB 0.10 の制約）ため、空判定を行ってから executemany を呼ぶ安全策を導入。
- ロギング:
  - 各モジュールで情報・警告・デバッグログを充実させ、失敗時の診断情報を出力。

Changed
- 設計方針の明示:
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を内部ロジックで直接参照しない方針を各 AI / 研究モジュールに適用（target_date を明示的引数に持つ）。
- 環境変数ロード順序を明確化: OS 環境 > .env.local > .env。`.env.local` は `.env` 上書き（override=True）。

Fixed
- API レスポンスパース堅牢化:
  - JSON モードで余計な前後テキストが混入するケース、またはスコアが整数で返されるケース（code を整数で返す等）への耐性を追加。
- OpenAI API エラー処理:
  - openai SDK の APIError に status_code 属性がある/ない両方に対応。5xx 系かどうかの判定を安全に行うよう改善。
- .env ファイル読み込みのファイルエンコーディング／IO エラーでの警告出力を追加。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- 環境変数の取り扱いで OS 環境変数を保護する仕組み（protected set）を導入。自動ロードを明示的に無効化できる環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加し、テスト時に機密情報の読み込みを抑制可能。

Notes / 実装上の重要ポイント
- フェイルセーフ設計: LLM 呼び出し失敗時に例外を上位に伝播させず安全側のデフォルトを使用して処理を継続する箇所が多く含まれる（AI スコアリング周り等）。これにより ETL・分析処理実行中の全停止を防ぐことを意図。
- 冪等性: market_regime / ai_scores / calendar 等への DB 書き込みは既存行を削除してから再挿入するなど冪等性を考慮した実装。
- テスト性: _call_openai_api の差し替え、api_key を引数で注入可能にする等、ユニットテスト・モックの容易性を考慮。
- DuckDB の日付型や未作成テーブルへの対応を用意（型変換ユーティリティやテーブル存在チェック）。

将来の改善候補（今後のリリースで検討）
- ai モジュールにおけるバッチサイズやトークン管理の自動調整（トークン上限に応じた分割）。
- OpenAI 応答のスキーマ検証を厳格化するための JSON schema の導入。
- pipeline モジュールの ETL 実行ワークフロー（ジョブ管理・再試行戦略）を高レベル API として公開。
- テスト用の DuckDB in-memory 初期化ユーティリティの追加。

Contact
- 問い合わせや不明点はリポジトリのイシューへお願いします。