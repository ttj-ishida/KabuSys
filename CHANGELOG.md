Keep a Changelog
=================

すべての重要な変更をここに記録します。これは人間が読める形式で、変更履歴は意味のあるリリース単位で整理します。

注: この CHANGELOG はソースコードの内容から推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-29
------------------

初回リリース。主にデータパイプライン、カレンダー管理、リサーチ用ファクター計算、ニュースNLP / レジーム判定などのコア機能を実装。

Added
-----

- 全体
  - パッケージ初期バージョンを定義: kabusys.__version__ = "0.1.0"。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に含める（strategy 等は外部インターフェースの一部として確保）。

- 環境設定（src/kabusys/config.py）
  - .env/.env.local ファイルまたは環境変数から設定を自動読み込みする仕組みを追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサーを堅牢化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の挙動制御等を実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数の保護（protected set）をサポートし、.env.local は既存環境変数を上書き可能にする制御を実装。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境（development/paper_trading/live）/ログレベルなどの取得とバリデーションを提供（必須変数未設定時は ValueError を送出）。
  - デフォルトの DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）や kabu API のデフォルト base URL を設定。

- AI モジュール（src/kabusys/ai）
  - news_nlp モジュールを追加（score_news を公開）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースをバッチで OpenAI（gpt-4o-mini）へ送信し、センチメントを ai_scores テーブルへ書き込む。
    - チャンクサイズ、トークン肥大化対策（1銘柄あたり最大記事数・最大文字数）、JSON Mode を用いたレスポンス処理、レスポンスの厳密なバリデーション実装。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。非リトライ例外はスキップして継続（フェイルセーフ）。
    - テスト容易性: _call_openai_api を patch してモック可能に設計。
    - DuckDB の executemany の制約（空リスト不可）に合わせた安全な DELETE/INSERT ロジックを実装（部分失敗時に既存スコアを保護）。
  - regime_detector モジュールを追加（score_regime を公開）。
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出用のキーワードリストを実装し、raw_news からタイトル抽出を行う。
    - OpenAI 呼び出しは独立実装とし、API エラー時には macro_sentiment=0.0 にフォールバック（例外を上げず処理継続）。リトライ/バックオフの制御を実装。
    - DB への書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。
    - ルックアヘッドバイアス防止の設計（datetime.today()/date.today() を参照しない、prices_daily クエリは date < target_date を使用）。

- データモジュール（src/kabusys/data）
  - calendar_management モジュールを追加。
    - JPX マーケットカレンダー（祝日・半日取引・SQ日）管理機能を提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録値があればそれを優先する一貫した挙動。
    - 夜間更新ジョブ calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを含む）。
  - pipeline モジュール（ETL）
    - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返す。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - DuckDB 上のテーブル存在チェック、最大日付取得等のユーティリティを実装。
  - etl.py で ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - factor_research モジュールを追加。
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）等の計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損・データ不足に対する安全な戻り値（None）やログ出力を実装。
    - すべての関数は prices_daily / raw_financials のみ参照し、外部 API 呼び出しを行わない設計。
  - feature_exploration モジュールを追加。
    - 将来リターン calc_forward_returns（任意ホライズン対応、入力検証あり）を実装。
    - スピアマンランク相関（IC）を計算する calc_ic を実装（None / 少数レコード時の扱いに注意）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

- テスト・開発支援
  - OpenAI 呼び出し箇所で内部 _call_openai_api 関数を分離し、ユニットテスト時に patch で差し替え可能に設計（news_nlp と regime_detector 両者で独立実装）。

Changed
-------

- （初回リリースのため該当なし）

Fixed
-----

- （初回リリースのため該当なし）

Security
--------

- 環境変数取得で必須項目が未設定の場合は ValueError を投げ、明示的に通知することで秘匿情報の未設定を早期に検出できるように設計。
- OpenAI API 呼び出しのリトライ挙動、API キーの注入（引数または環境変数）による柔軟な運用を考慮。

Notes / Implementation details
------------------------------

- DuckDB をデータ層に採用。executemany の空リスト制約（DuckDB 0.10 系）への対応や date 型の取り扱い（UTC naive / date オブジェクト）など、実運用での互換性を意識した実装が行われています。
- ニュース系 AI ワークフローは「JSON Mode」を利用する想定で厳格なレスポンスバリデーションを行い、LLM の不正な出力や余計なテキスト混入に対しても回復可能になるよう実装されています。
- ルックアヘッドバイアス防止のため、全モジュールで date / datetime の取り扱いに注意し、target_date を明示して計算する設計になっています。
- env 自動ロードの起点はパッケージファイル位置からの親ディレクトリ探索で決定され、CWD に依存しないためパッケージ配布後も安定して動作します。

Acknowledgements
----------------

- J-Quants / JPX / kabuステーション 等の外部データ提供元を前提とした設計になっています。
- OpenAI（gpt-4o-mini）を利用する想定の実装が含まれます。API 利用時は適切なアクセス管理を行ってください。