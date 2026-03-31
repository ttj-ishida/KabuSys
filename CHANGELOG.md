# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- このリポジトリの初期リリースを表す CHANGELOG（0.1.0）を作成しました。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-31

Added
- 初期公開: kabusys パッケージ全体を追加。
  - パッケージエントリポイント: src/kabusys/__init__.py （__version__ = "0.1.0"）
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 環境変数上書きロジック（override / protected キーサポート）。
  - Settings クラスを追加し、主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - 監視用しきい値（CPU/MEMORY/DISK）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev 判定プロパティ

- AI 関連機能 (kabusys.ai)
  - news_nlp モジュール: raw_news → ai_scores へニュースセンチメントを付与する score_news を実装。
    - ニュースの時間窓計算(calc_news_window)、記事集約、銘柄バッチ送信（最大 20 銘柄／チャンク）を実装。
    - gpt-4o-mini（OpenAI）を JSON Mode で呼び出し、レスポンスのバリデーションとスコアクリップ（±1.0）を行う。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、部分失敗時に他銘柄スコアを保護する DB 書き込み戦略（DELETE→INSERT）を実装。
    - DuckDB 互換性のため executemany に空リストを渡さない保護を追加。
  - regime_detector モジュール: ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジームを判定する score_regime を実装。
    - _calc_ma200_ratio、マクロキーワード抽出、OpenAI 呼び出し（_score_macro）を含むフローを実装。
    - API エラー／JSON パースエラー時のフェイルセーフ（macro_sentiment = 0.0）およびリトライ・バックオフ機構を実装。
    - レジームスコアの閾値に基づくラベル付与(bull / neutral / bear) と market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - AI モジュール共通設計:
    - OpenAI 呼び出しは各モジュールで独立実装し、モジュール間でプライベート関数を共有しない設計（テスト容易性・モジュール結合低減）。
    - デフォルトモデル: gpt-4o-mini、JSON Mode を利用。

- データ基盤 (kabusys.data)
  - calendar_management: JPX カレンダー取得・営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得のときは曜日ベースのフォールバック（土日非営業日）。
    - calendar_update_job 実装: J-Quants から差分取得、バックフィル、健全性チェック（将来日付の異常検知）を含む夜間バッチ。
  - pipeline / etl:
    - ETLResult dataclass を追加（ETL 実行結果の構造化と to_dict メソッド）。
    - ETL パイプラインの設計方針を実装（差分更新、バックフィル、品質チェック連携、例外収集方針など）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ機能 (kabusys.research)
  - factor_research: ファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を利用して PER/ROE を計算（PBR 等は未実装）。
    - DuckDB 上の SQL とウィンドウ関数を活用した実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）の計算（ties の平均ランク処理を含む）。
    - rank / factor_summary: ランク付けと各カラムの統計要約を提供。
    - pandas 等の外部依存なしに標準ライブラリ + duckdb で実装。

- その他ユーティリティ
  - DuckDB 関連の互換性処理やログ出力の拡充（警告・情報の追加）。
  - 多数の関数で「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計を明文化。

Changed
- 設計上の方針を明確化:
  - API 呼び出し失敗時は例外を直ちに上げずフェイルセーフで継続する箇所を多数実装（AI スコアリングや ETL の一部）。
  - モジュールの結合を抑え、テスト時に内部 OpenAI 呼び出しを差し替えやすくしている（unittest.mock.patch を想定）。
  - DuckDB のバージョン差分に対する防御的実装（executemany の空引数回避、list 型バインド回避など）。

Fixed
- （初期リリースにつき既知のバグ修正履歴はなし。実装時点での堅牢化項目を上記に記載。）

Security
- 環境自動読み込みを任意で無効化可能に（KABUSYS_DISABLE_AUTO_ENV_LOAD）。テストや CI での誤読込を防止。

Notes / その他
- OpenAI API キーは関数引数で注入可能（api_key 引数）。未指定時は環境変数 OPENAI_API_KEY を参照。
- DuckDB のテーブル・列存在チェックや NULL ハンドリングを細かく実装しているため、DB スキーマの不整合に対してログを残しつつ安全に動作することを目指しています。
- 一部機能（例: PBR、配当利回り）は現時点では未実装。

Assets / Contributors
- 初期実装（単一コミット相当）の内容を反映。貢献者情報はリポジトリのコミット履歴を参照してください。

----- 
参考: 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する場合は、実コミット/差分・マージ履歴に基づく調整を推奨します。