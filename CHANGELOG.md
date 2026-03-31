# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

- 計画中 / 予定
  - 戦略（strategy）・発注／実行（execution）・監視（monitoring）モジュールの実装拡張
  - 単体テスト・統合テストの拡充（特に OpenAI 呼び出しのモック周り）
  - J-Quants / kabu API クライアントの追加の堅牢化、エラー観測性向上
  - ドキュメント（Usage / Deployment / Configuration）の整備

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買プラットフォームの基盤機能群を実装・公開。

### 追加 (Added)

- パッケージ基本情報
  - パッケージルート定義（kabusys）とバージョン定数: `__version__ = "0.1.0"`。
  - 公開モジュール候補として ["data", "strategy", "execution", "monitoring"] を定義（strategy 等は将来実装予定のため現状は一部未実装）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - .env パーサ実装（export KEY=val 形式、クォート文字列、エスケープ、行内コメントの考慮）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等の設定取得とバリデーションを行う。
  - 環境名（development / paper_trading / live）やログレベルの妥当性チェックを実装。

- データ基盤（src/kabusys/data/*）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の有無に応じた曜日ベースのフォールバック、最大探索日数制限、バックフィル戦略、夜間更新ジョブ `calendar_update_job` を実装。
  - ETL パイプライン基盤:
    - ETL 結果を表現するデータクラス `ETLResult` を公開（src/kabusys/data/pipeline.py）。
    - ETL 用ユーティリティ（最終取得日の取得、テーブル存在チェック等）、差分取得・バックフィル方針の実装方針を含む。
  - `etl` モジュールで `ETLResult` を再エクスポート。

- AI / ニュース NLP（src/kabusys/ai/*）
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出、`ai_scores` テーブルへ書き込む `score_news` を提供。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 換算）を実装（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（記事数・文字数のトリム）、JSON Mode 応答の検証、リトライ（429/接続/タイムアウト/5xx に対する指数バックオフ）を実装。
    - API レスポンスの堅牢なバリデーション・クリップ処理を実装（レスポンスに余計なテキストが混入する場合の復元ロジック含む）。
    - テスト容易性のため `_call_openai_api` を差し替え可能に設計。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し `market_regime` テーブルへ冪等書き込みする `score_regime` を実装。
    - ma200 比率計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し（リトライ / フェイルセーフ）を含む。
    - API キー注入が可能で、未設定時は環境変数 `OPENAI_API_KEY` を参照。未設定時は ValueError を送出。

- リサーチ・分析（src/kabusys/research/*）
  - factor_research:
    - モメンタム（1M/3M/6M リターン・ma200 乖離）、ボラティリティ（20日 ATR・相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL によって計算する `calc_momentum`, `calc_volatility`, `calc_value` を実装。
    - データ不足時の None ハンドリング、ログ出力を実装。
  - feature_exploration:
    - 将来リターンの計算（calc_forward_returns、任意ホライズン対応）、IC（Information Coefficient）計算（Spearman の ρ）およびランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリ + DuckDB のみで実装。

- 共通・実装方針
  - DuckDB を主要な分析 DB として利用。
  - ルックアヘッドバイアス対策として内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DB への書き込みは冪等性を意識（DELETE → INSERT など）し、部分失敗時に既存データの保護を考慮。
  - OpenAI 呼び出しは明示的にリトライ・バックオフを行い、致命的な API 失敗があってもフェイルセーフ（スコアを 0 にフォールバック、例外を投げず処理継続）を採用している箇所がある。

### 変更 (Changed)

- 新規リリースにつき変更履歴は初出の内容を記載（基盤実装の追加）。

### 修正 (Fixed)

- 初期実装の中で以下の耐障害性処理を追加
  - .env 読み込みでの I/O エラーに対する警告出力（読み込み失敗時に例外を投げず警告）。
  - DuckDB の executemany が空リストを受け取れない問題を回避するためのガード（空パラメータ時は実行をスキップ）。
  - OpenAI API レスポンスパース失敗時のログとフォールバック（例外伝播を回避）。

### セキュリティ (Security)

- 環境変数の自動上書き挙動に関して保護機構を導入:
  - 自動ロード時に OS 環境変数のキーセットを保護（.env の値で上書きされない）。
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト等で利用可能）。
- 重要な API キー（OPENAI / JQUANTS / SLACK / KABU）を明示的に必須として `Settings` でチェック。未設定時は早期に ValueError を出すことで誤設定による動作を防止。

### 既知の制限 / 注意事項 (Known issues / Notes)

- OpenAI を用いる機能（news_nlp / regime_detector）は実行に `OPENAI_API_KEY` が必要。API 呼び出しはコスト・レート制限の影響を受ける可能性がある。
- top-level の __all__ に含まれる `strategy`, `execution`, `monitoring` は将来的なモジュールであり、現状は主要な実装が揃っていない可能性がある（今後のバージョンで追加予定）。
- news_nlp / regime_detector は gpt-4o-mini を前提に設計されているが、モデル変更時にプロンプトや応答検証ロジックの見直しが必要。
- DuckDB のバージョン差異によるプレースホルダ挙動（リストバインド等）に配慮した実装を行っているが、運用環境では DuckDB バージョンの互換性確認を推奨。

---

著者注: 上記はコードベースの実装内容から推測してまとめた CHANGELOG です。実際のリリースノートやプロジェクト方針に合わせて文言や項目を調整してください。