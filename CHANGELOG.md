# Changelog

すべての注目すべき変更点を記載します。  
フォーマットは Keep a Changelog に準拠しています。  

現在のリリース履歴はコードベースから推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-04
初回公開リリース（推測）。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出するため、CWD に依存しない。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）や各種パス（DUCKDB_PATH、SQLITE_PATH など）、監視閾値（CPU/MEM/DISK）をプロパティとして取得可能。
  - KABUSYS_ENV と LOG_LEVEL の値チェック（許容値を検証して不正値は ValueError）。

- AI（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini の JSON モード）でセンチメントをスコア化して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（UTC に変換）を対象。calc_news_window を提供。
    - バッチ処理: 銘柄を最大 20 件ずつチャンク処理、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON の抽出、results キー・型検証、未知コードの無視、スコアの数値化とクリップ）。
    - 部分失敗に備えた DB 書き換え戦略（該当コードのみ DELETE → INSERT）により既存データ保護。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みを行う機能を実装。
    - マクロニュース抽出: 定義済みキーワード群に基づくタイトル抽出、最大 20 件を LLM に渡す。
    - LLM 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
    - レジームスコアの合成と閾値判定（BULL_THRESHOLD / BEAR_THRESHOLD）。
    - DuckDB を用いたデータ取得・書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX 市場カレンダー管理ロジックを実装（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB にカレンダーが存在しない場合は曜日（土日）ベースのフォールバックを採用し、一貫性を担保。
    - 夜間バッチ job calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - カレンダー探索に最大検索日数の制限を導入し無限ループを防止。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL の集計結果、品質問題やエラーの収集を含む）。
    - ETL パイプライン（差分取得・保存・品質チェック）を想定したインターフェースと設計方針を実装（差分更新、backfill、品質チェックの収集方針など）。
    - jquants_client（外部モジュール想定）とのインタフェースを利用したデータ取得・保存の枠組みを実装。
  - データユーティリティ
    - テーブル存在チェックなどのユーティリティ関数を提供（DuckDB 用）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）といった定量ファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算（lookup 範囲にバッファを入れて週末・祝日を考慮）。
    - データ不足時の None 扱い、結果は (date, code) キーの dict リストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応、ホライズン検証あり）。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）とランク関数（rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージ __all__ に主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### 変更 (Changed)
- 設計方針・安全対策を広範に導入
  - すべての時刻参照処理で datetime.today()/date.today() によるルックアヘッドを避け、関数の引数として target_date を与える設計を採用。
  - OpenAI 呼び出しは news_nlp と regime_detector で独立実装（モジュール間結合を避ける）。
  - API 失敗時は例外を投げずフェイルセーフで継続する設計（部分結果保存、ゼロフォールバック）。ただし、API キー未指定時は ValueError を発生させ明示的に要求。

### 修正 (Fixed)
- DB 書き込みの堅牢化
  - DuckDB の executemany に関する互換性を考慮し、空パラメータでの呼び出しを回避するガードを追加（空リストの場合は実行しない）。
  - 書き込みは冪等性を意識（DELETE → INSERT の手順、calendar_update_job の ON CONFLICT を想定）。

### ドキュメント・注記 (Notes)
- OpenAI 絡み
  - gpt-4o-mini を使用し JSON Mode（response_format={"type":"json_object"}）での呼び出しを前提としているが、API レスポンスが必ずしも厳密 JSON とは限らないため、パーサで前後余計文字列から最外の {} を抽出する対応を実装。
  - API 呼び出しはテスト容易性のため _call_openai_api を patch で差し替え可能にしている。
- 環境変数の取り扱い
  - 重要な値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 経由で必須チェックを行う。未設定時は ValueError で明示。
- 互換性
  - DuckDB のバージョン差異を意識した実装（配列バインドや executemany のエッジケースに配慮）。

### 既知の制約 / 今後の改善候補
- PBR・配当利回りはバリューファクターで未実装（calc_value に注記あり）。
- news_nlp と regime_detector の LLM 呼び出しロジックが重複しているため、将来的に共通化できる可能性ありが、現状はモジュール分離を優先。
- calendar_update_job は jquants_client の実装に依存（外部 API のエラーは呼び出し元に伝播せずログ記録して 0 を返す設計）。

---

（この CHANGELOG は提供されたコードからの推測に基づいて作成しています。実際のリリースノートや運用方針に合わせて適宜修正してください。）