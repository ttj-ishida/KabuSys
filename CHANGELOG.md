# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実装の設計方針やログ出力、フェイルセーフ動作などもドキュメントやコードコメントを元に要約しています。

## [Unreleased]

- 次回リリースに向けた未実装・改善候補（参考）
  - pipeline._get_max_date の実装途中と思われる箇所の修正
  - テストカバレッジ強化（外部APIモック、DuckDBの互換性テスト等）
  - ドキュメント化（Usage examples、API surfaceの詳細）

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システムのコアライブラリ群を実装・公開。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パブリックモジュールエクスポート: data, strategy, execution, monitoring。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード順序: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（クォート処理、export プレフィックス、行内コメントの取り扱いを考慮）。
  - 保護された OS 環境変数を上書きしない仕組み（protected set）。
  - 必須キー取得時に未設定で ValueError を送出する _require()。
  - 各種設定プロパティ: J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）/監視閾値/環境・ログレベル判定メソッド（is_live / is_paper / is_dev）。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント: score_news（src/kabusys/ai/news_nlp.py）
    - raw_news, news_symbols を集約して銘柄毎に OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（1回最大20銘柄）、1銘柄あたり記事数・文字数のトリム(_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - JSON Mode を使った堅牢なレスポンス処理とバリデーション（余計な前後テキストの復元処理を含む）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - DuckDB 互換性を考慮した書き込みロジック（部分成功を許容する DELETE→INSERT 方針、executemany 空リスト回避）。
    - ルックアヘッドバイアス防止のため、内部で date.today() を参照しない設計（target_date パラメータ指定）。
    - テスト時に差し替え可能な _call_openai_api フックを用意。

  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出は内部キーワードリストでフィルタ（日本・米国関連主要ワードを含む）。
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出、API失敗時はフェイルセーフで 0.0 を使用。
    - レジームのスコア・ラベル・ma200_ratio・macro_sentiment を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計（news_nlp と共有しない）。

- Research / ファクター分析 (src/kabusys/research)
  - ファクター計算エントリーポイント（__init__）: zscore_normalize の再エクスポート、calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank を公開。
  - calc_momentum
    - 1M/3M/6M リターン、200日MA乖離(ma200_dev) を DuckDB SQL により高速算出。
    - データ不足時は None を返す設計。
  - calc_volatility
    - 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比(volume_ratio) を算出。
    - true_range の NULL伝播を考慮して精密に計算。
  - calc_value
    - raw_financials から最新の財務データを取得し PER / ROE を算出（EPS が 0/欠損の場合は None）。
  - feature_exploration
    - calc_forward_returns: 指定日以降の各ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。
    - rank: 同順位は平均ランクを返す実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。

- Data プラットフォーム（DuckDB ベース） (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジックの提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DBにデータがある場合は DB 値を優先し、未登録日は曜日ベースでフォールバック（週末を休場扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新する夜間バッチ処理（バックフィルや健全性チェックあり）。
  - ETL パイプライン骨格 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分取得の基本方針、バックフィル挙動、品質チェック（quality モジュール）との連携を想定した構成。
    - jquants_client と連携して idempotent に保存する想定（save_* 関数呼び出し）。

- 互換性・実装上の配慮
  - DuckDB を主要な一時的/恒久的ストレージとして想定し、SQL ウィンドウ関数や executemany の互換性を考慮。
  - OpenAI SDK エラー型（RateLimitError / APIConnectionError / APITimeoutError / APIError）を考慮した細かなエラー処理。
  - LLM 呼び出しのリトライ/バックオフ、JSONパース失敗時のフォールバックを明確化。
  - 外部に副作用を与える処理（API呼び出し・DB書き込み等）については冪等性を重視（DELETE→INSERT や ON CONFLICT の想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（protected set）。  
- OpenAI API キーなど機密情報は Settings._require により必須チェックを行い、未設定時は明示的にエラーにする設計。

### Known issues / Notes
- pipeline._get_max_date の末尾が不完全（コード断片 "return date.fro" で終わっている）ため、該当関数の完成・検証が必要です。リリース前に修正が必要と推測されます。
- 一部モジュールは jquants_client や quality モジュールに依存するため、外部依存のスタブ/モックを用いたテストが必要です。
- news_nlp / regime_detector の OpenAI 呼び出しは JSON Mode を利用する想定だが、実運用ではモデル仕様やレスポンス形式の変化に注意。
- DuckDB のバージョン差異（executemany の空リスト取り扱いなど）を考慮した実装になっているため、運用時は対象環境の DuckDB バージョンでの動作確認を推奨。

---

作成者: 自動生成（コードベース解析による推測）