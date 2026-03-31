# Changelog

全ての注記は Keep a Changelog のフォーマットに準拠しています。  
日付・内容は提示されたコードベースから推測して記載しています。

すべての非破壊的・破壊的変更はこのファイルに記録してください。

## [Unreleased]

- 小さな改善・ドキュメント整備やテスト用フックの追加などを予定。

---

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能・設計方針を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（version = 0.1.0）。公開モジュールとして data, strategy, execution, monitoring を __all__ にエクスポート。
- 設定管理 (kabusys.config)
  - 環境変数管理クラス Settings を追加。J-Quants / kabuステーション / Slack / DB /監視 /システム設定等のプロパティを提供。
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を起点に探索）。
  - .env ロード挙動:
    - 読み込み順序: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - 強力な .env パーサを実装（export 形式対応、クォート内のエスケープ処理、インラインコメントルール等）。
  - 必須環境変数未設定時に分かりやすい ValueError を送出する _require ユーティリティ。
  - 環境値の検証（KABUSYS_ENV 値や LOG_LEVEL の許容値チェック）。
  - デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）と監視閾値の既定値を提供。
- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores テーブルに保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供（UTC naive datetime を返す）。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数と文字数のトリム、レスポンス検証（JSON パース・結果構造・スコア数値検証）を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフによるリトライを実装。失敗時は部分スキップし、他銘柄の既存データを保護するため書き込みは対象コードのみ置換（DELETE→INSERT）。
    - テスト容易性のために _call_openai_api を patch 可能な設計に。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily と raw_news を参照し、ma200_ratio 計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - API 呼び出し失敗やパース失敗時はフェイルセーフとして macro_sentiment=0.0 にフォールバック。
    - テスト容易性のために _call_openai_api を独立実装（news_nlp と共有しない）。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB データ優先、未登録日は曜日ベースでフォールバックする設計。
    - calendar_update_job を実装: J-Quants API から差分取得→market_calendar へ冪等更新（バックフィルや健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラーログの格納、辞書化メソッド）。
    - ETL パイプライン設計方針を反映（差分取得、バックフィル、品質チェックとの連携、id_token 注入可能設計）。
  - jquants_client との連携を前提とした設計（fetch / save 関数の呼び出し）。
- Research モジュール (kabusys.research)
  - ファクター計算モジュール群を追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を算出（EPS が 0/NULL の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズンの LEAD を用いて一括取得）を計算。
    - calc_ic: スピアマン（ランク）相関による IC 計算を実装（不足データ時は None を返す）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank ユーティリティを実装（同順位は平均ランク、丸め処理により浮動小数点 tie を扱う）。
  - kabusys.data.stats の zscore_normalize を再エクスポートするための研究パッケージ __init__ を設定。

### 変更 (Changed)
- 設計方針・実装上の重要な決定点（コード内ドキュメント化、設計注記として含む）
  - ルックアヘッドバイアス防止のため、各処理で datetime.today() / date.today() へ直接依存しない設計を徹底（target_date を明示引数として受け取る）。
  - DuckDB を分析データの主要ストレージとして利用（DuckDB の executemany の振る舞いに対する注意・ガードあり）。
  - DB 書き込みはできる限り冪等化（DELETE→INSERT、ON CONFLICT 想定、トランザクション使用）して部分失敗時のデータ保全を優先。
  - OpenAI 呼び出しは JSON モード（厳密な JSON 出力）を期待すると同時に、余剰テキスト混入時の復元ロジックを追加。

### 修正 (Fixed)
- フォールバックとエラーハンドリングの整備
  - OpenAI など外部 API の失敗に対し、リトライ（指数バックオフ）／5xx とそれ以外の判別／最終失敗時のフェイルセーフ（スコアを 0.0 にする・部分スキップ）を実装。
  - .env ファイル読み込み失敗時に warnings.warn を使用して安全に継続するように変更。
  - DuckDB の日付値変換ユーティリティ _to_date を実装し DB 日付型の取り扱いを安定化。

### セキュリティ (Security)
- 環境変数に依存する機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）は Settings 経由で必須チェックを行う。未設定時は例外を送出して早期に検出。

### ドキュメント/テストフック (Documentation / Tests)
- 各モジュールに処理フロー・設計方針・注意点を詳細に docstring として記載。これにより保守性とレビュー性を向上。
- OpenAI 呼び出し部（_call_openai_api）を直接 patch できるように実装してユニットテストを容易化。

### 既知の制限 / 今後の作業 (Known issues / Todo)
- 一部機能は jquants_client や外部 API 実装に依存しており、実運用前にそれらクライアント実装と統合テストが必要。
- strategy / execution / monitoring パッケージ（__all__ に含む）が公開されているが、本スナップショットではそれらの実装の詳細が含まれていない（別途実装予定）。
- ai モジュールの LLM 呼び出しはコストがかかるため、バッチサイズやトークン制限のチューニングが今後必要。
- DuckDB バージョン差異に起因する parametrized list binding の不安定性に対応済みだが、将来的に DB バージョン条件分岐や統合テストでの検証が望ましい。

---

メンテナンス: 今後のリリースでは以下を含める予定
- strategy / execution の自動発注ロジック（kabu ステーション API 連携）とモニタリング（プロセス監視・Slack 通知）の実装。
- より詳細なドキュメント（使用手順、環境構築例、運用ガイド）。
- CI テスト（DuckDB を用いたユニット／統合テスト）、およびモックを使った LLM 呼び出しテストの追加。