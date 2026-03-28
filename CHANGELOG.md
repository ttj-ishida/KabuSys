# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョンポリシー: セマンティックバージョニングを想定。

## [Unreleased]

- なし（初回リリースは 0.1.0）

## [0.1.0] - 2026-03-28

初回公開リリース。以下の主要機能と設計方針を含みます。

### 追加 (Added)
- 基本パッケージ構成
  - kabusys パッケージ初期構成（data, research, ai, monitoring, execution, strategy を想定した __all__ エクスポート）。
  - パッケージバージョン: 0.1.0。

- 環境設定/読み込み
  - 環境変数管理モジュール (kabusys.config) を実装。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml による検出）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export プレフィックス、クォートやエスケープ、インラインコメントの取り扱いに対応する .env パーサー。
    - OS 環境変数を保護する protected パラメータでの上書き制御。
    - 必須環境変数取得ヘルパー _require。
    - 設定クラス Settings による属性アクセス（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定等）。
    - env/log_level の妥当性チェック（許容値チェック）と is_live/is_paper/is_dev のユーティリティ。

- AI（NLP）モジュール
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を用いた銘柄ごとのニュース集約ロジック。
    - OpenAI (gpt-4o-mini) を用いたバッチセンチメント評価（JSON mode）実装。
    - バッチサイズ、記事数・文字数制限、リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ。
    - レスポンスの厳密なバリデーションとスコアクリッピング（±1.0）。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、部分失敗時の保護）。
    - calc_news_window ユーティリティ（JST基準のニュース集計ウィンドウ算出）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。

  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news 抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み。
    - API フェイルセーフ（失敗時 macro_sentiment = 0.0）、リトライ、ログ出力。
    - ルックアヘッドバイアス防止を考慮したデータ参照設計（target_date 未満の排他条件、datetime.today() を直接参照しない）。

- Data（ETL / カレンダー / パイプライン）
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダーの取得・更新ジョブ（calendar_update_job）と、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定ユーティリティを実装。
    - market_calendar 未取得時の曜日ベースのフォールバックをサポート。
    - 最大探索日数の上限やバックフィル、健全性チェック（将来日付の異常検知）を実装。

  - kabusys.data.pipeline / ETL:
    - ETL パイプラインの結果表現 ETLResult（dataclass）。
    - 差分取得、保存、品質チェック（quality モジュールとの連携想定）などの方針とユーティリティ関数（テーブル存在確認、最大日付取得など）を実装。
    - デフォルトのバックフィル処理、calendar の先読み設定、J-Quants からの差分取得想定。
    - kabusys.data.etl に ETLResult を再エクスポート。

  - jquants_client など外部クライアント（client 実装は別モジュール想定）との連携ポイントを用意。

- Research（因子・特徴量探索）
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算、データ不足時の None 処理。
    - 出力は (date, code) キーの辞書リスト。

  - kabusys.research.feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）と rank/ic/factor_summary 等の統計ツールを実装。
    - スピアマン IC（ランク相関）計算、ランク付け（同順位は平均ランク）実装。
    - factor_summary による count/mean/std/min/max/median の算出。

### 変更 (Changed)
- N/A（初回リリースのため過去バージョンからの変更は無し）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- API キーや機密値は環境変数経由での運用を想定。必須キー未設定時は ValueError を投げることで誤設定を検出。
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で切替可能。OS 環境変数の上書きを防ぐため protected キーセットを採用。

### 注意事項 / 既知の制約 (Notes / Known issues)
- DuckDB バージョン依存:
  - executemany に空リストを渡せない点を回避するため、空チェックを行っている。
  - SQL の一部でリストバインドや ANY(?) の扱いは DuckDB のバージョン差により不安定になる可能性があるため個別 DELETE を使用。
- OpenAI 呼び出し:
  - gpt-4o-mini の JSON モードを前提にしているため、レスポンスの形式変化があった場合はパースロジックの変更が必要。
  - API レスポンスの不整合時はスキップ／フェイルセーフ（スコア=0.0、または該当銘柄のスキップ）する設計。
- ルックアヘッドバイアス対策:
  - すべての日時ロジックは target_date を明示的に受け取り、内部で date.today() / datetime.today() を使用しない方針。
- 要求される環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（関数呼び出し時に引数で指定可）などが必須または推奨。
- テストのしやすさ:
  - OpenAI 呼び出し部分は内部 _call_openai_api を patch して差し替え可能にしているためユニットテストが容易。

---

（注）この CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のリリース日やリリースノートはプロジェクト運用に合わせて調整してください。