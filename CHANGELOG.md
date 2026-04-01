# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-01

初期リリース。

### 追加
- コアパッケージ構成
  - package: kabusys（__version__ = 0.1.0）
  - モジュール公開一覧: data, strategy, execution, monitoring（__all__）

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（優先度: OS 環境 > .env.local > .env）
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）
  - .env パーサ（export 式、クォート、エスケープ、行内コメントの取り扱いに対応）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを導入し、アプリケーション設定をプロパティで提供:
    - J-Quants / kabuステーション / Slack / データベース（duckdb/sqlite）/監視閾値（CPU/Memory/Disk）等
    - 環境チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）
    - パスは expanduser() で展開
    - 必須変数取得時は未設定で ValueError を送出

- アップストリーム AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に書き込む
    - タイムウィンドウ計算（JST 基準 → DB 比較は UTC naive datetime）
    - 1銘柄あたり記事数・文字数上限（バッチ肥大対策）
    - バッチ API 呼び出し（最大 20 銘柄/チャンク）
    - エクスポネンシャルバックオフ（429/ネットワーク断/タイムアウト/5xx をリトライ）
    - レスポンス検証（JSON モードの前後余白の補正、results リスト・code/score 検証）
    - スコアを ±1.0 にクリップ
    - 部分失敗時に既存スコアを保護するため、書き込みは対象コードに限定した DELETE → INSERT の冪等処理
    - テスト用に _call_openai_api を patch 可能に設計

  - regime_detector.score_regime: ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して market_regime に保存
    - ma200_ratio（200日）計算（target_date 未満データのみ使用、データ不足時は中立値を返す）
    - マクロニュース抽出（マクロキーワードでタイトルをフィルタ、最大記事数制限）
    - OpenAI（gpt-4o-mini）によるマクロセンチメント評価（APIエラー時は 0.0 にフェイルセーフ）
    - 合成スコア: ma200(70%) + macro(30%)、クリップしてラベル化（bull/neutral/bear）
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、書込み失敗時は ROLLBACK）

- データ処理・ETL（kabusys.data）
  - pipeline.ETLResult を公開（データクラス: 取得数・保存数・品質チェック結果・エラー一覧を保持）
  - etl モジュールから ETLResult を再エクスポート
  - calendar_management モジュール
    - market_calendar を用いた営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による安全策
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新（バックフィルロジック、健全性チェックを含む）

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出
    - DuckDB ベースの SQL 実装で、外部 API を呼ばない設計
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン計算（デフォルト [1,5,21]）
    - calc_ic: スピアマンのランク相関（IC）を計算
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位（ties）を平均ランクで処理するランク化ユーティリティ
  - zscore_normalize を data.stats から再エクスポート

### 変更（設計／実装上の重要点）
- DuckDB 互換性と安全性
  - executemany に空リストを投げないようにガード（DuckDB 0.10 の制約回避）
  - DATE 型の取り扱いを統一し、DuckDB からの値を date に変換するユーティリティを提供
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の扱いを意識）

- LLM 呼び出しの堅牢性
  - JSON Mode を前提にしつつ、出力に余計なテキストが混ざる場合の復元ロジックを実装
  - 5xx や接続系エラーに対しては指数バックオフでリトライ、 recover できない場合はフェイルセーフ（0.0 やスキップ）で継続
  - テスト容易性のため、内部の API 呼び出し関数は patch 可能に実装

- ルックアヘッドバイアス対策
  - いずれの AI/リサーチ関数も内部で datetime.today()/date.today() を参照せず、明示的な target_date を取る設計

### 修正（バグフィックス）
- （初期リリースのため該当なし）

### 既知の制約 / 注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出する箇所あり。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、パッケージ配布後は環境変数を明示的に設定することが推奨される。
- news_nlp の出力は外部 LLM に依存するため、スキーマ変更やモデル挙動の変化に注意。レスポンス検証で想定外の形式はスキップされる設計。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存。API 側エラーはジョブ内でハンドルされ、0 を返す。

### 開発者向けメモ
- テスト時は以下の内部関数を patch して外部 API 呼び出しをモック可能:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- duckdb 接続を使うユニットテストは一時 DB を用意し、必要なテーブルをセットアップしてからテストを実施すること。

---

（今後のリリースでは、機能追加・API 変更・バグ修正を上の形式で記録してください。）