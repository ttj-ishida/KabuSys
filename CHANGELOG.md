# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のリリース履歴はコードベースから推測して作成しています。

## [0.1.0] - 2026-03-31
初回リリース（推定）。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を含むモジュール群を追加。

### Added
- パッケージの基本エントリポイントを追加
  - src/kabusys/__init__.py: __version__ = "0.1.0"、公開サブパッケージ一覧を __all__ に定義（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py:
    - .env および .env.local ファイルからの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 高度な .env パーサー実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 必須環境変数取得用 _require、Settings クラスによる型・値チェック（J-Quants / kabu / Slack / DB パスなど）。
    - KABUSYS_ENV の検証（development/paper_trading/live）や LOG_LEVEL の検証。
- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）と記事トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - バッチ処理（1コールあたり最大20銘柄）・JSON Mode 解析・レスポンス検証・スコアクリップ。
    - エラー耐性: レート制限・ネットワーク断・5xx に対する指数バックオフリトライ、失敗時は該当チャンクをスキップして継続。
    - DuckDB（raw_news / news_symbols / ai_scores）との冪等書き込みロジック（DELETE → INSERT、部分失敗時に既存データを保護）。
    - calc_news_window、score_news を公開 API として提供。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しの独立実装、API リトライ・フェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
    - DuckDB（prices_daily / raw_news / market_regime）を参照し、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - score_regime を公開 API として提供。
- データ基盤（Data）
  - src/kabusys/data/calendar_management.py:
    - JPX 市場カレンダー管理と夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar 未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した挙動、探索上限（日数制限）を実装。
    - J-Quants クライアント経由の差分取得・バックフィル・健全性チェックを含む。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの結果を表現する ETLResult データクラスを追加（取得数・保存数・品質チェック結果・エラー集計など）。
    - 差分更新、バックフィル、品質チェックを想定した設計（_MIN_DATA_DATE、_DEFAULT_BACKFILL_DAYS 等の定数あり）。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult の再エクスポートを追加（外部向け API）。
- リサーチ（Research）
  - src/kabusys/research/factor_research.py:
    - Momentum（1M/3M/6M・MA200乖離）、Volatility（20日ATR, ATR比率）、Value（PER, ROE）等のファクター計算関数を追加（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。データ不足時は None を返す設計。
    - 設計上、本番 API へはアクセスしない（prices_daily / raw_financials のみ参照）。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、rank、ファクター統計サマリー（factor_summary）を追加。
    - pandas 等外部依存を排し、純粋に標準ライブラリと DuckDB で実装。
- その他
  - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py による公開 API の整理。
  - DuckDB を前提とした多くのユーティリティ関数で date オブジェクトを厳密に扱う（タイムゾーン混入回避）。

### Changed
(初回リリースに伴う初期実装のため該当なし)

### Fixed
(初回リリースに伴う初期実装のため該当なし)

### Security
- 環境変数の取り扱い:
  - 自動 .env ロード時に OS 環境変数を保護する機構（protected set）を導入。override=True の場合でも OS 環境変数は上書きされない。
  - OpenAI API キーは関数引数で注入可能（テスト容易性）かつ、渡されない場合は環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を発生させる設計。

### Notes / Design decisions
- ルックアヘッドバイアス防止:
  - AI モジュール・リサーチ関数ともに datetime.today()/date.today() を直接参照しない設計。全て target_date を明示的に受け取ることでバックテストでのリークを防止。
- フォールバック / フェイルセーフ:
  - OpenAI や外部 API 呼び出し失敗時は例外を全体に拡散させず、部分的にフォールバック（例: macro_sentiment=0.0、チャンクスキップ）することで ETL/スコアリングの継続性を重視。
- 冪等性:
  - DB 書き込みは DELETE + INSERT または ON CONFLICT 相当で冪等性を担保。部分失敗時に既存データを不必要に消さないよう配慮。
- DuckDB 互換性:
  - executemany の空引数回避やリスト型バインドのバージョン差対策など、DuckDB の実装差を考慮した実装。

### Public API（主な公開関数 / クラス）
- kabusys.config.settings (Settings)
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.data.ETLResult (pipeline.ETLResult 再エクスポート)
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ に列挙）

---

今後のリリースでは、以下のような項目が想定されます:
- strategy / execution / monitoring サブパッケージの具体的な実装追加（バックテスト、発注ラッパー、モニタリング）
- ai モデルの切替やプロンプト最適化、より詳細なレスポンス検証
- ETL パイプラインのスケジューラ統合や品質チェック強化（quality モジュールとの連携拡張）
- ドキュメント（API リファレンス・設計ドキュメント）とユニットテストの整備

（この CHANGELOG は提供されたコードベースの内容に基づいて推測して作成しています。実際のリリースノート作成時はコミット履歴・変更差分を参考に正確な記載を行ってください。）