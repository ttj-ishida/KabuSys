# Changelog

すべての重要な変更をこのファイルに記録します。  
本プロジェクトは Keep a Changelog の慣例に従っています。  
発行日付はリリース時点のものを記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（version = 0.1.0）。
  - __all__ で公開モジュールを定義（data, strategy, execution, monitoring）。

- 設定管理
  - kabusys.config:
    - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
    - .env パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
    - 環境変数上書き制御（override フラグ、OS 環境変数を protected として保護）。
    - Settings クラスを提供し、必須設定取得（_require）やデフォルト値、バリデーションを実装。
    - 主要設定項目例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - Settings に便利なプロパティ（is_live / is_paper / is_dev）。

- AI（自然言語処理）関連
  - kabusys.ai パッケージ公開関数: score_news をエクスポート。
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数の上限）を実装。
    - JSON Mode を利用した応答のバリデーション（results 配列、code/score 構造、数値検証）。
    - API 呼び出しの再試行ロジック（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）を実装。
    - レスポンスパース失敗や API エラーはフェイルセーフでスキップし、全体処理を継続。
    - calc_news_window: JST 基準のニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う）。
    - score_news: ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存スコアを保護するテクニックを採用。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily / raw_news / market_regime テーブルを使用し、計算結果を market_regime に冪等書き込み。
    - OpenAI 呼び出しに関する詳細なリトライ・フォールバック（API エラーやパース失敗時は macro_sentiment=0.0）を実装。
    - _calc_ma200_ratio でデータ不足時の中立扱い（ma200_ratio=1.0）と警告ログ出力。
    - レジーム合成時の閾値とラベリング（BULL_THRESHOLD, BEAR_THRESHOLD 等）を定義。

- Data（データ基盤）
  - kabusys.data パッケージ
  - calendar_management:
    - JPX 市場カレンダーの管理ロジック（market_calendar テーブルに基づく営業日判定、next/prev/get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェック（将来日付の異常検出）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 処理の集計結果、品質チェック結果、エラー一覧を保持）。
    - ETL フレームワークの基礎（差分更新、バックフィル、品質チェックを行う設計）。jquants_client と quality モジュールと連携する設計を明記。
    - _table_exists / _get_max_date 等のユーティリティ実装。

- Research（リサーチ）
  - kabusys.research パッケージを公開（factor_research と feature_exploration の関数を再エクスポート）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL ベースで計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御や窓幅チェックを実装。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を算出（EPS が無効な場合は None）。target_date 以前の最新レコード取得ロジックを採用。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで計算。ホライズン引数のバリデーションあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（None 値・重複順位対応、十分サンプルがなければ None を返す）。
    - rank: 同順位は平均ランクを返す実装（丸め処理で ties 検出の安定化）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出（None 値除外）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出して早期検出する。
- .env ロードは OS 環境変数を保護（protected set）し、デフォルトでは既存 OS 環境変数を上書きしない挙動。
- 外部 API 呼び出し（OpenAI / J-Quants）失敗時はフェイルセーフ化（部分スコアの省略やデフォルト値の採用）し、致命的なクラッシュを防ぐ設計。ただし API キー漏洩や誤設定には注意。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして公開する場合は、著者／メンテナ情報や差分の根拠（コミットハッシュ等）を追加してください。