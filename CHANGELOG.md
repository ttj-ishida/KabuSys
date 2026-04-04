# Changelog

すべての注目すべき変更履歴を記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

なお、本リリースはパッケージの最初の公開バージョン (0.1.0) をコードベースから推測してまとめた内容です。

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、トップレベルエクスポート: data, strategy, execution, monitoring を公開。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - シンプルだが堅牢な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ対応）。
  - 環境変数の保護（OS 環境変数を protected として上書き防止）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等の取得ロジックを集中管理。
  - 必須環境変数未設定時は明示的な ValueError を発生させるユーティリティを提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、銘柄ごとに前日15:00 JST〜当日08:30 JST のニュースウィンドウを対象に OpenAI（gpt-4o-mini）でセンチメントを算出。
  - バッチ処理（1回あたり最大20銘柄）、1銘柄あたり記事数・文字数の上限トリム、JSON モード応答のバリデーションを実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、致命的でない失敗時はスキップして継続するフェイルセーフ。
  - レスポンスパースの耐性（前後に余計なテキストが混入した場合の最外殻 JSON 抽出等）、スコアを ±1.0 にクリップ。
  - スコアは ai_scores テーブルへ「部分的置換（該当 code の DELETE → INSERT）」で書き込み。部分失敗時に他コードを保護する設計。
  - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch できる）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
  - マクロキーワードで raw_news タイトルをフィルタして LLM に渡す。記事なし、または API 問題時は macro_sentiment=0 にフォールバック。
  - OpenAI（gpt-4o-mini）呼び出しは独立実装。API リトライ・バックオフや 5xx の扱いを実装。
  - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。

- データプラットフォーム機能（src/kabusys/data/*）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー一覧等を含む）。
    - 差分更新、バックフィル、品質チェックを想定した設計（J-Quants クライアント経由で取得し idempotent に保存）。
  - ETL 公開インターフェースとして ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定（is_trading_day）、翌営業日/前営業日の取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ 日判定（is_sq_day）を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した動作。探索範囲の上限を設定して無限ループを防止。
    - calendar_update_job により J-Quants からカレンダーを差分取得して保存。バックフィルと健全性チェックを実装。

- リサーチ機能（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）計算。データ不足時の None 扱い。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - Value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0 或いは欠損時は None）。
    - いずれも DuckDB 上の SQL ウィンドウ関数を活用し、外部 API に依存しない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）：任意ホライズンに対する fwd_xd を計算。horizons のバリデーションあり。
    - IC（calc_ic）: ファクターと将来リターンのスピアマンランク相関を計算。有効レコードが少ない場合は None を返す。
    - ランク関数（rank）: 同順位は平均ランクで処理（丸めによる ties 対応）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの再エクスポートを用意（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

- DuckDB を中心としたデータ操作
  - 主要処理は DuckDB 接続を受け取り SQL と Python の組合せで完結する設計。パフォーマンスと一貫性を重視。

### Design / Reliability Notes
- ルックアヘッドバイアス防止
  - AI スコアリング・レジーム判定・ファクター計算等、いずれも内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計。DB クエリにも date < target_date / date BETWEEN を用いることでルックアヘッドを回避。
- 冪等性と部分失敗耐性
  - AI スコア / レジーム / カレンダーの DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 等）を意識。部分失敗時に既存データを不用意に消さないよう設計。
- API 呼び出しの堅牢化
  - OpenAI（gpt-4o-mini）呼び出しはタイムアウト・レート制限・5xx に対するリトライ（指数バックオフ）を実装。最終的に失敗した場合はスコアに安全なデフォルト（0.0）を使うか、該当チャンクをスキップして処理を継続。
- テスト性
  - OpenAI 呼び出しポイントは内部関数（_call_openai_api）を経由しており、unittest.mock.patch により差し替え可能。DB 周りも明示的な接続引き渡しでテスト容易性を考慮。

### Removed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させ明示的に扱う。

---

注記:
- 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートは開発者が意図した変更点や既知の制約を反映して適宜調整してください。