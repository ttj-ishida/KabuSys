CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース。以下の主要機能・モジュールを実装。
  - パッケージ公開情報
    - kabusys.__version__ = "0.1.0" を設定。
    - パッケージの公開モジュール一覧: data, strategy, execution, monitoring（__all__）。
  - 設定・環境変数管理 (kabusys.config)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、インラインコメント処理）。
    - 読み込み時の上書き挙動: OS 環境変数保護（protected set）をサポートし、.env と .env.local の優先度制御を実装。
    - Settings クラスを提供し、アプリケーションで使用する主要設定 (J-Quants, kabu API, Slack, DBパス, 監視閾値, 環境モード/ログレベル判定等) をプロパティ経由で取得。未設定時のバリデーション（必須 env は ValueError）や値の範囲チェックを実装。
  - AI 関連 (kabusys.ai)
    - news_nlp モジュール
      - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込むフローを実装。
      - 時間ウィンドウ算出（JST 基準の前日 15:00 ～ 当日 08:30）を calc_news_window で提供（DB は UTC naive datetime 前提）。
      - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事/文字数上限、JSON Mode 出力のバリデーション、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
      - DuckDB の executemany の空リスト制約を考慮した安全な DB 書き込み（部分失敗時に他銘柄の既存スコアを保護）。
    - regime_detector モジュール
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定する機能を実装。
      - ma200_ratio の計算（target_date 未満のみ使用、データ不足時は中立 1.0 を返す）、マクロニュース抽出（マクロキーワードリスト）、OpenAI 呼び出し（JSON Mode）とリトライ、スコア合成とラベリング、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
      - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
  - Research（kabusys.research）
    - factor_research モジュール: モメンタム（1M/3M/6M）、200日MA乖離、ATR/流動性/売買代金などの定量ファクター計算を SQL（DuckDB）で提供。
    - feature_exploration モジュール: 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman rank）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部依存（pandas 等）なしで標準ライブラリのみを使用。
  - Data プラットフォーム（kabusys.data）
    - calendar_management モジュール
      - market_calendar テーブルを用いた営業日判定/探索 API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB にデータがない場合の曜日ベースフォールバック、最大探索範囲制約、バックフィルや健全性チェックを含むカレンダー更新ジョブ（calendar_update_job）を実装。J-Quants クライアントとの差分取得・保存フローを想定。
    - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
      - ETLResult データクラスを実装し、ETL 実行結果・品質チェック結果・エラー収集の構造を提供。to_dict により品質イシューを辞書化して出力可能。
      - ETL の設計方針（差分更新、backfill、品質チェック継続、id_token 注入可能性）をコードコメントに明記。
    - jquants_client インターフェースを想定した差分取得・保存処理を実装（カレンダー/市場データの取得と保存を想定）。
  - その他
    - 複数モジュールで DuckDB の挙動（date 型、executemany の空リスト制約等）に合わせた実装・安全性考慮を行っている。
    - 各所で冪等性（DELETE→INSERT や ON CONFLICT 戻し）やトランザクション（BEGIN/COMMIT/ROLLBACK）の扱いが統一的に実装されている。
    - すべての日付・時間処理はルックアヘッドバイアス防止のため target_date パラメータに依存し、date.today() / datetime.today() を用いない設計方針を採用。

Changed
- 初版リリースのため該当なし（初期実装）。

Fixed
- 該当なし（初期実装）。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的にエラー扱い。
- 環境ファイル読み込み時に OS 環境変数を保護するため protected set を利用し、意図しない上書きを防止。

Internal
- 各モジュールに詳細なログ出力（info/warning/debug）を追加し、運用時のトラブルシュートを容易にしている。
- OpenAI 呼び出しはテストで差し替え可能な _call_openai_api を用意（unittest.mock.patch でモック化しやすい構造）。

Known issues / Notes
- data.pipeline モジュール内の一部関数実装に、ファイル末尾での未完/誤植の痕跡が見られます（_get_max_date の戻り処理の途中と思われる行 "return date.fro"）。ビルド／実行前に当該箇所の修正（正しい日付変換処理への補完）を推奨します。
- 本リリースは初期実装であり、外部 API（J-Quants / OpenAI）や DB（DuckDB）周りの実運用テストが必要です。特に OpenAI のレスポンス形式や SDK バージョンの差分による例外型の違い（status_code 等）に注意する考慮がコード内にありますが、実運用での確認を推奨します。

Compatibility
- DuckDB を利用する前提（date 型の扱い、executemany の挙動など）で実装されています。DuckDB のバージョン差分に依存する箇所があるため、想定動作する DuckDB バージョンでの動作確認を推奨します。

Acknowledgements
- 本CHANGELOGはリポジトリ内のソースコードから推測して作成しています。実際のリリースノートには追加の運用メモや設定手順（.env.example 等）があるとより有用です。