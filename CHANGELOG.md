# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを使用します。  

最新: Unreleased

## [Unreleased]
- 次回リリース向けの変更はここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージ骨組み
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、__all__ に data, strategy, execution, monitoring を登録）。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local からの自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサで以下に対応：
    - 空行・コメント行の無視
    - export KEY=val 形式の対応
    - シングル／ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォート無しのときは前の空白で # をコメント認識）
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境モード（development, paper_trading, live）などの設定をプロパティ経由で取得・検証。
  - 環境変数未設定時は明確なエラー（ValueError）を送出するユーティリティを実装。
- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込む機能（score_news）。
    - ニュース時間ウィンドウ計算（JST ベース→UTC naive datetime 変換）を実装（calc_news_window）。
    - バッチ処理（銘柄ごと最大 _BATCH_SIZE＝20）、文字数トリム、最大記事数制限などトークン肥大化対策を導入。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ実装。
    - レスポンスバリデーション（JSON 抽出、results フォーマット検証、スコア数値チェック）実装。失敗時は該当チャンクをスキップし、他銘柄を保護する設計。
    - テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
    - DuckDB への書き込みは冪等（DELETE → INSERT）かつ部分失敗に強い（影響範囲を取得済みコードに限定）。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ記録（score_regime）。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満データのみ使用）とマクロ記事抽出・LLM 評価、スコア合成、冪等 DB 書き込みを実装。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - news_nlp とは別実装の _call_openai_api を持ち、モジュール結合を低く保つ設計。
- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → market_calendar へ冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定・探索ユーティリティを提供。DB にデータがない場合は曜日ベースでフォールバック。
    - 検索範囲上限・健全性チェック・バックフィル等の安全策を実装。
  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult dataclass を追加（ETL 実行結果の構造化保存・シリアライズ）。
    - 差分取得・バックフィル戦略、品質チェックのためのフック実装方針を用意。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - jquants_client と quality モジュールとの連携を前提としたインターフェースを実装（実際のクライアント実装は別モジュール想定）。
- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、MA200 乖離、ATR、売買代金、PER/ROE 等）を計算。
    - データ不足時の扱い（None 戻し）やログ出力を実装。
  - feature_exploration モジュール
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、rank（平均ランク付与）、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで実装。
  - 研究ユーティリティ（kabusys.research.__init__）で主要関数を再エクスポート。
- 共通実装
  - DuckDB を主要なオンディスク分析 DB として利用する前提で SQL + Python のハイブリッド実装を採用。
  - ルックアヘッドバイアス防止のため、target_date 処理では datetime.today()/date.today() を直接参照しない設計を徹底。
  - 多くの関数で冪等性・部分失敗時の保護・明確なログ出力を意識して実装。
- ドキュメント的注記
  - 各モジュールに処理フロー・設計方針・フェイルセーフの説明を docstring として詳述。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- なし。

### Removed
- なし。

### Security
- API キー等の必須設定（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は環境変数で取得する設計。誤ってコミットしないよう .env.example を経由した運用を推奨。

### Notes / Usage hints
- OpenAI API 関連
  - news_nlp / regime_detector は OpenAI の JSON mode（response_format={"type": "json_object"}）を想定しており、レスポンスパースに失敗した場合は安全にスキップまたはフォールバックします。
  - テストでは kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を patch してエンドツーエンド呼び出しをモックできます。
- 環境設定
  - 自動 .env ロードはプロジェクトルート検出に依存するため、配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御するか、環境変数を直接設定してください。
- データベース
  - デフォルトの DuckDB/SQLite パスは Settings で確認・上書き可能（DUCKDB_PATH / SQLITE_PATH）。
- 既知の制約
  - 現フェーズでは一部ファクター（PBR・配当利回り等）は未実装。
  - DuckDB バインドの互換性（executemany に空リスト不可等）を考慮した実装になっています。

もし差分や追加のリリースノートをより詳細に（各モジュールごとの変更点やサンプル使用方法、互換性情報など）記載したい場合は、その範囲を指定していただければ追記します。