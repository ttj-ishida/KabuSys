# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース: 0.1.0 — 2026-03-31

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買 / データ基盤・リサーチ・AI支援モジュールをまとめた最初の公開版。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを追加。バージョンは `0.1.0` に設定。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能:
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先度: OS 環境 > .env.local > .env。
    - OS 環境変数は保護（デフォルトで上書きされない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロード無効化可能（テスト向け）。
  - .env のパースは export 形式・クォート・エスケープ・インラインコメント等に対応。
  - 必須環境変数取得用 _require とバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
  - 代表的な必須キー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - データベースパスのデフォルト: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して、銘柄ごとにニュース全文（タイトル＋本文）を結合して OpenAI（gpt-4o-mini）でセンチメント評価。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する calc_news_window。
    - 1 銘柄あたり最大記事数・文字数でトリム（トークン肥大対策）。
    - バッチ処理（デフォルト 20 銘柄/コール）とエクスポネンシャルバックオフによるリトライ（429, ネットワーク, タイムアウト, 5xx）。
    - JSON Mode のレスポンス検証、部分失敗に配慮した ai_scores テーブルへの冪等置換（DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し部分を内部関数で切り出し、モック可能。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込み。
    - マクロニュースは特定キーワードでフィルタし、OpenAI により -1.0〜1.0 のスコアを取得。
    - API エラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - DuckDB を用いた冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI クライアント呼び出しはモジュール間で共有しない独立実装（結合低減・テスト容易性）。

- データ基盤 / ETL / カレンダー管理 (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理ロジックを実装。is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業日）でフォールバック。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants API から差分取得し冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索範囲・ループ防止、NULL 値検出時のログ出力など品質に配慮した実装。
  - pipeline / etl:
    - ETLResult dataclass を実装（取得件数、保存件数、品質問題、エラー一覧等を格納）。
    - ETLResult#to_dict によるシリアライズ、has_errors / has_quality_errors などのヘルパーを提供。
    - ETL の内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整）を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials を参照して PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB 上で SQL を駆使して効率的に計算。データ不足時は None を返す仕様。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 研究向けユーティリティ群を __all__ で公開（zscore_normalize は data.stats から）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- news_nlp と regime_detector 内で OpenAI レスポンスの JSON パース失敗や余計な前後テキスト混入に対する回復処理を追加（最外の `{}` を抽出してパースを試行する等）。これにより JSON Mode でも稀なノイズに対して耐性が向上。

### 既知の注意点 / 移行メモ (Notes)
- AI 機能（score_news / score_regime）は OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）が必須。未設定時は ValueError を送出する。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージを配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用することを推奨。
- DuckDB への executemany に空リストを渡すと問題になるバージョン（例: DuckDB 0.10）を考慮して、空チェックを行った上で実行している。
- 時刻・日付は原則 timezone-naive な date / datetime を使用し、ルックアヘッドバイアス防止のため global な現在時刻参照（date.today() / datetime.today()）を直接使用しない設計が多くの箇所で採用されている。
- jquants_client（kabusys.data.jquants_client）への依存があるため、実稼働で使用する場合は該当クライアント実装と認証トークンの準備が必要。

### テスト / 開発向け（実装上の配慮）
- OpenAI 呼び出しはモジュール内のプライベート関数に切り出してあり、unittest.mock.patch などで差し替えてユニットテストを行いやすい設計になっています。
- DB 書き込みは可能な限り冪等性（DELETE/INSERT、ON CONFLICT 等）を保つよう実装されています。

---

今後のリリースで予定している改良（例）
- strategy / execution / monitoring モジュールの具体的な取引ロジック・注文実行フローの実装とテスト。
- J-Quants クライアント周りの堅牢化・リトライ戦略の統一。
- リアルタイム監視・アラート（Slack 統合）の充実。
- ai モデル出力のキャリブレーション・評価用ユーティリティの追加。

(以上)