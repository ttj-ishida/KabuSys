Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コード内容から推測して機能・設計・注意点などをまとめています。必要なら日付や文言の調整を教えてください。

----------------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
----------------------------------------------------------------------

Unreleased
---------
- なし（次回リリースに向けた未確定の変更はここに記載）

0.1.0 - 2026-03-27
-----------------
初回リリース。パッケージ全体のコア機能、データ取得/ETL、調査（Research）、AIベースのニュース/レジーム分析、カレンダー管理、設定読み込みなどの基盤を実装。

Added
- パッケージ構造
  - kabusys パッケージの基本エクスポートを定義（__version__ = 0.1.0, data, strategy, execution, monitoring を公開）。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートの探索は .git または pyproject.toml を基準）。
  - export KEY=val 形式やクォート文字列、インラインコメントなどに対応した独自の .env パーサを実装。
  - OS 環境変数を保護する protected パラメータ、override モードの実装。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - 必須環境変数未設定時に明瞭なエラーメッセージを返す _require 関数。
  - Settings クラス（プロパティ経由で各種設定を取得）:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabu API: KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH, SQLITE_PATH（デフォルトを提供）
    - 環境種別 KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - 時間窓は JST ベースで前日 15:00 ～ 当日 08:30（DB 比較用に UTC naive に変換）。
    - バッチ処理（デフォルト 20 銘柄/回）、1銘柄あたりの記事数・文字数上限を実装（トークン肥大化対策）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳密な検証（JSON 抽出、results 配列、code と score の検証、値のクリップ）。
    - DuckDB へは idempotent な置換（DELETE → INSERT）で書き込み。部分失敗時に既存データを保護。
    - テスト容易性: _call_openai_api はパッチ差替え可能。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のみを使用しルックアヘッドを防止。
    - マクロ記事はキーワードフィルタリングで取得、記事がある場合のみ LLM 呼び出しを行う。API エラー時は macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは retry/backoff を実装、JSON パース失敗は警告して 0.0 を返すフェイルセーフ。
    - 結果は market_regime テーブルに冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - テスト容易性: _call_openai_api は news_nlp と別実装（モジュール結合を避ける）。
- Research モジュール (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。真の true_range 計算で NULL 伝播を扱う。
    - calc_value: raw_financials から最新の財務データをマージして PER（EPS 有効時）と ROE を算出。
    - パフォーマンスと過去スキャン範囲のバッファ設定（スキャン日数の定義）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンをまとめて取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（同順位は平均ランク処理）。
    - rank / factor_summary: ランク付けと各ファクターの統計サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリ非依存で標準ライブラリのみで実装。
- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar を元に営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 不在時は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫性を確保。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル、健全性チェック（未来日付過多の検出）を実装。
  - pipeline / etl:
    - ETLResult: ETL 実行結果を表す dataclass（取得件数・保存件数・品質問題・エラーの集約）。
    - ETL パイプライン方針を注記（差分更新、品質チェック、backfill など）。
    - _get_max_date / _table_exists などの DB ユーティリティ。
  - ETLResult は data.etl で再エクスポート。
- 汎用設計上の配慮
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照しない内部設計（target_date を明示的に受け取る）。
  - DuckDB を主要なローカル分析 DB として明記（特定バージョン考慮: DuckDB 0.10 の executemany の挙動に対応）。
  - OpenAI 呼び出しは JSON mode を期待、厳密なレスポンス検証を行う。
  - ロギングを随所に追加し、処理経過やフォールバック時の警告を明示。
  - テスト容易性: OpenAI 呼び出しやスリープ関数の差し替えポイントを用意。

Security
- 環境変数（APIキー等）は Settings 経由で取得し、未設定時には ValueError を投げて安全に失敗する設計。
- .env 自動読み込み時に OS 環境変数を上書きしないデフォルト動作と、上書きする .env.local の読み込み順序を採用。

Notes / Known limitations
- OpenAI（gpt-4o-mini）と J-Quants の API に依存。実行には各種 API キー・トークンが必要。
- news_nlp と regime_detector は API へのネットワーク依存が強く、API エラー発生時はフェイルセーフ（スコア＝0.0 など）で続行するが完全停止を防ぐ。
- 外部依存: duckdb, openai が実行時に必要（要インストール）。
- datetime は UTC naive を内部で使うことがあるため、DB に保存されている datetime の前提（UTC）に注意。
- 一部 SQL 文は DuckDB のウィンドウ関数や row_number/lead/lag を使用しているため、互換性のある DuckDB バージョンが必要。
- .env パーサは多くのケースに対応しているが、特殊なエスケープ/複合ケースは注意が必要。

Breaking Changes
- 初版のため破壊的変更はなし。

Developer / Testing notes
- テスト時の API 呼び出し差し替え:
  - kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え可能。
  - kabusys.ai.regime_detector._call_openai_api も同様に差し替え可能。
  - regime_detector._score_macro は _sleep_fn 引数により sleep の差替え（タイムコストの削減）が可能。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストでの副作用を抑制。

----------------------------------------------------------------------
変更を加える際の提案（今後の改善案）
- optional: OpenAI クライアントの抽象化（インターフェース層）を導入してモックをさらに簡潔に。
- メトリクス/監視: スコア取得失敗率や API レイテンシ計測を組み込み、運用可観測性を向上。
- バックテスト/シミュレーション用に strategy モジュールのスタブ・サンプル戦略を追加。
- データ品質チェック結果に基づく自動アラート（Slack 連携等）の追加。
----------------------------------------------------------------------

必要があれば、特定ファイルごとの変更ログやリリースノート文言の調整（より簡潔/詳細化）を作成します。どの程度の粒度で記載したいか（ユーザ向け/開発者向け）を教えてください。