# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、SemVer を使用します。

※このファイルはコードベースから推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-27
### Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージの公開インターフェースを定義（src/kabusys/__init__.py）
    - __version__ = 0.1.0
    - __all__ で data, strategy, execution, monitoring をエクスポート（将来のモジュール統合を想定）

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env/.env.local を自動読み込みする仕組みを実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD に依存しない）
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - OS 環境変数は保護され、.env の上書きを防止
  - .env 行パーサ実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応）
  - Settings クラスを提供し、以下のプロパティ経由で設定値を取得（必須チェック含む）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev の簡易フラグ

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を JST→UTC で変換して処理（calc_news_window）
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を取得
    - バッチ処理: 最大 20 銘柄/回、1 銘柄あたり最大 10 記事、最大 3000 文字にトリム
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ
    - レスポンス検証: JSON パース、"results" フォーマット検証、未知コードの無視、数値検証、±1.0 にクリップ
    - DB 書き込み方針: 部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT（トランザクション）
    - テストしやすさ: _call_openai_api をパッチ差し替え可能に実装
    - パブリック API: score_news(conn, target_date, api_key=None) がスコアを ai_scores に書き込み、書込件数を返す
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）で
      市場レジーム（bull/neutral/bear）を日次判定
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止
    - マクロ記事は定義済みキーワードでフィルタ（最大 20 件）し、OpenAI（gpt-4o-mini）で JSON レスポンスを要求
    - LLM 呼び出しはリトライ/バックオフを実装。API/解析失敗時は macro_sentiment=0.0 でフォールバック（例外は投げない）
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 閾値によりラベル判定（BULL_THRESHOLD=0.2, BEAR_THRESHOLD=0.2）
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装
    - テストしやすさ: _call_openai_api を差し替え可能
    - パブリック API: score_regime(conn, target_date, api_key=None) が market_regime テーブルに書き込み

- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算
    - DuckDB 上の SQL と Python 組合せで実装し、prices_daily / raw_financials のみを参照（外部 API へのアクセスなし）
    - データ不足時は None を返す等の堅牢な設計
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応、最大ホライズンに合わせたスキャン範囲
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関を実装、レコード不足（<3）で None を返す
    - ランキングユーティリティ（rank）: 同順位は平均ランク、浮動小数誤差対策に round(..,12) を採用
    - 統計サマリ（factor_summary）: count/mean/std/min/max/median を算出（None を除外）
    - 公開 API を __all__ で整理して再エクスポート

- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティを提供
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバック
    - next/prev/search は最大探索日数を設定して無限ループを回避（_MAX_SEARCH_DAYS）
    - 夜間バッチ更新 job (calendar_update_job): J-Quants API から差分取得、バックフィル（直近 _BACKFILL_DAYS を再フェッチ）と健全性チェックを実装
    - jquants_client 経由の取得/保存で冪等性を確保（J-Quants 側の fetch/save を利用）
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を定義（取得/保存件数、品質問題リスト、エラーリスト等）
    - 差分更新・バックフィル・品質チェックの設計思想を文書化
    - DuckDB のテーブル存在チェックと最大日付取得ユーティリティを実装
    - etl モジュールで ETLResult を再エクスポート

### Design / Quality / Testability
- ルックアヘッドバイアス対策: 各モジュール（AI スコアリング、ファクター計算、将来リターン計算など）は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に受け取る設計。
- フェイルセーフ: OpenAI 呼び出しや外部 API エラー時は例外をそのまま上げず、フォールバック値（例: 0.0）で継続する箇所が多く、運用時の堅牢性を重視。
- テスト容易性: OpenAI 呼び出し箇所は _call_openai_api をパッチ可能にし、外部 API をモックして単体テストを行いやすい設計。
- DuckDB 互換性配慮: executemany に空リストを渡さない等、DuckDB の既知の挙動に合わせた実装上の配慮。

### Removed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- 環境変数の扱いに注意: .env ファイルの自動読み込みをするが OS 環境変数は上書きされないよう保護している。自動ロードを無効化するフラグも提供。

---

今後のリリースでは以下を想定しています（例示）:
- strategy / execution / monitoring の具体実装の追加
- jquants_client の具体実装と統合テスト
- ドキュメント・使用例・CLI の追加
- 性能改善（バッチ処理の並列化など）および追加の品質チェックルール

もし特定ファイルや機能についての詳細な変更点を追記したい場合は、対象ファイル名と注目ポイントを教えてください。