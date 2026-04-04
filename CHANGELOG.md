CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載します。  
安定版リリース、後方互換性、重要な設計判断などは各項目に記載しています。

フォーマット: https://keepachangelog.com/ja/

Unreleased
----------
- 今後の変更はここに記載します。

0.1.0 - 2026-04-04
------------------
Added
- 基本メタ情報
  - パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。
  - パッケージ公開 API として data, strategy, execution, monitoring を想定（__all__）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は __file__ 起点で親ディレクトリを探索し、.git または pyproject.toml を検出して行うため CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 環境変数上書き制御（override / protected）により OS 環境変数の保護をサポート。
  - Settings クラスを公開し、主要な設定をプロパティで取得可能:
    - J-Quants / kabu / LINE / DB（duckdb/sqlite）/監視（PID, kill flag,閾値）/システム設定（env, log_level, is_live 等）
  - 環境変数の必須チェック関数 _require を実装し、未設定時は ValueError を送出。

- AI（自然言語処理 / レジーム検出） (src/kabusys/ai/*.py)
  - ニュース NLP スコアリング (news_nlp.py)
    - タイムウィンドウ計算 (calc_news_window)（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON モード）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - バッチサイズ上限、記事数/文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーション、スコア ±1.0 クリップを実装。
    - スコアの書き込みは冪等的（DELETE → INSERT、部分失敗時に既存データを保護）で DuckDB 互換性（executemany の空リスト回避）に配慮。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（Nikkei225 連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、API リトライ・バックオフ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジーム計算後は market_regime テーブルへ冪等的にトランザクション（BEGIN/DELETE/INSERT/COMMIT）で書き込み、失敗時は ROLLBACK を実行。
    - lookahead バイアス対策として datetime.today()/date.today() を直接参照しない設計。
    - OpenAI クライアントに関する特定例外（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）を考慮した堅牢な実装。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data/*.py)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを基に営業日判定ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は休場）し、DB 登録が一部のみの場合でも一貫した判定を行う。
    - 夜間バッチ更新 calendar_update_job により J-Quants API から差分取得し冪等保存（fetch / save via jquants_client）。バックフィル、健全性チェック等を実装。
    - 探索範囲の上限（_MAX_SEARCH_DAYS）やバックフィルの考慮、NULL 値検出時の警告など、安全性重視の実装。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分更新の方針（営業日単位の差分算出、バックフィル）、品質チェック（quality モジュールとの連携）を想定したインターフェース。
    - jquants_client を利用した idempotent な保存（ON CONFLICT DO UPDATE）を前提に設計。
    - ETL 実行中のエラー・品質問題の集計と to_dict によるシリアライズをサポート。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - ファクター計算 (factor_research.py)
    - Momentum: mom_1m, mom_3m, mom_6m（営業日ベースのラグ）、ma200_dev（200日 MA 乖離）。データ不足時は None。
    - Volatility / Liquidity: atr_20（20日 ATR の平均）、atr_pct（ATR/価格）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高 / 20日平均出来高）。不十分なウィンドウ時は None。
    - Value: PER（price / eps）、ROE（raw_financials から直近 report_date <= target_date のデータを取得）。EPS が 0 または欠損の場合は PER を None。
    - すべて DuckDB 上の SQL を使い、prices_daily / raw_financials のみ参照する設計。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns)：指定ホライズン（デフォルト [1,5,21]）に対する fwd_{h}d を計算。horizons の検証あり。
    - IC（Information Coefficient）計算 (calc_ic)：factor_records と forward_records を code で結合し、Spearman（ランク相関）を算出。データが不足すると None を返す。
    - rank：同順位は平均ランクで処理（丸めで ties の検出漏れを防止）。
    - factor_summary：count/mean/std/min/max/median を計算するユーティリティ。

Other notable design decisions and safety measures
- DuckDB を主要なストレージとして想定し、SQL と Python を組み合わせて処理を行う設計。
- ルックアヘッドバイアス回避のため、内部で現在日時を直接参照しない（target_date ベースの計算）。
- 外部 API 呼び出し（OpenAI / J-Quants）に対する堅牢なエラーハンドリング（リトライ、バックオフ、フェイルセーフ）を導入。API レスポンスの厳密バリデーションを行い、異常時には安全にスキップまたはフォールバックする。
- DB 書き込みは可能な限り冪等（DELETE → INSERT / ON CONFLICT）にし、トランザクションで整合性を担保。失敗時は ROLLBACK を試行。
- テスト容易性: OpenAI 呼び出し等は差し替え可能（モジュール単位での patch を想定）、executemany の空パラメータに対する互換性配慮など実運用を想定した実装。

Requirements / 環境変数（主要）
- 必須（使用する機能により必要）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（news_nlp / regime_detector を使用する場合）
- 任意:
  - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH 等（Settings でデフォルトあり）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 外部 API キーは環境変数で管理する設計。公開リポジトリでのキー格納を避けること。

補足
- 本 CHANGELOG はソースコードから推測して作成しています。実際のドキュメントや運用手順、公開 API の詳細（strategy, execution, monitoring モジュール等）は別途補完が必要です。