# Changelog

すべての変更は Keep a Changelog の規約に従って記載します。  
このプロジェクトの初版リリース情報をコードベースから推測して作成しています。

全般:
- 日付は本 CHANGELOG の作成日（2026-03-31）を用いています。
- 本リリースはパッケージのバージョン __version__ = "0.1.0" に対応します。

## [Unreleased]
- 今後の変更を記載

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能とモジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報と公開 API を定義（kabusys.__init__）。
  - モジュール群を整備: data, research, ai, execution, strategy, monitoring（__all__ に含めたモジュール名）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env/.env.local をロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
    - 上書き制御（override）と OS 環境変数を保護する protected キーセットをサポート。
  - Settings クラスを提供（settings 1インスタンス）。
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを環境変数から取得。
    - 必須環境変数未設定時は ValueError を送出。
    - KABUSYS_ENV の値検証（development / paper_trading / live）と LOG_LEVEL 検証。

- ニュース NLP & レジーム判定 (kabusys.ai)
  - news_nlp モジュール（score_news 関数）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI（gpt-4o-mini、JSON mode）へバッチ（最大 20 銘柄/チャンク）で投げてセンチメントを取得。
    - 1銘柄あたりの記事上限数・文字数トリム、レスポンス検証（JSON 抽出、results リスト検証、コード整合性、数値チェック）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他エラーはフェイルセーフでスキップ。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ冪等的（DELETE → INSERT）に保存。
    - テスト用に内部の OpenAI 呼び出し部分をパッチ可能に設計（_call_openai_api を差し替え可能）。
    - タイムウィンドウ計算 (calc_news_window) を実装し、ルックアヘッドバイアスを防止（datetime.today() を直接参照しない）。
  - regime_detector モジュール（score_regime 関数）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出のためのキーワードリストを実装（日本語・米国系キーワード）。
    - OpenAI 呼び出しは JSON mode を使用、失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT のパターン）。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- データプラットフォーム (kabusys.data)
  - calendar_management モジュール
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックを行う実装。
    - 次／前営業日の探索で最大探索日数を設けて無限ループを防止。
    - JPX カレンダー差分取得ジョブ calendar_update_job を実装（jquants_client を経由して取得、バックフィルと健全性チェックを実装）。
  - ETL / pipeline モジュール
    - ETLResult データクラスを定義（ETL 実行の結果集約: 取得件数・保存件数・品質問題・エラー等）。
    - 差分更新、バックフィル、品質チェックの方針を反映した基盤を実装（jquants_client と quality モジュールを想定）。
    - DuckDB を用いたテーブル存在確認や最大日付取得などのユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（出来高比率・平均売買代金）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL と組み合わせて高効率に集計（欠損やデータ不足時の None 処理）。
    - 外部 API や取引 API には依存しない設計。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - Spearman（ランク）相関の実装、ties を平均ランクで処理する設計。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### ドキュメント/設計上の注意 (Notes)
- ルックアヘッドバイアス対策として、全てのバッチ判定関数（score_news, score_regime, calc_* 等）は内部で datetime.today()/date.today() を直接参照しない設計になっており、target_date を明示的に受け取ります。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode を利用。テスト容易性のために内部呼び出しをモック可能。
- DuckDB を主なデータストアとして想定しており、所定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を参照 / 書き込みします。実際のスキーマは別途定義が必要です。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後に異なる動作が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- エラー処理は「フェイルセーフで継続（部分失敗を許容）」を基本方針としており、AI API の失敗時にもシステム全体が停止しないよう設計されています（ただし、必須の環境変数は例外で通知）。

---

この CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノートや API 仕様とは異なる箇所がある可能性があるため、必要に応じてプロジェクトの公式ドキュメント・コミット履歴を参照して調整してください。