CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリースポリシー: ここに記載されるバージョンは semantic versioning（MAJOR.MINOR.PATCH）に従います。

Unreleased
----------

（現在未リリースの変更はここに記載します。）

0.1.0 - 2026-04-04
------------------

初回公開リリース。

Added
- パッケージ基盤
  - パッケージのバージョンを定義: kabusys.__version__ = "0.1.0"。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - ファイル読み込み失敗時は警告を出力して続行。
  - .env パーサ実装（export プレフィックス対応、クォート内のエスケープ、コメント処理などを考慮）。
  - 環境変数保護（protected）機能: OS 環境変数を上書きしないよう扱う。
  - Settings クラスを提供し、アプリケーションで参照する設定プロパティを定義：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを Path オブジェクトで返す）
    - PID / KILL フラグ関連設定（監視用）
    - CPU/MEM/DISK 閾値（デフォルト値）
    - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev のショートハンドプロパティ
  - 必須変数未設定時は明確な ValueError を送出する挙動。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメント（-1..1）を取得する実装。
    - 時間ウィンドウ定義（JST ベース）と calc_news_window ユーティリティ。
    - バッチ処理: 最大 _BATCH_SIZE（デフォルト20）銘柄/コール、1銘柄あたりの最大記事数と最大文字数でトリムする仕組み。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーションとパース（JSON モードでも余分なテキストを含む場合に対応）。
    - スコアは ±1.0 にクリップ。
    - DB への書き込みは冪等に行う（取得済みコードのみ DELETE→INSERT、部分失敗時に他コードの既存スコアを保護）。
    - テスト容易性のため、OpenAI 呼び出しを差し替えられるよう _call_openai_api 関数を分離（unittest.mock.patch に対応）。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを防止）。
    - マクロニュース抽出（title にマクロキーワードを含む記事を最大 _MAX_MACRO_ARTICLES 件抽出）。
    - OpenAI（gpt-4o-mini）呼び出しとスコア合成ロジックを備え、最終的に market_regime テーブルへ冪等書き込み。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ運用。
    - レートリミットや接続エラーに対するリトライ実装。
    - news_nlp モジュールとは OpenAI 呼び出しを共有せず別実装にすることでモジュール結合を避ける設計。

- データ処理 / ETL / カレンダー (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェックを行う設計方針に基づくユーティリティを実装。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得などのユーティリティを含む。
  - ETL インターフェースを再エクスポート (kabusys.data.etl)。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が存在しない場合は曜日ベース（土日を非営業日とする）でフォールバック。
    - calendar_update_job による J-Quants からの差分取得・保存（バックフィル・健全性チェックを含む）。
    - DB 登録値優先・未登録日は曜日フォールバックにより next/prev/get_trading_day と一貫した挙動。
  - jquants_client との連携（fetch / save を想定）。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0/欠損時は None）。
    - すべて DuckDB の prices_daily / raw_financials のみを参照し、外部へのアクセスを行わない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算し、データ不足時は None を返す。
    - rank: 同順位は平均ランクになるように処理（浮動小数点の丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 研究向け関数は pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。

Changed
- 初版リリースのため「変更」はなし（初回導入機能のまとめ）。

Fixed
- 初版リリースのため「修正」はなし。

Security
- OpenAI API キーは明示的に要求される（score_news, score_regime は api_key 引数または環境変数 OPENAI_API_KEY が必要）。未設定時は ValueError を投げて明示的に失敗。
- J-Quants / kabu API の機密トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 経由で必須となる。
- .env の読み込みはデフォルトで OS 環境変数を上書きしない設計（保護されたキーセットを利用）。

Notes / その他の設計上の注意
- ルックアヘッドバイアス防止: 各モジュール（news_nlp, regime_detector 等）は datetime.today()/date.today() を直接参照せず、外部から与えられる target_date を基準に処理するように設計されています。
- フェイルセーフ設計: 外部 API（OpenAI/J-Quants）呼び出し失敗時は例外を投げずに安全なデフォルト（例: 0.0 やスキップ）を用いて処理を継続する箇所が多く、運用時の回復性を考慮しています。ただし API キー未設定は例外となります。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の使用）しており、部分失敗時に既存データを不意に消さない設計です。
- テストのための差し替えポイント（_call_openai_api 等）が用意されています。

今後の予定（例）
- strategy / execution / monitoring の具体実装拡張（現時点ではパッケージ構成のみ）。
- ai モデル周りのパラメータチューニングや新たなプロンプト設計の導入。
- ETL の品質チェック（quality モジュール）との統合強化と監査ログの拡充。

--- 

以上。必要であれば、各関数・クラスの変更履歴（より細かいリリースノート）を関数単位で生成します。どの粒度がよいか教えてください。