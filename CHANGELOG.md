# Changelog

すべての注記は Keep a Changelog の形式に準拠しており、重要な変更・追加点を日付順に記載しています。

フォーマット:
- 変更の種類は Added / Changed / Fixed / Security / Deprecated / Removed で分類しています。
- 初版リリース（0.1.0）はリポジトリ内のソースコードから推測して作成しています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys パッケージを初期実装。モジュール公開: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン番号を "0.1.0" に設定。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を実装。読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行う。
  - .env パーサを実装。export 記法、シングル／ダブルクォート、エスケープ、行内コメント処理に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - 必須環境変数取得ヘルパ _require() と Settings クラスを実装。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの検証を提供。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメントをスコア化。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証機構（JSON パースの復元、キー検証、型検査、スコアの有限性チェック、±1 でクリップ）。
    - 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT の置換方式で ai_scores を更新（冪等性確保）。
    - テスト用に OpenAI 呼び出しを差し替え可能（unittest.mock.patch 対応）。
    - calc_news_window() により JST ベースのニュースウィンドウ計算を提供（ルックアヘッドバイアス対策）。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）およびリトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームスコア合成ロジック、閾値指定、かつ market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - DuckDB クエリにおけるルックアヘッド回避設計（target_date 未満のデータのみ使用）。

- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照。結果は (date, code) をキーとする辞書のリストで返す。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

- Data Platform（src/kabusys/data）
  - calendar_management.py
    - market_calendar テーブルの取得・判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB にデータがなければ曜日ベースのフォールバックを使用。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job()（J-Quants API 経由で取得・保存、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数等の安全設計。
  - pipeline.py / etl.py
    - ETL パイプラインの基礎実装。差分取得・保存・品質チェックのフローに対応。
    - ETLResult データクラスを公開（etl.py で再エクスポート）。品質チェック結果の集約、エラー判定用プロパティ（has_errors, has_quality_errors）および辞書変換を提供。
    - DuckDB テーブル存在チェック、最大日付取得などのユーティリティを含む。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

### Notes / 実装上の設計方針・既知の制約
- ルックアヘッドバイアス対策: すべての分析/スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、target_date に基づいて過去データのみを参照する設計。
- OpenAI 呼び出し:
  - JSON Mode を利用する前提のためレスポンスが不正な場合の復元処理を実装（最外の {} を抽出して再パース）。
  - テスト性のために _call_openai_api をモック差替え可能にしている。
- フェイルセーフ:
  - API レベルの一時エラーやパース失敗は例外を上げずフォールバック値（例: macro_sentiment=0.0）やスキップで継続する実装。DB 書き込み失敗時のみ例外を伝播させる（トランザクションは ROLLBACK を試行）。
- DB 書き込みの冪等性:
  - ai_scores, market_regime, market_calendar の更新は既存レコードの上書きや DELETE→INSERT の方式を採用し、部分失敗時に他データを保護する設計。
- 時間・タイムゾーン:
  - news ウィンドウは JST を基準に計算し、DB 側の raw_news.datetime は UTC naive として扱う前提。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への対応を考慮して空チェックを実装。
- 環境変数パース:
  - .env パーサは複雑なクォート/エスケープ/コメントのケースに対応。ただし特殊ケースでの挙動は .env.example を参照することを推奨。

### Migration / 互換性
- 初版のため過去バージョンとの互換性考慮は不要。
- 将来のリリースで OpenAI モデル名や API クライアント仕様が変わる可能性があるため、呼び出し箇所の抽象化（モック可能な _call_openai_api）を残している。

---

今後の予定（想定）
- strategy / execution / monitoring の実装拡充（現状はパッケージ構成を露出）。
- パフォーマンス改善や追加の品質チェック、エンドツーエンドの統合テスト拡充。
- ドキュメント（Usage / Configuration / ETL 運用手順）の整備。

（以上）