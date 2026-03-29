# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、Semantic Versioning を採用しています。

全般:
- 日付はリリース日を示します。
- このファイルはコードベース（src/kabusys 以下）を読み取って推測した機能・設計方針に基づき作成しています。

## [Unreleased]

### Added
- 今後のリリースに向けた未確定の改善やバグ修正をここに記載します。

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群と主要機能を提供。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージ外部公開 API に data, strategy, execution, monitoring を含める。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みするロジックを実装。
    - プロジェクトルートの自動検出 (.git または pyproject.toml) に基づく読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env ファイルの堅牢なパーサー実装（コメント・export 形式・クォート・エスケープ対応）。
  - Settings クラスを提供し、必須設定 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等) の取得とバリデーションを実施。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live, is_paper, is_dev）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を算出・保存。
    - 時間ウィンドウ計算（JST 基準）とトークン肥大化対策（記事数・文字数上限）。
    - バッチ処理（最大20銘柄/コール）、JSON Mode を用いたレスポンス検証、スコアの ±1.0 クリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライと、失敗時のフェイルセーフ（スキップ継続）。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時に既存データを保護。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
    - マクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）実装、API エラー時は macro_sentiment=0.0 にフォールバック。
    - リトライロジック、JSON パースおよび例外処理を組み込み、DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily/raw_financials から計算する関数群を提供。
    - データ不足時の None 処理やスキャン範囲調整、ログ出力を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対応（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関。
    - 統計サマリー（factor_summary）とランク関数（rank）を提供。
  - 研究ユーティリティの再公開（zscore_normalize 等）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API からの差分取得 → 保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供して ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分取得、バックフィル、品質チェックの設計方針を実装する基盤を準備。
    - etl モジュールで ETLResult を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動読み込み時、既存の OS 環境変数を保護するため protected set を導入。
- 必須トークン（OpenAI, Slack, J-Quants, kabuステーション等）を明示的に取得・検証し、未設定時は ValueError を投げて安全に停止。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、datetime.today()/date.today() の直接参照を極力避け、関数引数の target_date を基準として処理を行う設計。
- DuckDB 互換性（executemany 空リスト回避やリスト型バインドの回避）に配慮した実装。
- OpenAI 呼び出しはテスト容易性のためラップされ、ユニットテストで差し替え可能（unittest.mock.patch 対応）。
- DB 書き込みは部分失敗を許容する（対象コードのみ上書き）ことでデータの保護を優先。

### Breaking Changes
- （初回リリースのため該当なし）

---

開発に関する補足や未記載の内部実装について質問があればお知らせください。必要に応じて、より詳細なリリースノート（テーブル・例・ログ出力例）を追記します。