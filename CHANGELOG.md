# CHANGELOG

すべての注目すべき変更はここに記載します。  
このプロジェクトは Keep a Changelog の規約に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

### Added
- 初回公開リリース。パッケージ名: kabusys, バージョン 0.1.0。
- パッケージ公開インターフェースを追加:
  - src/kabusys/__init__.py にて version とサブパッケージ（data, research, ai, など）の公開設定。
- 環境設定管理:
  - src/kabusys/config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml）を実装し、.env / .env.local の自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース機能実装（export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープ、行内コメントの取り扱い等）。
    - 環境変数の保護（OS環境変数を protected として .env.local で上書きされないよう扱う）。
    - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / ログ・環境のバリデーションを含む）。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。

- AI モジュール（OpenAI を用いた NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、gpt-4o-mini（JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチ処理（1回最大20銘柄）、トークン肥大対策（記事数・文字数制限）、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出・results 構造チェック・スコアのクリップ）を実装。
    - DuckDB への冪等書き込み（DELETE→INSERT、executemany の空リスト回避）を実装。
    - ルックアヘッドバイアス回避設計（target_date 依存、datetime.today() を参照しない）。
    - テスト向けに _call_openai_api を差し替え可能な実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）、スコア合成とクリッピング、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - news_nlp の内部関数と意図的に分離された _call_openai_api を用意（モジュール結合の抑制）。

- Research（ファクター計算・特徴量解析）:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の取り扱い（必要行数未満は None を返す）や、SQL ウィンドウ関数を用いた実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出（calc_forward_returns、任意ホライズン対応・入力検証あり）、IC（Information Coefficient）計算（calc_ic、Spearman ランク相関）、ランク関数（rank、同順位は平均ランク）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

- Data（データ取得 / カレンダー / ETL）:
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル参照）。
    - 営業日判定・前後営業日の取得・期間内営業日リスト取得・SQ 日判定の API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未登録時は曜日ベースのフォールバックを一貫して使用。
    - calendar_update_job: J-Quants クライアント経由で差分取得 → 冪等保存、バックフィル・健全性チェック実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプライン用の ETLResult dataclass とユーティリティ（差分更新、バックフィル、品質チェックの統合フレームワーク設計）。
    - _get_max_date 等のヘルパー関数を備え、J-Quants クライアントや quality モジュールとの連携を想定。
    - etl.py で ETLResult を再エクスポート。
  - 共通設計:
    - DuckDB を前提にした SQL ベースの処理、冪等保存、トランザクションとロールバックの取り扱い。

- パッケージ構成:
  - ai, data, research サブパッケージや公開関数（news_nlp.score_news, ai.regime_detector.score_regime 等）を整理して公開。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- API キー未設定時に明確な ValueError を送出することで、安全に失敗する挙動を明示（OpenAI 関連、Settings の必須キー）。
- .env の読み込みで OS 環境変数を保護する挙動を実装（.env.local の override にも配慮）。

### Notes / Implementation details
- OpenAI の呼び出しは gpt-4o-mini を想定し、JSON モードでの厳密な JSON 出力を期待する。ただしレスポンスパース失敗や API エラー時はフォールバック（スコア 0.0 など）して処理を継続する設計。
- ルックアヘッドバイアスを防ぐ設計方針を一貫して採用（target_date に依存、datetime.today() を直接参照しない）。
- DuckDB のバージョン差異（executemany の空リスト制約、リスト型バインドの互換性）に配慮した実装がある。
- テスト容易性のため、OpenAI 呼び出し部分（内部の _call_openai_api）を unittest.mock.patch 等で差し替え可能な設計になっている。
- jquants_client、quality モジュール等の外部クライアントは本コードベースでは参照されるが、実装は別モジュールとして分離される想定。

---

### Breaking Changes
- なし（初回リリースのため）。

---

開発・運用の都合により CHANGELOG を更新してください。