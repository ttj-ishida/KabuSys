# Changelog

すべての重要な変更はこのファイルに記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
リリース日はリポジトリ内の初期バージョン（__version__ = "0.1.0"）に合わせて記載しています。

※注意: 以下はソースコードから推測して作成したリリースノートです。実際の変更履歴が別途ある場合はそちらを優先してください。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初期公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群をまとめて導入します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージのメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開モジュールを __all__ で整理（data, strategy, execution, monitoring）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動ロードする機構を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env / .env.local の読み込み順と上書き制御（OS 環境変数保護）を導入。
  - エクスポート形式（export KEY=val）やクォート・エスケープ・コメント処理に対応した .env パーサを実装（堅牢なパース実装）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - 必須 env の取得ヘルパ `_require` と Settings クラスを提供。
  - Settings で参照される主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のいずれか）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ保存。
    - JST の「前日 15:00 〜 当日 08:30」ウィンドウ計算ロジック（UTC で扱う calc_news_window）を提供。
    - 1チャンク当たり最大 20 銘柄でバッチ送信、1銘柄あたり最大 10 記事・3000 文字でトリム。
    - JSON mode を利用した厳密なレスポンス期待、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。テストしやすいように API 呼び出し関数をモック差し替え可能に設計。
    - 部分失敗時に既存データを保護するため、書き込みは対象コードのみ DELETE → INSERT の置換を実施（DuckDB executemany の互換性考慮）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull / neutral / bear）を決定し market_regime テーブルへ冪等的に書き込む。
    - マクロニュースは news_nlp のウィンドウ集約 calc_news_window を利用して抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ動作。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、例外時は ROLLBACK を実施し上位に伝播。
- データ処理（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定（is_trading_day）、SQ 判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を実装。
    - DB 未取得時のフォールバック（曜日ベース: 土日非営業日）や、DB がまばらな場合でも一貫した判定が行える設計。
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存。バックフィルや健全性チェックを実装。
  - pipeline（ETL）
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分更新、保存（idempotent save_*）、品質チェックのフレームワーク設計。backfill 日数やカレンダー先読み等のパラメータを定義。
    - ETLResult は品質問題（quality.QualityIssue）とエラー概要を保持し、has_errors / has_quality_errors / to_dict を提供。
- リサーチ（kabusys.research）
  - factor_research
    - ファクター計算機能を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
      - calc_value: PER / ROE（raw_financials の最新報告を target_date 以前から取得して計算）
    - DuckDB 内 SQL を活用した高効率実装。欠測時の None 扱いやデータ不足時の警告を含む。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターン計算。ホライズン検証（正の整数かつ <=252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 値のランク付け（同順位は平均ランク）。浮動小数丸めで ties の検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
- モジュール公開の整理
  - 各サブパッケージの __init__ で主要 API を整理して再エクスポート（例: kabusys.ai.__all__, kabusys.research.__all__ など）。
- テスト容易性のための注記
  - OpenAI 呼び出し部分（_call_openai_api 等）は unittest.mock.patch で差し替え可能に設計。

### 変更 (Changed)
- （初期リリースのため変更履歴なし）

### 修正 (Fixed)
- （初期リリースのため修正履歴なし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーの扱いについて、api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とする設計。未設定の場合は ValueError を送出して安全に停止。

### 注記 (Notes)
- 多くの計算関数は「ルックアヘッドバイアス防止」のため datetime.today() / date.today() を参照せず、引数で与えられた target_date を基準に動作します。バックテスト / リサーチ用途での再現性が高い設計です。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定しています。API バージョンやモデルの変更に伴う互換性には注意が必要です。
- DuckDB のバージョンによる executemany の挙動やリストバインドの制約を考慮した実装（空リストハンドリング等）を行っています。
- .env パーサは一般的なシェル形式の export キーやクォート・バックスラッシュエスケープ、インラインコメント処理に対応していますが、極端に特殊な .env 構成では期待通りに動作しない可能性があります。
- 単体テストでは自動 .env ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

保持方針: 将来のリリースでは、各バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで差分を明確に記載してください。