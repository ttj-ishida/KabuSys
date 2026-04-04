CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-04
--------------------

初期リリース。日本株自動売買/データ基盤のコア機能群を実装しました。主な追加点と設計上の注意点を下記にまとめます。

Added
- パッケージ骨格
  - kabusys パッケージを追加。
  - __version__ を "0.1.0" として公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出: .git または pyproject.toml を起点に探索（CWD非依存）。
    - 読込順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントを扱う。
    - 既存 OS 環境変数はデフォルトで保護され、.env による上書きは行われない（.env.local での上書きは可能）。
  - Settings クラスで主要設定をプロパティとして提供（必須値取得時は未設定で ValueError）。
    - J-Quants / kabu API / LINE / データベース/監視/システム関連の設定をカバー。
    - 主要デフォルト:
      - KABU_API_BASE_URL: http://localhost:18080/kabusapi
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEMORY/DISK 閾値 等
    - 環境: KABUSYS_ENV は development / paper_trading / live を許容。LOG_LEVEL の検証も実施。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols を用いたニュースセンチメントスコアリングを実装。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのスコアを取得。
    - バッチ処理（最大 20 銘柄／コール）、1銘柄あたり記事数と文字数のトリム制御。
    - 再試行ロジック: レート制限・接続断・タイムアウト・5xx を対象に指数バックオフ。
    - レスポンス検証: JSON 抽出、results 配列、code と score の検証、未知コードは無視、スコアを ±1 にクリップ。
    - ai_scores テーブルへ安全に置換（対象コードのみ DELETE → INSERT、トランザクション）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、target_date ベースでウィンドウを算出。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の market_regime を判定。
    - マクロセンチメントはニュースタイトル群を LLM（gpt-4o-mini）へ渡して JSON で取得。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
    - ラベル付け閾値: bull / neutral / bear。
    - API 失敗時は macro_sentiment=0.0 として継続（フォールトトレラント）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー取得・管理および営業日の判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未登録の領域は曜日（土日）ベースでフォールバックする設計（DB 登録がある場合は DB 値優先）。
    - 夜間バッチ: calendar_update_job により J-Quants API から差分取得し冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.ETLResult 経由で再エクスポート）。
    - ETL の設計方針: 差分更新、backfill、品質チェックの収集・報告（Fail-Fast させず呼び出し元で判断）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - jquants_client と quality モジュールを呼び出す統合ポイントを用意（実装は外部モジュール側）。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      流動性（20 日平均売買代金 / 出来高比率）、Value（PER / ROE）などのファクター計算を実装。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に計算。データ不足時は None を返す挙動。
    - 計算結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク相関）を計算。3 銘柄未満で None を返す。
    - rank / factor_summary: ランキング（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装。
  - kabusys.research パッケージは主要関数をエクスポート（zscore_normalize を data.stats から再利用）。

Changed
- 標準的なログ出力・警告を各モジュールに配置し、問題発生時に詳細な情報を残す設計にしています（例: JSON パース失敗、API リトライ、ROLLBACK 失敗等）。

Fixed
- （初版につき該当なし）

Deprecated
- （初版につき該当なし）

Removed
- （初版につき該当なし）

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY から解決。未設定時は明示的に ValueError を発生させ、安全に処理を中断するように設計。

Design / 注意事項（実装に基づく重要ポイント）
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定などは全て target_date を明示的に受け取り、date.today() を内部参照しないように実装。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants 等）失敗時は例外を全面的に投げるのではなく、該当箇所を 0.0（中立）やスキップして ETLResult.errors に登録する等、システム全体の可用性を優先。
- トランザクションと冪等性:
  - DB 書き込みは明示的な BEGIN/COMMIT/ROLLBACK を使用し、DELETE→INSERT のパターンで冪等性を確保（部分失敗時に既存データを不必要に消さない工夫あり）。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する挙動を回避するため、空チェックを行ってから executemany を呼ぶ実装。
- OpenAI 呼び出し:
  - news_nlp と regime_detector で OpenAI 呼び出し関数を独立実装しており、モジュール間でプライベート関数を共有しない設計（テスト容易性と結合度低減のため）。
- 環境変数のパース:
  - .env のパースは export, quoted/unquoted 値、コメント、エスケープを考慮。キーが空の場合は無視。

今後の予定（想定）
- ETL パイプラインの実行ワークフロー実装（差分算出→jquants_client 呼出→quality チェック→監査ログ）。
- ai モジュールの追加検証・プロンプト改良とモデル選択オプションの拡張。
- monitoring / execution / strategy 等の上位層モジュールの実装と統合テスト。

貢献
- バグ報告・改善提案は issue を通じてお願いします。