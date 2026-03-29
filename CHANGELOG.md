Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録しています。  
このプロジェクトは「Keep a Changelog」規約に準拠します。  
配布されている初回リリースは 0.1.0 です。

[Unreleased]
------------

- (なし)

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルート: src/kabusys/__init__.py にて __version__ を 0.1.0 として公開。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に基づく）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local および OS 環境変数から設定値を読み込む自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に実行。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env の読み込み順序: OS 環境 > .env.local > .env（.env.local は override=True）。
  - 高機能な .env パーサ実装:
    - export PREFIX、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱い等に対応。
  - Settings クラス: 環境変数をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - デフォルトパス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
  - KABUSYS_ENV 値検証（development / paper_trading / live）と LOG_LEVEL 値検証（DEBUG/INFO/...）。
  - ヘルパー: is_live / is_paper / is_dev プロパティ。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブルの読み書き、祝日/SQ/半日判定）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存する夜間バッチ実装。バックフィル・健全性チェックあり。
    - DB 未取得時には曜日ベースのフォールバック（土日を休日）を採用して一貫した挙動を保証。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分取得・バックフィル・品質チェックの設計に基づく ETL 基盤を実装。
    - DuckDB 互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティ。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news および news_symbols から記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得、ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime に変換して使用）。
    - API 呼び出しはチャンク（最大 20 銘柄）で実施。1銘柄当たり最大記事数・文字数でトリム。
    - リトライ: 429/ネットワーク断/タイムアウト/5xx をエクスポネンシャルバックオフで再試行。その他エラーはスキップ（フェイルセーフ）。
    - レスポンス検証: JSON パース、"results" リスト構造、コード整合性、スコア数値性、±1.0 にクリップ。
    - DB 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT して既存スコアを保護（DuckDB の executemany の空リスト制約に配慮）。
    - テスト容易性: 内部の _call_openai_api をパッチ可能（unittest.mock.patch 推奨）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースによるマクロセンチメント（重み 30%）を合成して market_regime テーブルに書き込む。
    - マクロニュースは news_nlp.calc_news_window で算出されるウィンドウから抽出し、OpenAI（gpt-4o-mini）により JSON 出力で macro_sentiment を取得。
    - LLM 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（警告ログ）。
    - レジームスコアはクリップ化され、閾値により bull / neutral / bear にラベル付与。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を参照して PER / ROE を計算。
    - いずれも DuckDB の SQL ウィンドウ関数を使って効率的に集計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装（最小有効サンプル数チェックあり）。
    - rank: 平均ランク（同順位は平均）を返すユーティリティ。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージ __init__ で主要関数を再エクスポート。

- テスト性・堅牢性向上
  - LLM 呼び出し部分をモジュールごとに分離しており、ユニットテスト時に差し替え可能。
  - すべての "日付基準" API は datetime.today()/date.today() を直接参照しない設計でルックアヘッドバイアスを排除。
  - API 呼び出し失敗は基本的にフェイルセーフ（スコア/センチメントに中立値を使用）で継続。

Fixed
- DuckDB executemany の空リスト制約を回避するため、executemany を呼ぶ前に params が空でないことをチェックするロジックを追加（score_news 等）。

Security
- OpenAI API キーや各種トークン（J-Quants / Kabu / Slack）は環境変数経由で必須。関数呼び出し時にキーが見つからない場合は ValueError を送出して明示的に失敗するようになっています。
  - OpenAI: OPENAI_API_KEY または api_key 引数が必要（score_news / score_regime）。
  - J-Quants: JQUANTS_REFRESH_TOKEN 必須（Settings）。
  - Kabu: KABU_API_PASSWORD 必須（Settings）。
  - Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 必須（Settings）。

Changed
- (新規リリースのため該当なし)

Removed
- (新規リリースのため該当なし)

Deprecated
- (現時点で該当なし)

Breaking Changes
- なし（初回リリースのため互換性破壊の履歴はありません）。

Upgrade / Migration Notes
- 環境変数の準備:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - AI 機能を利用する場合: OPENAI_API_KEY（または関数引数で明示的に渡す）
- 自動 .env ロードはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして無効化できます。
- デフォルトの DB パスは Settings.duckdb_path / sqlite_path に定義されています。必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH で変更してください。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を想定しており、レスポンスのパースが壊れた場合は該当チャンクや macro_sentiment の取得をスキップして中立値で継続します（ログ出力あり）。

注記
- 各モジュールは DuckDB 接続を受け取り、データベース（prices_daily, raw_news, ai_scores, market_regime, raw_financials 等）に対して読み書きします。運用環境で使用する際はバックアップ・トランザクション管理を考慮してください。
- ログは各モジュールで logger を使用しており、Settings.log_level によって制御されます。

(END)