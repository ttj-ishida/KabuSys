# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※この CHANGELOG はコードベースの内容から推測して作成した初期リリースノートです。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-01

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ:
    - __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring

- 環境・設定管理（kabusys.config）
  - .env / .env.local または OS 環境変数から設定を自動読み込みするユーティリティを実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env の行パーサはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート有無による扱い）に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境判定 等）。
  - 設定値のバリデーション（env 値の許容集合、ログレベルの許容値）を実装。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄ごとのセンチメント（ai_score）を計算し ai_scores テーブルへ書き込む。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と照合）。
    - バッチ処理: 最大 20 銘柄／API コール、1 銘柄あたり記事数・文字数の上限トリム。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）は指数バックオフでリトライ。その他エラーは安全にスキップ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code と score、既知コードフィルタ、スコア数値チェック）。スコアは ±1 にクリップ。
    - DB 書き込みは部分失敗に備え、スコア取得済みコードのみ DELETE → INSERT（冪等性・既存データ保護）。
    - ルックアヘッドバイアス防止のため日付参照は引数 target_date に依存（date.today() を直接参照しない）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードベース（日本・米国等のマクロ語句リスト）で最大 20 件を抽出。
    - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment=0.0 で継続するフェイルセーフ動作。
    - API 呼び出しのリトライと 5xx ハンドリング、レスポンス JSON パースエラーハンドリングを実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を用いた冪等処理とロールバック対策を実装。
    - ルックアヘッドバイアス防止: prices_daily クエリは target_date 未満のデータのみを使用。

- 研究用モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200（200 日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率などを計算。NULL 散在時の取扱いを明確に実装。
    - calc_value: raw_financials から直近の財務データを取得し PER・ROE を計算（EPS=0/欠損は None）。
    - すべて DuckDB の prices_daily/raw_financials のみを参照し、本番発注 API へはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは入力検証あり。
    - calc_ic: スピアマンランク相関（IC）を計算。無効レコード・少数データ時の振る舞いを定義（3 件未満で None）。
    - rank: 同順位は平均ランクで返すランク関数（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
  - kabusys.research.__init__ で主要関数をエクスポート（zscore_normalize は data.stats から再利用）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX 市場カレンダー管理と営業日判定ユーティリティ。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェック実装。
  - pipeline & ETLResult
    - ETLResult dataclass を公開（etl モジュール経由で再エクスポート）。
    - ETL パイプライン設計方針や差分更新・品質チェック・バックフィル方針に基づく構成（詳細は pipeline モジュールに実装）。
    - DuckDB を主要なデータストアとして使用するための各種ユーティリティ（テーブル存在確認、最大日付取得など）。

- その他ユーティリティ
  - data.etl が pipeline.ETLResult を再エクスポート。
  - 複数箇所で DuckDB を用いた SQL ベースの計算・集約を実装。
  - ロギング（logger）を各モジュールで利用し、情報・警告・例外ロギングを適切に配置。

Notes / Important
- OpenAI API キーは各 AI 関数（score_news / score_regime）で api_key 引数から渡すか、環境変数 OPENAI_API_KEY を使用する必要がある。未設定時は ValueError を送出する。
- OpenAI 呼び出し失敗時はフェイルセーフとして 0.0 を使用する等の継続指向の設計を採用している（例外を全体に波及させない）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 期待等）されており、部分失敗時に既存データを不必要に消さない工夫がある。
- ルックアヘッドバイアスを避ける設計方針が徹底されている（target_date ベースでの明示的ウィンドウ指定、date.today() を直接参照しない等）。
- .env パーサは複雑なケース（引用・エスケープ・コメント）に対応しているが、極端なフォーマットは未検証のため .env.example を参考にすること。

Breaking Changes
- 初期リリースのため該当なし。

Deprecated
- 該当なし。

Security
- 機密情報（API トークン等）は環境変数で管理すること。.env をコミットしないこと。
- OpenAI のレスポンスを厳密にパースしているが、不正データや想定外の型が来る可能性を考慮してフォールバック処理が入っている。

--- 

（この CHANGELOG はソースコードの構造とドキュメント文字列から推測して作成したものであり、実際のリリースノートは運用上の要件に合わせて調整してください。）