# Changelog

すべての注目すべき変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース指標:
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py に定義)
- 初期リリース日: 2026-04-02

## [Unreleased]
- なし

## [0.1.0] - 2026-04-02

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開: モジュール群（data, research, ai, config, など）の骨格と主要機能を実装。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export 形式、クォート文字列、エスケープ、インラインコメントの扱いを考慮）。
  - 環境変数保護機構: OS 環境変数（起動時の既存キー）を protected として上書きから保護。
  - Settings クラスでアプリ設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb/sqlite）/監視閾値/システム環境（env, log_level）等を提供。
  - 入力バリデーション: KABUSYS_ENV, LOG_LEVEL の許可値チェック、必須変数未設定時は ValueError。

- AI（ニュースNLP・レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成。
    - OpenAI（gpt-4o-mini）へのバッチ送信によるセンチメント推定（JSON mode）を実装。
    - バッチ処理・チャンクサイズ管理（デフォルト _BATCH_SIZE=20）。
    - 1銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - 再試行・指数バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）。リトライ上限あり。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証、スコアの有限性確認）。
    - スコアは ±1.0 にクリップ。ai_scores テーブルへの冪等的書き換え（DELETE → INSERT）を実装。
    - ルックアヘッドバイアス対策: datetime.today() 非依存、target_date ベースの時間ウィンドウ（JST 前日15:00〜当日08:30）を calc_news_window 関数で定義。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを回避。
    - マクロ記事抽出はタイトルにマクロキーワードを含む記事を選択（最大 _MAX_MACRO_ARTICLES）。
    - OpenAI 呼び出し（gpt-4o-mini）で JSON の {"macro_sentiment": float} を期待、API エラー時はフェイルセーフで macro_sentiment=0.0。
    - 合成スコアはクリップされ閾値によりラベル付け。market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出し関数は独立実装でモジュール間の密結合を避ける。

- Data / ETL / カレンダー（src/kabusys/data/*）
  - ETL 基盤（pipeline, etl）
    - ETLResult dataclass を公開し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を一元管理可能に。
    - pipeline モジュールの ETLResult を再エクスポート（kabusys.data.etl）。
    - ETL の設計方針、差分更新・バックフィル・品質チェックの骨格を実装（外部 jquants_client と quality モジュールを利用）。

  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar を基に営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが無い場合は曜日ベースのフォールバック（平日を営業日扱い）。
    - next/prev_trading_day は最大探索範囲を制限（_MAX_SEARCH_DAYS）して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
    - 市場カレンダーが部分的にしかない場合でも一貫した結果を返す設計。

- Research（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性指標（20日平均売買代金、出来高比率）などのファクター計算を実装。
    - DuckDB の window 関数を用いて効率的に計算。データ不足時は None を返す設計。
    - calc_momentum, calc_volatility, calc_value を提供。

  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）について LEAD を使って1クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：スピアマン ρ をランクを使って算出、記述的統計・欠損処理含む。
    - ランク化ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- .env 読み込み時に既存 OS 環境変数を保護する仕組みを導入（protected set）。自動ロードを無効化するフラグを用意してテスト時のキー漏洩リスクを低減。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI モジュール・ETL・research のすべてで datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計を採用。
- OpenAI 連携:
  - gpt-4o-mini を想定し、JSON Mode を利用して厳密な JSON レスポンスを期待。それでもパース失敗に備えた復元ロジックやフォールバック値を実装。
  - リトライと指数バックオフを実装し一時的な障害に耐性を持たせている。
- データベース操作:
  - DuckDB を前提とした実装（SQL + window 関数活用）。executemany の空リスト問題（DuckDB 0.10）を考慮したガードあり。
  - テーブル書き込みは冪等性を重視（DELETE → INSERT、あるいは ON CONFLICT 相当を利用する設計）。
- フェイルセーフ設計:
  - LLM や外部 API の失敗は例外を上位に投げず、当該スコアはスキップまたは中立値（0.0/1.0）で継続する箇所がある（運用上の安全重視）。
- 既知の未実装 / 制約:
  - 一部モジュール（例えばパッケージの strategy, execution, monitoring の実体）は今回のスナップショットに含まれている名前空間に対して実装の骨格があるが、完全な実装は別途提供される想定。
  - jquants_client, quality 等の外部依存モジュールは本コード内で利用しているが、実際の API クライアント実装や外部サービスの挙動に依存するため、運用時はそれらの設定とテストが必要。

---

この CHANGELOG はコードベースから推測して作成した初期リリースの要約です。実際の変更履歴やリリース日付はリポジトリのコミット履歴・リリースノートに合わせて更新してください。