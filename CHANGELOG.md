CHANGELOG
=========
すべての著名された変更は Keep a Changelog の形式に従い、かつ意味のある互換性バージョニングを使用します。
https://keepachangelog.com/ja/1.0.0/

フォーマット
-----------
- 変更は新しいリリースが上に来るように記載しています。
- 日付は ISO 形式 (YYYY-MM-DD) です。

Unreleased
----------
（なし）

0.1.0 - 2026-04-01
------------------
Added
- パッケージ初回公開。
- 基本パッケージ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開対象モジュール: data, strategy, execution, monitoring（__all__ にて公開）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする自動ローダ実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env（デフォルト）→ .env.local（上書き）の優先順を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
  - .env の行パーサ実装: コメント、export プレフィックス、クォート／エスケープ対応、インラインコメント処理などに対応。
  - 環境変数取得ヘルパ（Settings クラス）を提供:
    - J-Quants、kabuステーション、Slack、DB パス（duckdb/sqlite）、監視設定（PID ファイル・閾値）、システム設定（KABUSYS_ENV/LOG_LEVEL）等をプロパティで取得。
    - 必須環境変数未設定時は ValueError を発生。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実施。
    - デフォルト値（例: KABUSYS_ENV=development、KABUSYS_API_BASE_URL 等）を設定。

- AI: ニュース NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出。
  - タイムウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（内部は UTC naive datetime を利用）。
  - チャンク処理: 最大 20 銘柄／コール、1 銘柄当たりの記事上限・文字数トリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
  - レスポンスのバリデーション: JSON パース、"results" フォーマット検証、コードの正規化、スコア数値化、±1.0 でクリップ。
  - エラー対策:
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
    - それ以外の失敗はそのチャンクをスキップして継続（フェイルセーフ）。
    - テスト向けに _call_openai_api を patch して差し替え可能。
  - DuckDB への書き込みは部分失敗に強い実装（影響あるコードのみ DELETE → INSERT）で、executemany の空リスト制約に対応。

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（'bull' / 'neutral' / 'bear'）。
  - 処理の主な特徴:
    - prices_daily からのルックアヘッド防止（target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini, JSON mode）で macro_sentiment を算出。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（例外を上げないフェイルセーフ）。
    - レジームはスコアをクリップして閾値判定し、market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装でモジュール結合を低く保つ。リトライ・バックオフ、5xx の扱いを実装。

- Data: マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー（祝日・半日取引・SQ日）の取得・保持・営業日判定ロジックを提供。
  - 関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB 登録データがある場合は DB 優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫した挙動。
  - 夜間バッチ job（calendar_update_job）を実装: J-Quants から差分取得、バックフィル、健全性チェック（将来日付の異常検出）を実施。
  - 最大探索日数等の安全ガード（_MAX_SEARCH_DAYS など）を導入。

- Data: ETL パイプライン (kabusys.data.pipeline / etl)
  - ETLResult データクラスを公開（etl.py で再エクスポート）。
  - ETL の設計方針・結果構造を定義:
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）を想定。
    - エラー／品質問題は収集して呼び出し元に渡す設計（Fail-Fast ではなく収集型）。
    - DuckDB のテーブル存在チェック／最大日付取得等のユーティリティを実装。
  - J-Quants クライアント経由の保存処理（save_*）と連携する想定。

- Research（kabusys.research）
  - ファクター計算および特徴量探索のユーティリティを提供。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（データ不足時は None / ログ出力）。
    - calc_volatility: 20 日 ATR（true range の NULL を正しく扱う）、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損なら PER は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、実行環境に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性検査あり。
    - calc_ic: ランク相関（Spearman）ベースの IC 計算。データ不足（<3）時は None。
    - rank: 同順位は平均ランクとする実装（丸めで ties の漏れを防止）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。
  - 全体の設計方針: DuckDB 接続を受け取り SQL と標準ライブラリのみで処理（pandas 等に依存しない）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 環境変数取り扱い:
  - OS 環境変数を上書きしないデフォルト動作（.env 読み込みの override 制御と protected set による保護）。
  - 必須シークレット（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に明示的にエラーを出す（早期検出）。

Notes / 使い方・移行メモ
- OpenAI API を利用する機能（score_news, score_regime）は実行前に OPENAI_API_KEY を環境変数または api_key 引数で設定する必要があります。未設定時は ValueError を送出します。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後に CWD に依存しない挙動を期待できます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQL 操作は冪等性（DELETE→INSERT 等）を重視しており、部分失敗時に既存データを不必要に消さないよう配慮しています。
- 時刻・日付の扱い:
  - 主要な処理（ニュースウィンドウ、ETL、レジーム判定等）は内部で date.today() や datetime.today() に依存しない設計（呼び出し元が target_date を渡す）となっており、ルックアヘッドバイアスを防止します。
- テストしやすさ:
  - OpenAI 呼出し用の内部関数はテスト中に patch できるように設計されています（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

問い合わせ
--------
不明点・追加の修正履歴記載の希望があれば、どのモジュールについての変更履歴を詳述したいかを教えてください。