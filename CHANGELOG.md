# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース文脈: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。  
- バージョン番号はパッケージ定義 (kabusys.__version__ == 0.1.0) に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初回リリース。日本株のデータ取得・前処理、リサーチ用ファクター計算、ニュース NLP / 市場レジーム判定、カレンダー管理、ETL パイプラインなど研究・データ基盤と AI スコアリングのコア機能を提供。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージ名: KabuSys（kabusys）。バージョン 0.1.0 を定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索するため CWD に依存しない。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォート無い場合の # 扱い）に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / ログ設定などのプロパティを環境変数から取得。未設定の必須値取得時は例外を投げる。
  - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の妥当性チェックを実装。

- ニュース NLP（AI） (kabusys.ai.news_nlp)
  - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコア（-1.0～1.0）を算出。
  - ニュース収集ウィンドウを JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST、内部では UTC naive datetime を使用）。
  - 1銘柄あたり最大記事数および最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - バッチ処理（最大 20 銘柄/コール）、JSON Mode を利用した応答バリデーション、レスポンスの堅牢なパース（前後の余計なテキストの切り出し等）。
  - リトライ方針: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフで再試行。その他はスキップして継続（フェイルセーフ）。
  - 成果は ai_scores テーブルへ冪等に書き込み（対象コードのみ DELETE → INSERT）し、部分失敗時に他コードのスコアを保護。
  - テスト容易性のため _call_openai_api を patch 可能に設計。

- 市場レジーム判定（AI + テクニカル融合） (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み。
  - MA200 乖離は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。データ不足時は中立（1.0）を使用。
  - マクロニュースはタイトルでキーワードフィルタ（多言語キーワードを含む）し、LLM に JSON 出力を要求して macro_sentiment を取得。API エラー時は macro_sentiment=0.0 にフォールバック。
  - スコア合成後、regime_label を bull/neutral/bear に分類し、冪等的に DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
  - OpenAI 呼び出しは独立実装で、モジュール結合を避ける設計。

- データプラットフォーム / カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルを基に営業日判定と補助関数を提供:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - DB にカレンダーデータがない日については曜日（平日/土日）を使ったフォールバックを実装。DB 登録がある場合は DB 値を優先。
  - カレンダー夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。

- ETL パイプライン（データ取り込み） (kabusys.data.pipeline, kabusys.data.etl)
  - ETL の結果を表す ETLResult データクラスを提供（取得数・保存数・品質問題・エラー等を集約）。
  - 差分更新・保存（jquants_client の save_* を利用して冪等保存）・品質チェックの骨組みを実装。
  - デフォルトのバックフィル・カレンダー先読み・品質チェック方針を定義。
  - kabusys.data.etl は ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（平均）、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の直近財務を用いて PER / ROE を算出（EPS 無しや 0 の場合は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、DB 内で SQL を利用して効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンをまとめて取得する SQL 実装。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクとして処理（丸めで ties 対応）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出（None 値は除外）。
  - すべて外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- パッケージ公開 API
  - 複数のサブパッケージ/関数を __all__ / __init__ で公開（例: kabusys.ai.score_news, kabusys.research.* など）。

### 変更 (Changed)
- （初回リリースのため特になし）

### 修正 (Fixed)
- （初回リリースのため特になし）

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で注入する設計。コード内で平文固定は行わない前提。
- .env の自動読み込みで OS 環境変数を保護するため protected 機構を導入（既存 OS 環境変数は上書きされない）。

### 既知の制約・注意点 (Notes)
- ニュース / レジーム判定の LLM 呼び出しは外部 API に依存するため、API 制限・料金・レスポンス仕様変更に注意。フェイルセーフ（0.0 やスキップ）を多用しているが、運用時は監視が必要。
- DuckDB のバージョン互換性（executemany の空リスト制約等）に配慮した実装を行っている。
- strategy / execution / monitoring に関連する実装はパッケージの __all__ に名前があるが、このリリースではコードスニペット内に具体的実装がないため、将来的に追加予定。
- 日付・時間の扱いはルックアヘッドバイアス防止のため date / UTC naive datetime を厳格に扱う方針。

---

参考: 上記の CHANGELOG は与えられたソースコードの記述・ドキュメント文字列から推測して作成しています。実際のリポジトリ履歴（コミットメッセージ等）がある場合は、それに基づいて変更履歴を調整してください。