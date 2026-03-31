# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
日付はリポジトリ内の初期リリース相当の状態（コードベースから推測）を基にしています。

全般的な方針：
- 日付やバージョンはコード内の __version__ と現在のスナップショットに基づき設定しています。
- 記述はコード実装（モジュール、関数、設計方針、フェイルセーフなど）から推測した変更点・機能追加を反映しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース（コードベースの最初の実装相当）。以下の主要機能・モジュールを実装・追加。

### Added
- パッケージのメタ情報
  - kabusys パッケージを追加。バージョン __version__ = "0.1.0" を定義。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を想定（strategy/execution/monitoring は他ファイルで実装されていることを想定）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パース機能を実装（export プレフィックス対応、クォート内のエスケープ処理、行末コメント処理など）。
  - override / protected オプションで OS 環境変数を保護しつつ .env.local を上書き可能に。
  - Settings クラスを追加し、必須設定 (_require) を通じて以下の設定をプロパティで提供:
    - J-Quants, kabuステーション, Slack, DB パス（duckdb/sqlite）、監視閾値（CPU/MEM/DISK）、PID ファイルパス、環境（development/paper_trading/live）およびログレベル検証。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でバッチ評価する score_news を実装。
    - ニュースウィンドウ計算（JST 前日15:00〜当日08:30 に相当する UTC 範囲）を calc_news_window で提供。
    - バッチサイズ、文字数上限、記事数上限、リトライ（429/ネットワーク/タイムアウト/5xx）を備えた堅牢な API 呼び出し／再試行ロジック。
    - レスポンス検証ロジック（JSON モードの余分テキスト回復、results リスト・code/score バリデーション、数値クリップ）を実装。
    - ai_scores テーブルへ冗長のない置換（DELETE -> INSERT）を行うことで冪等性を確保。DuckDB の executemany 空リスト制約に対する対応あり。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースセンチメント（LLM、重み 30%）を合成して日次の market_regime を判定・保存する score_regime を実装。
    - prices_daily / raw_news を参照し、MA 計算・キーワードフィルタ・OpenAI 呼び出し（gpt-4o-mini）・スコア合成・冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - API 失敗時は macro_sentiment=0.0 としフェイルセーフで処理継続する設計。
    - ルックアヘッドバイアス対策（target_date 未満データのみ使用、datetime.today() を直接参照しない）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定およびユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際の曜日ベースフォールバック、DB 登録値優先の一貫性、探索上限（_MAX_SEARCH_DAYS）などの堅牢設計。
    - JPX カレンダーを J-Quants から差分取得し更新する calendar_update_job を実装（バックフィル、健全性チェック、エラーハンドリング）。
  - ETL パイプライン（kabusys.data.pipeline, etl re-export）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラーなど）を集約。
    - 差分取得・backfill・品質チェック（quality モジュール）を想定した設計（実装の骨格）。
    - jquants_client を通じたデータ取得・保存の想定。保存は idempotent（ON CONFLICT DO UPDATE）を前提。
  - etl モジュール（kabusys.data.etl）で ETLResult を再エクスポート。

- リサーチ/ファクター（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS が 0 または欠損の際は None）。
    - DuckDB のウィンドウ関数を活用し営業日ベースの窓処理を実行。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - 将来リターン（LEAD を用いたホライズン別 fwd_xd）の計算（ホライズン検証、スキャン範囲最適化）。
    - IC（Spearman の ρ）計算（ランク化、同順位の平均ランク処理）。
    - 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。

### Changed
- 設計ポリシー・実装方針を明示
  - ルックアヘッドバイアス防止のため日付参照を外部引数に依存する設計（target_date パラメータ）を採用。
  - 外部 API 呼び出しに対するフェイルセーフ（失敗時はスコア 0.0 またはスキップ）を標準化。
  - DB 書き込みにおいて冪等性・部分失敗時の既存データ保護（対象コードだけを置換）を優先。

### Fixed
- .env パーサの堅牢化
  - export 形式対応、クォート中のバックスラッシュエスケープ処理、コメント判定の改善により .env ファイルの多様な書式を許容。
- OpenAI 呼び出しの安定化
  - レートリミット・接続エラー・タイムアウト・5xx に対する再試行（指数バックオフ）を実装。
  - レスポンス JSON パース失敗時のフォールバックロジック（部分 JSON 抽出）を追加。

### Known issues / Notes
- pipeline._get_max_date の実装片に末尾の不完全なコード（"return date.fro" で切れている）が見受けられるため、その部分は修正が必要です（おそらく date を返すロジックのタイポ）。リリース前に該当箇所の補完・テストを推奨。
- jquants_client（kabusys.data.jquants_client）は参照されているが、本差分にクライアント実装が含まれているかは未確認。実運用では API クライアントの実装と認証・例外処理の確認が必要。
- __all__ に strategy, execution, monitoring が含まれているが、このスナップショットでは該当モジュールのソースを参照できないため、当該モジュールは別コミット/別ファイルで実装されている想定。未実装の場合はパッケージインポート時に ImportError になる可能性あり。
- DuckDB のバインド挙動（リストバインド、executemany の空リスト制約など）に依存する実装箇所があるため、ターゲット DuckDB バージョンでの検証が必要。

### Security
- 環境変数に依存する機密情報（OpenAI API キー、J-Quants トークン、Slack トークン等）は Settings._require により必須チェックを行う。CI / デプロイ時には適切なシークレット管理を行うこと。

---

参照:
- 各モジュール内の docstring と実装ノートに基づき機能を列挙しました。具体的な API 仕様や DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials など）はコード内コメントに依存します。