# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-02

初回リリース。日本株自動売買システム "KabuSys" の基本機能をまとめて公開します。  
主にデータ取得/整備、研究用ファクター計算、ニュース NLP と市場レジーム判定、環境設定周りのユーティリティを含みます。

### 追加
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ を "0.1.0" として公開。
  - パッケージ公開モジュール: data, research, ai, execution, monitoring, strategy 等の名前空間構成（__all__ 設定）。

- 環境設定 / .env 読み込み (kabusys.config)
  - .env と .env.local をプロジェクトルート（.git または pyproject.toml を検出）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 環境値取得ラッパ Settings を提供（J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 実行環境などのプロパティを定義）。
  - バリデーション: KABUSYS_ENV / LOG_LEVEL の許容値チェック。必須値未設定時は ValueError を送出する _require。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（1銘柄あたり記事数上限・文字数上限）、結果バリデーション、±1.0 クリップ、部分的な DB 書き換え（DELETE → INSERT）を実装。
    - リトライ/バックオフ: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - calc_news_window を公開（JST の前日 15:00 〜 当日 08:30 に相当する UTC ウィンドウを返す）。これはルックアヘッドバイアス防止のため date ベースで計算。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM）センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を算出。
    - OpenAI によるマクロセンチメント取得は記事が存在する場合のみ呼び出し。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - DuckDB の prices_daily / raw_news / market_regime を参照し、結果は冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出し周りにリトライ・指定モデル（gpt-4o-mini）・JSON 応答パースなどを実装。

- 研究・解析機能（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio 等の計算（NULL伝播やカウント制御を考慮）。
    - calc_value: raw_financials を用いた PER（EPS が 0/欠損時は None）および ROE の計算。
    - 全関数は DuckDB 上の SQL（prices_daily / raw_financials）で完結。外部売買 API へのアクセスは行わない設計。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの妥当性チェックあり。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク化ユーティリティ（丸めによる ties 漏れ対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - market_calendar が部分的または未取得でも曜日ベースのフォールバックを提供し、一貫した振る舞いを保証。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを実装）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL の取得/保存件数、品質問題、エラーなどを格納）。to_dict により品質問題をシリアライズ可能。
    - pipeline の骨組みと差分更新、品質チェックを想定した設計（jquants_client, quality モジュールとの連携を前提）。

- テストしやすさ・安全性に関する設計上の配慮
  - LLM 呼び出し用の内部関数はテストで差し替え可能（unittest.mock.patch によりモック化しやすい構造）。
  - datetime.today() / date.today() の不適切な使用を避け、全ての処理は引数で与えられる target_date に依存（ルックアヘッドバイアスの排除）。
  - DB 書き込みは冪等化を目指し、部分失敗時に既存データを不必要に消さないよう実装。
  - DuckDB を主要なローカル DB として想定。

### 変更
- （初回リリースのため過去バージョンからの変更はなし）

### 修正
- （初回リリースのため過去バージョンからの修正はなし）

### 既知の制約・挙動
- OpenAI API キーは引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出する。
- news_nlp / regime_detector ともに OpenAI の JSON mode を前提とするレスポンスパース実装が含まれるが、API 側の応答変化によりパースが失敗する可能性がある（その場合は該当チャンク/評価をスキップし、フェイルセーフで続行）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンに対応するため、書き込み前に空チェックを行っている。
- calendar_update_job / ETL 処理は jquants_client の具象実装・ネットワーク環境に依存するため、実行時に外部 API 呼び出しの例外やネットワークエラーが発生した場合はログ出力の上 0 を返す設計。

### セキュリティ
- 環境変数に機密情報を保持する想定（API トークン・パスワード）。.env 自動読み込みはテスト時に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

今後の予定メモ（非包括）:
- ETL パイプラインの complete 実装（pipeline 内の差分計算・quality チェックの具体実装）。
- 発注（execution）・監視（monitoring）モジュールの実装拡充と統合テスト。
- OpenAI 呼び出しの堅牢性向上（動的レート制御・応答フォールバックの改善）およびロギング強化。

もし特定のモジュールや関数について詳細な変更点（例: 関数シグネチャ、戻り値、例外の挙動）を CHANGELOG に追記したい場合は、対象を指定してください。