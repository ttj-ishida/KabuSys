Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

履歴
----

### Unreleased
- （なし）

### [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを実装。

Added
- パッケージ初期化
  - kabusys パッケージと __version__ = "0.1.0" を追加。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは次をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント扱い（直前がスペース/タブの場合のみ）
  - 読み込み方針:
    - 優先順位: OS 環境変数 > .env.local > .env
    - .env.local は override=True（既存 OS 環境変数は保護）
  - Settings クラスを提供し、アプリケーション向け設定アクセスをプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（展開済み Path を返す）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news/news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive に変換）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄 / チャンク、1銘柄あたり最大 _MAX_ARTICLES_PER_STOCK=10 記事 / _MAX_CHARS_PER_STOCK=3000 文字にトリム。
    - 再試行（バックオフ）戦略: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ（初回待機 1.0s、最大リトライ _MAX_RETRIES）。
    - レスポンス検証:
      - JSON パース（前後余分テキストが混ざる場合でも最外側の {} を抽出して復元を試行）
      - "results" リストの存在確認、各要素に code/score があること、score を数値化し ±1.0 にクリップ
      - 未知の code は無視（安全措置）
    - データベース書込:
      - 成功スコアのみを対象に DELETE (date, code) → INSERT（部分失敗時に既存スコアを保護）
      - DuckDB の executemany の仕様を考慮し、空リストは渡さないガード
    - テスト容易性: API 呼び出しラッパー _call_openai_api を unittest.mock.patch で差し替え可能
    - 公開 API: score_news(conn, target_date, api_key=None)
      - OpenAI API キー注入可能（引数または環境変数 OPENAI_API_KEY）
      - 取得した書き込み銘柄数を返す

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM センチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（_MACRO_KEYWORDS）し、最大 _MAX_MACRO_ARTICLES 件を LLM へ送信して macro_sentiment を取得。
    - レジームスコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 閾値: _BULL_THRESHOLD / _BEAR_THRESHOLD に基づきラベル決定
    - DB 書込は冪等（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出しとリトライ/エラー扱いは news_nlp と類似の堅牢実装
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録がない場合は曜日（平日）ベースでフォールバックする設計（まばらな DB 登録でも一貫した動作を提供）
    - 夜間バッチ calendar_update_job(conn, lookahead_days=90) を実装（J-Quants から差分取得 → 保存）
    - 安全策: バックフィル（日数固定）、健全性チェック（将来日付が不自然に大きい場合はスキップ）、最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止
    - jquants_client との統合ポイントを用意

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult dataclass を公開（取得件数・保存件数・品質チェック結果・エラーリスト等を含む）
    - 差分取得、バックフィル、品質チェックを行う設計方針を実装（jquants_client / quality モジュール経由）
    - DuckDB 操作のユーティリティ（テーブル存在チェック、最大日付取得など）を実装

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER/ROE）等を SQL ベースで計算
    - データ不足時は None を返す仕様
    - 関数は DuckDB 接続を受け取り副作用なしで結果を返す
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - 統計サマリー factor_summary（count/mean/std/min/max/median、None は除外）
    - pandas 等に依存せず標準ライブラリ + DuckDB SQL のみで実装

Changed
- —（初版のため該当なし）

Fixed
- DuckDB の実装制約に対応:
  - executemany に空リストを渡すと失敗する問題を考慮して空チェックを導入（ai_scores の書込み等）
- LLM 応答のパース性向上:
  - JSON mode でも前後に余分なテキストが混ざるケースを想定し、最外側の {} を抽出して復元を試みる処理を追加（news_nlp）
- 型・エラーハンドリングの堅牢化:
  - news_nlp で LLM が整数で code を返すケースに対し str 正規化で照合
  - API エラー種類に応じた再試行/フェイルセーフ動作（非5xx は再試行しない等）

Security
- —（初版のため該当なし）

Notes / 設計上の注意
- ルックアヘッドバイアス防止:
  - すべてのスコア/ファクター/レジーム計算は target_date を明示的に受け取り、datetime.today()/date.today() に依存しない設計。
- OpenAI API キー:
  - score_news / score_regime は引数で api_key を受け取れる。引数が None の場合は環境変数 OPENAI_API_KEY を参照。
  - API 失敗時は例外を上位に伝えない（基本的にフォールバックやスキップ）設計で、機能の安全性を優先。
- テストしやすさ:
  - _call_openai_api のパッチ置換により、外部 API を呼ばずにユニットテスト可能。
- 外部依存:
  - DuckDB を主要なローカル DB として利用。
  - OpenAI（gpt-4o-mini）を NLP に利用（JSON mode）。
  - jquants_client / quality モジュールと連携する設計（これらは別モジュール実装を想定）。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（バックテスト・発注ロジック・監視アラート）
- ai モデル・プロンプト改善、レトロスペクティブ評価（バックテストとの結合）
- ETL の並列化・性能改善、品質チェックの強化

リンク
- バージョン: 0.1.0

（この CHANGELOG はソースコード構成とドキュメント文字列から推測して作成しています。実際のリリースノートはリリース方針に合わせて調整してください。）