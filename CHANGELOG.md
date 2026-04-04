# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に準拠して記載します。  
初回公開リリースの内容は、ソースコードからの推測に基づいています。

フォーマットの説明: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。パッケージ名: kabusys — 日本株自動売買 / 研究 / データ基盤用ライブラリ。

### Added
- パッケージ基盤
  - パッケージバージョンを設定 (kabusys.__version__ = "0.1.0")。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring（未来の拡張に対応）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機構を実装。
    - プロジェクトルート判定は __file__ から上位ディレクトリを探索し、.git または pyproject.toml を基準に判定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - コメント行、空行、"export KEY=val" 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント除去ロジック、クォートなしコメント判定を考慮。
  - .env 読み込み時の上書き制御:
    - override および protected（OS 環境変数保護）オプションで安全に上書き。
    - ファイル読み込み失敗時は警告を出力して処理継続。
  - Settings クラスを提供し、各種設定をプロパティ経由で取得可能:
    - J-Quants / kabuステーション / LINE API / DB パス（duckdb/sqlite） / 監視用ファイルパス / リソース閾値（CPU/MEM/DISK） / 環境 (development/paper_trading/live) / ログレベル など。
    - 必須環境変数チェック (_require)：未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値以外は ValueError）。
    - デフォルト値、Path.expanduser 等の便利な扱いを実装。

- 自然言語処理 (kabusys.ai)
  - ニュースセンチメント解析モジュール (news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄単位にニュースを結合して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを取得。
    - 時間ウィンドウは JST ベース: 前日 15:00 JST ～ 当日 08:30 JST（DB 比較用に UTC naive に変換）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄単位で送信。
    - 1 銘柄あたりの上限記事数 (_MAX_ARTICLES_PER_STOCK=10) と文字数トリム (_MAX_CHARS_PER_STOCK=3000) を実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ。リトライ上限・ログ出力に対応。
    - レスポンスバリデーション: JSON 抽出、"results" リスト検証、コード照合、スコア数値化、±1.0 にクリップ。
    - DB への書き込みは冪等性を保つため、スコア取得済みコードのみ DELETE → INSERT（部分失敗時に既存スコアを破壊しない）。
    - API キー注入可（api_key 引数）および環境変数 OPENAI_API_KEY に対応。未設定時は ValueError。
  - 市場レジーム判定モジュール (regime_detector.py)
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードリストに基づき raw_news をフィルタし、最大 _MAX_MACRO_ARTICLES 件を LLM に送信。
    - OpenAI 呼び出しは専用 client を生成して実行。リトライ/バックオフ/エラーハンドリングを実装し、API 失敗時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試み上位に例外を伝播。

- 研究機能 (kabusys.research)
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None 扱い。
    - calc_volatility: 20 日 ATR（true_range を厳密に扱う）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損時は None）と ROE を計算。最新財務レコードの取得はレポート日 <= target_date の最新を使用。
    - 各関数は DuckDB 接続を受け取り SQL で計算、日付/コードごとの dict リストを返す。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。実用上のフィルタ・最小サンプル数チェックを実装。
    - rank: 同順位は平均ランクを返す実装（丸め対策あり）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出（None を除外）。

- データ基盤 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（平日のみ営業日扱い）。
    - next/prev_trading_day は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した探索を行う。最大探索日数制限を導入して無限ループを防止（_MAX_SEARCH_DAYS=60）。
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得して market_calendar を更新。バックフィルと健全性チェック（過度な将来日付はスキップ）を実装。
  - pipeline ETL モジュール
    - ETLResult データクラスを導入し、ETL の取得件数／保存件数／品質問題／エラーをまとめて返却・監査用辞書化可能。
    - ETL の設計方針に沿い、差分更新・バックフィル・品質チェック（quality モジュール）・idempotent 保存（jquants_client.save_*）を想定したインターフェースを提供。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

### Changed
- 設計上の重要な方針（コード中注記）
  - ルックアヘッドバイアス回避: AI / 研究処理で datetime.today() / date.today() を直接参照せず、必ず target_date を引数で受け取る設計に統一。
  - DB 書き込み: 部分失敗時に既存データを不必要に消さないよう、コードレベルで削除対象を限定してから挿入する方式を採用（ai_scores など）。
  - OpenAI 呼び出しの失敗は厳格にハンドリングし、重大な障害を起こさない場合はフェイルセーフで継続（スコアを 0.0 とする等）。

### Fixed
- （初回リリースにつき該当なし／コードから想定される安定化処置を実装済み）
  - .env パースや OpenAI レスポンスパースのエッジケース（前後余分テキストが混ざる JSON など）に対する耐性を追加。

### Security
- 機密情報の扱いに関する注意
  - API キー・パスワードは環境変数経由で管理する設計（Settings に必須チェックあり）。.env 自動読み込みは環境変数で無効化可能。
  - .env 上書きの際に OS 環境変数を保護する protected オプションを採用。

### Notes / Usage highlights
- OpenAI を利用する機能（kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime）は api_key 引数でキー注入可能。指定がない場合は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError。
- news_nlp の時間ウィンドウは JST 基準で定義され、DB 内 datetimes は UTC と想定して比較する実装（calc_news_window を使用）。
- DuckDB を想定した SQL を多用しており、戻り値は list[dict] 形式で扱いやすく提供。
- jquants_client / quality モジュールや jquants API 相当のクライアントは外部依存（data.jquants_client を通して呼び出す想定）。

---

今後のリリース候補（例）
- Unreleased: モジュール分割、strategy/execution/monitoring の実装拡充、テストカバレッジ強化、CLI/自動ジョブスケジューリングの追加など。

（以上）