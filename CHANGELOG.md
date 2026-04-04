# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記録しています。  
新しい変更は常に一番上に追加してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 追加予定
- テストカバレッジ拡充（OpenAI 呼び出し・DB 書き込み部分のモックテストの追加）
- ドキュメント（Usage / API / データベーススキーマ）の整備
- jquants_client の例外ハンドリング強化およびバックオフ設定の外部化

---

## [0.1.0] - 2026-04-04

初期リリース — 日本株自動売買 / データプラットフォーム基盤を実装。

### 追加
- パッケージ基礎
  - パッケージエントリポイントを追加 (kabusys.__version__ = 0.1.0)。
  - モジュール構成: data, research, ai, monitoring, strategy, execution（公開インターフェースでの整理）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーを独自実装（export 形式・クォート・エスケープ・インラインコメントの扱いに対応）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティとして提供。
  - 必須環境変数未設定時に明確なエラーメッセージを返す _require() を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を算出して書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で算出。
    - バッチサイズ、トリム、最大記事数等のトークン肥大対策を実装。
    - JSON Mode を想定したレスポンス検証・抽出ロジック、スコアの ±1.0 クリップ、部分書き換え（DELETE→INSERT）により冪等性と部分失敗耐性を確保。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフの実装、API失敗はフェイルセーフでスキップ。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で market_regime を算出・保存するロジックを実装。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行ロジック、API障害時は macro_sentiment=0 とするフェイルセーフを実装。
    - DB への冪等的書込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。

- データ処理（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを導入して ETL の取得・保存件数、品質問題、エラー概要を集約。
    - 差分更新（最終取得日を基に新規データのみ取得）、バックフィル、品質チェックの設計方針を反映。

  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定・次／前営業日の算出・期間内営業日一覧取得・SQ日判定のユーティリティ群を実装。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末を非営業日とする）。
    - calendar_update_job による J-Quants からの差分取得と冪等保存の実装（バックフィル・健全性チェック含む）。

  - ETL 再エクスポート（kabusys.data.etl）
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR / 相対 ATR / 平均売買代金 / 出来高比率）、Value（PER / ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時の None 扱い、結果を (date, code) ベースの dict リストで返す設計。
    - DuckDB SQL を利用しパフォーマンス考慮した窓関数等を実装。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズンのリターン）を実装。
    - calc_ic（Spearman ランク相関による IC 計算）、rank（平均ランク処理）、factor_summary（count/mean/std/min/max/median の計算）を実装。
    - pandas 等に依存しない純標準ライブラリ実装。

### 変更・設計上の注意事項
- ルックアヘッドバイアス対策:
  - AI モジュールおよびリサーチモジュールは datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡す方式を採用。
  - DB クエリは target_date より前のデータのみを参照する等、データリークを防止する実装方針。

- 耐障害性:
  - OpenAI API 呼び出しはリトライとバックオフ、非致命的失敗時はログを残してフェイルセーフ（0 やスキップ）で継続する設計。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時も警告ログで記録。

- DuckDB 互換性配慮:
  - executemany に空リストを渡さない等、DuckDB バージョン差分を考慮した実装。

### 修正
- N/A（初期リリースのため既知のバグ修正履歴はなし）

### 削除
- N/A

### 既知の制約・留意点
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要がある。未設定時は ValueError を送出する設計。
- news_nlp / regime_detector では gpt-4o-mini の JSON Mode を期待するため、モデルの挙動変更があるとパースが必要。
- 一部設計決定（閾値、重み、ウィンドウ長など）はコード内定数で固定されているため、将来的に外部設定化することが想定される。

---

（注）本 CHANGELOG は提示されたコードの実装内容から推測して作成しています。実際のリリースノートとして利用する際は、コミット履歴・差分・リリース日を確認して調整してください。