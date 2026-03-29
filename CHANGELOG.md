CHANGELOG
=========

すべての注目すべき変更履歴はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース。
  - src/kabusys パッケージを公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェースで data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py: .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - OS 環境変数を保護する protected バインド（.env.local は既存の OS 環境変数を上書きしない）を実装。
  - Settings クラスを提供し、必要な設定（J-Quants、kabuステーション、Slack、DBパス、実行環境、ログレベルなど）をプロパティで取得できるようにした。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）が含まれる。
    - duckdb/sqlite のデフォルトパスを提供。

- ニュースNLP / AI
  - src/kabusys/ai/news_nlp.py: ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む機能を追加。
    - JST の時間窓（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事収集ロジック（UTC naive datetime を返す calc_news_window を含む）。
    - 銘柄ごとに最新記事を集約し、1チャンク最大 20 銘柄でバッチ送信。1銘柄あたり記事数・文字数制限（トリム）あり。
    - OpenAI 呼び出し時の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - JSON レスポンスのバリデーションと復元処理（前後余分なテキストが混ざる場合に外側の {} を抽出）。
    - スコアは ±1.0 にクリップ。部分失敗時にも既存スコアを保護するため、書き込みは取得済みコードのみ DELETE→INSERT の冪等更新。
    - テスト用に _call_openai_api をパッチ差し替え可能（unittest.mock.patch を想定）。

  - src/kabusys/ai/regime_detector.py: 市場レジーム判定（bull/neutral/bear）を追加。
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成。
    - マクロニュース抽出はキーワードリストに基づき raw_news からタイトルを取得。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得。API失敗時はフェイルセーフで macro_sentiment=0.0 を採用。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出し用の内部関数は news_nlp と分離しモジュール結合を避ける設計。

- データ管理（Data）
  - src/kabusys/data/calendar_management.py: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day をサポート。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB登録値優先の一貫した挙動。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得→保存（バックフィル・健全性チェック含む）を実装。
  - src/kabusys/data/pipeline.py: ETL パイプライン用ユーティリティと ETLResult データクラスを実装。
    - 差分取得、保存（idempotent）、品質チェック呼び出しのための共通ロジックを提供。
    - ETLResult に品質問題とエラーの集約、has_errors / has_quality_errors / to_dict を追加。
  - src/kabusys/data/etl.py: pipeline.ETLResult の再エクスポートを追加。

- 研究（Research）
  - src/kabusys/research/*: ファクター計算および特徴量探索ツールを提供。
    - factor_research.py: モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、バリュー（PER, ROE）等の計算関数を追加。DuckDB SQL を利用し prices_daily / raw_financials を参照。
    - feature_exploration.py:
      - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）。
      - IC（Spearman の ρ）計算 calc_ic（欠損レコード除外、最小サンプル数チェック）。
      - ランク変換ユーティリティ rank（同順位は平均ランク）。
      - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 研究用 API は外部サービス（取引・発注）へはアクセスしない設計。

Changed
- 設計・実装面の注記（実装から推測）
  - ルックアヘッドバイアス防止のため、各 AI / ETL / Research モジュールは datetime.today() / date.today() を直接参照しないように設計されている（target_date を明示的に受け取る）。
  - DuckDB を主要な解析・永続化層として利用。書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT など）している。

Fixed
- N/A（初期リリースのため修正履歴はなし）

Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY から取得する挙動を採用。エラー時は ValueError を発生させ明示的に通知。
- .env ローダは OS 環境変数を保護する仕組み（protected set）を備え、意図しない上書きを防止。

Performance / Reliability (Internal)
- AI 呼び出しでのリトライ（指数バックオフ）、チャンク処理、最大バッチサイズの制御により可用性とトークン利用効率を向上。
- ETL / calendar 更新でのバックフィル・健全性チェックによりデータ品質維持を図る。

Notes / 既知の設計方針（実装からの推測）
- テスト容易性のため、OpenAI 呼び出しを行う内部関数はモジュールローカルで定義され、patch による差し替えが想定されている。
- DuckDB の executemany が空リストを受け付けないバージョン互換性を考慮して、空パラメータ時の条件分岐を実装している。
- タイムゾーンは内部で UTC naive datetime を使用し、JST 時間窓は明示的に UTC に変換して比較している。

Acknowledgments
- この CHANGELOG は、提供されたコードの内容に基づいて作成しました。実際の変更履歴やリリースノートはリポジトリのコミット履歴や作者の公開情報を参照してください。