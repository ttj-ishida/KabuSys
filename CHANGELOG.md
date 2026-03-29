# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

※ バージョンはパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアモジュールを実装・公開。

### Added
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージとして data, strategy, execution, monitoring をエクスポート。
- 設定・環境読み込み（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装に。
  - .env の行パースで以下に対応:
    - コメント行、空行、`export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行の inline コメント（`#`）取り扱い（直前が空白／タブの場合にコメントと認識）
  - 自動読み込みの優先順位は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
  - 環境変数の保護（既存 OS 環境を protected として上書きを防止）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得可能。KABUSYS_ENV と LOG_LEVEL の妥当性チェックを実装。
- AI 関連機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを計算して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（内部は UTC naive で扱い）。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数と最大文字数でのトリムをサポート。
    - API の一時的エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフのリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リストの検証、スコアの数値判定・有限値判定、±1.0 でのクリップ）を実装。LLM が整数でコードを返すケースのためコードを文字列化して照合。
    - DuckDB の executemany の制約を考慮し、空リストの実行回避処理を実装（部分失敗時に既存スコアを保持する戦略）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - prices_daily からのデータ取得は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロニュース抽出はキーワード（日本語・英語）でフィルタして最大記事数を制限。
    - OpenAI 呼び出しは JSON Mode を利用、リトライ戦略・エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定・次/前営業日検索・期間の営業日列挙・SQ 判定などのユーティリティを提供。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装（バックフィル、健全性チェックを含む）。
    - DB にデータが無い場合の曜日ベースのフォールバック実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分更新、バックフィル戦略、品質チェックフック、idempotent 保存を想定した ETLResult データクラスを実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
    - ETLResult は品質問題の要約やエラー有無判定用のプロパティと辞書変換メソッドを持つ。
  - jquants_client と quality 等のクライアント連携ポイントを想定した設計。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M）、ma200 乖離、Volatility（20日 ATR）および流動性指標（20日平均売買代金、出来高比）を DuckDB 上で計算する関数を実装。
    - raw_financials を用いた Value（PER, ROE）の計算を実装。EPS が 0 または欠損時は PER を None にする挙動を明記。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient）計算（スピアマン順位相関）と rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算。
  - zscore_normalize を含むデータユーティリティの再エクスポート。

### Changed
- 設計・実装方針に関する言及をコードコメント・ドキュメントに網羅的に追加
  - ルックアヘッドバイアス対策として datetime.today() / date.today() を直接参照しない方針を明記した上で各関数で target_date を明示的に受ける設計に。
  - DuckDB の互換性を考慮した実装（executemany の空リスト回避、list バインドの回避等）。

### Fixed / Robustness
- OpenAI レスポンスの堅牢性向上
  - JSON mode でも余計な前後テキストが混入するケースに対し、最外の {} を抽出して JSON を復元するフォールバックを追加。
  - API エラー分類（RateLimitError / APIConnectionError / APITimeoutError / APIError）に応じた再試行ロジックとログ出力を明確化。
- データ不足時のフォールバック挙動を明確化
  - MA200 や ATR 等で必要な過去行数が不足する場合、None または中立値（1.0）を返して処理を継続するフェイルセーフを実装。
- .env 読み込み時の IO エラーを warnings.warn で通知し処理継続するように改善。
- market_regime / ai_scores への書き込みは冪等に（DELETE → INSERT）し、トランザクションで保護。ROLLBACK の失敗時のログ出力を追加。

### Security
- 環境変数読み込みで OS 環境を protected として扱い、意図しない上書きを防止。
- 必須の機密情報（OpenAI API キー、Slack トークン、J-Quants トークン、kabu API パスワード等）は Settings で必須化し、未設定時は明示的に ValueError を投げる設計に。

### Notes / Migration
- OpenAI 関連機能は gpt-4o-mini + JSON Mode を使用する実装になっており、API キーは api_key 引数または環境変数 OPENAI_API_KEY で提供する必要があります。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB との相互運用性のため、executemany に空リストを渡さないようにしているため、将来 DuckDB の挙動が変わる場合は注意してください。

---

今後のリリースでは以下を予定（例）:
- strategy / execution / monitoring の具体的な注文実行ロジック・モニタリング機能の実装
- テストカバレッジ強化、CI での OpenAI 呼び出しモック整備
- パフォーマンス改善（大量銘柄時の並列化等）

もし CHANGELOG に追加してほしい詳細（リリース日修正、個別変更の分割など）があれば教えてください。