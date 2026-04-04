CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
初回公開リリースとして v0.1.0 を記録します。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-04
--------------------

Added
-----
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - パッケージトップは kabusys モジュールで、主要サブパッケージとして data, strategy, execution, monitoring を想定したエクスポートを含む。

- 環境設定・.env ローダー (kabusys.config)
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探す実装を追加。これによりカレントワーキングディレクトリに依存せず .env を自動ロード可能。
  - .env パーサ: export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応する堅牢なパーサを実装。
  - .env ファイル自動読み込み順序:
    - OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - OSの既存環境変数は保護（protected）され、必要に応じて上書きを制御可能。
  - Settings クラスを提供し、アプリ設定をプロパティとして取得可能:
    - J-Quants / kabuステーション / LINE Messaging API / データベース (DUCKDB/SQLite) / 監視設定（PID ファイル・kill flag・閾値）/ システム設定（環境・ログレベル判定）等をカバー。
    - 環境変数未設定時に明示的にエラーを投げる _require() を利用する必須設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV の検証（development/paper_trading/live）・LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）を実装。

- ニュース NLP & レジーム判定 (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp):
    - raw_news / news_symbols を集計し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）へ送信、JSON モードでレスポンスを検証して ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、1銘柄あたりの記事数制限、文字数トリムのパラメータ（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンスバリデーション（JSON 抽出、results フォーマット検証、コード照合、数値検証）、スコアの ±1.0 クリッピング。
    - 部分失敗に備え、ai_scores の更新は対象コードのみ DELETE → INSERT を行い既存スコアを保護。
    - calc_news_window(target_date) によるニュース収集ウィンドウ計算（JST ベースの前日 15:00 〜 当日 08:30 相当の UTC 範囲）。
    - API 呼び出しラッパーはテスト差し替えが可能（unittest.mock.patch で _call_openai_api を差し替え可能）。

  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みを行う実装。
    - マクロニュース抽出はキーワードベース（日本・米国等の主要ワード群）でタイトルを取得。
    - OpenAI（gpt-4o-mini）呼び出し、JSON パース、リトライ（RateLimit/APIConnection/Timeout/APIError の扱い）を含む堅牢化。
    - フェイルセーフ設計: API 失敗時は macro_sentiment = 0.0 で継続し例外を上げない。
    - ルックアヘッドバイアス回避: date < target_date のデータのみ使用、datetime.today()/date.today() を直接参照しない設計。

- リサーチ機能 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M のリターン、200日MA乖離（ma200_dev）を計算。データ不足時に None を返す挙動。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）等を計算。true_range の NULL 伝播を意識した実装。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0/NULL の場合は None）。PBR/配当利回りは未実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）で None を返す。
    - rank: 同順位は平均ランクとするランク化実装（浮動小数の丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。
  - research パッケージは一般的な factor 解析ワークフローをサポートするユーティリティ群を公開。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱う夜間更新ジョブ calendar_update_job 実装（J-Quants から差分取得 → 保存）。バックフィル・健全性チェックを実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した仕様。
  - pipeline / ETL:
    - ETLResult データクラスを導入（kabusys.data.pipeline.ETLResult）。ETL の取得数・保存数・品質問題・エラー集約とヘルパー（to_dict, has_errors, has_quality_errors）を実装。
    - ETL モジュールは差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
  - etl パッケージは pipeline.ETLResult を再エクスポート（kabusys.data.etl）。

- DuckDB を主要なローカル DB として使用
  - 多くの機能が DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL を用いて計算・読込・書込を行う実装になっている（テーブル例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）。

- ロギングと堅牢性
  - 各モジュールで詳細な logger メッセージを追加し、例外発生時は ROLLBACK の試行や警告ログ出力を行う等の安全策を採用。
  - API 呼び出しのリトライ、レスポンス検証、フェイルセーフ（スコア0へのフォールバック、部分書き込み保護）を重視。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Security
--------
- 初回リリースのため該当なし。

注意事項 / マイグレーション
-------------------------
- OpenAI API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で指定する必要があります。未指定時は ValueError が発生します。
- 自動で .env をプロジェクトルートから読み込む挙動があるため、CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ（テーブル名・カラム名）が前提になっている箇所が多いため、既存 DB を利用する場合は必要なテーブルを用意してください。
- news_nlp / regime_detector の OpenAI 呼び出しはテスト時に差し替え可能（_call_openai_api をモックすることで API 実コールを回避できます）。
- news_nlp の出力バリデーションは厳密に行うため、モデル出力が仕様（厳密 JSON）に従わない場合はスキップされることがあります。

貢献・フィードバック
-------------------
バグや改善要望、ドキュメントの不備は issue を作成してください。次期リリースでは以下を予定しています:
- PBR/配当利回りの計算追加（calc_value 拡張）
- strategy / execution / monitoring パッケージの実装拡充（発注ロジック・モニタリング実行環境）
- テストスイートと CI の整備、型ヒントの補完とドキュメント自動生成

---