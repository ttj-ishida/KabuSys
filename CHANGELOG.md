# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※この履歴は与えられたコードベースからの推測に基づいて作成しています。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 基本パッケージ初期リリースを追加。
  - パッケージ名: kabusys、バージョン 0.1.0。
- 環境設定/ロード機能を実装（kabusys.config）。
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パーサは export 形式、クォート付き値、インラインコメント、エスケープシーケンスに対応。
  - 環境変数必須チェック用の _require と、アプリ設定を表す Settings クラスを公開。J-Quants、kabuステーション、LINE、DBパス、監視パラメータ、実行環境（development/paper_trading/live）などのプロパティを提供。
  - 設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の検査）と便利判定プロパティ（is_live / is_paper / is_dev）。

- AI 関連モジュールを追加（kabusys.ai）。
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数上限・文字数上限を導入（トークン肥大対策）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーションと部分失敗時のフェイルセーフ（失敗銘柄はスキップ、他銘柄は保護）。
    - ai_scores テーブルへの冪等更新ロジック（DELETE → INSERT、DuckDBの executemany 空リスト回避）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンス（{"macro_sentiment": ...}）を期待。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。
    - テスト用に _call_openai_api の差し替えを想定。

- Data（データ基盤）モジュールを追加（kabusys.data）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）に基づく営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データがない場合は曜日ベースのフォールバック（週末を非営業日）。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・冪等保存を行う。バックフィル、健全性チェック（過度の未来日付スキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー等を追跡）。to_dict により品質問題を辞書化。
    - 差分更新、バックフィル、品質チェック統合を想定した設計。J-Quants クライアントと quality モジュールを利用する構造。
  - etl モジュールで ETLResult を再エクスポート。

- Research（研究）モジュールを追加（kabusys.research）。
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、出来高/売買代金の流動性指標、財務ベースの PER / ROE を計算する関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials のみ参照。
    - データ不足時の None ハンドリング。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意のホライズンをサポート）、IC（calc_ic、Spearman の ρ）、rank（同順位は平均ランク処理）、factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB で実装。
  - research パッケージの __all__ で主要関数を公開。

- 共通実装・設計/運用上の工夫
  - DuckDB を主要なローカル分析用 DB として採用。
  - 全モジュールでルックアヘッドバイアス回避設計（datetime.today()/date.today() を内部で参照しない、呼び出し側が target_date を供給）。
  - OpenAI 呼び出しのリトライ戦略・エラー分類（429/ネットワーク/タイムアウト/5xx を再試行、その他はスキップ）を統一的に実装。
  - API 呼び出しのテスト容易性を考慮し、呼び出し関数を差し替え可能に設計。
  - DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT 等）し、部分失敗時に既存データを保護。

### 変更 (Changed)
- 初版につき過去バージョンからの変更はなし（新規導入）。

### 修正 (Fixed)
- 初版につき修正履歴はなし（新規導入）。

### 廃止 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI / J-Quants 等の外部 API キーは環境変数（OPENAI_API_KEY 等）で管理。キー未設定時は明示的に ValueError を発生させる旨の動作を実装。
- .env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制限・注意事項
- OpenAI API（gpt-4o-mini）や J-Quants API に依存するため、実行には各種 API キーとネットワーク接続が必要。
- news_nlp と regime_detector の JSON パースは堅牢化されているが、LLM の非構造化出力に対しては部分スキップとなる設計（失敗時はスコア 0.0 や該当銘柄スキップ）。
- calc_value は現状 PER, ROE のみ実装。PBR・配当利回り等は未実装。
- DuckDB のバージョン差異（executemany の空リスト取り扱い等）を想定した回避コードが含まれるが、運用環境の DuckDB バージョンによっては追加調整が必要となる場合がある。
- 一部内部関数（例: _call_openai_api）の差し替えはテスト向けを想定しているため、モック/パッチの設定が必要。

---

初期リリース（0.1.0）では、データ収集・前処理（ETL/カレンダー）、ファクター計算、ニュースを用いた AI スコアリング、および市場レジーム判定までの一連の機能基盤を実装しました。今後は運用で得られた要件に応じ、指標の拡張、改善、テストカバレッジ強化、UI/CLI や実行スケジューラとの統合を予定しています。