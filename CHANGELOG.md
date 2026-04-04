# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の指針に従っています。  

※この CHANGELOG はソースコードから機能・設計方針を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回公開リリース — 基本的なデータ基盤・リサーチ・AI スコアリング機能を実装。

### 追加 (Added)
- パッケージ基本構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - 公開モジュール（パッケージ API）に data / strategy / execution / monitoring を想定（__all__ にて公開）。
- 環境設定管理 (kabusys.config)
  - プロジェクトルートの自動検出（.git または pyproject.toml 基準）を行い、.env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーが export KEY=val 形式、クォート文字列（エスケープ考慮）、行内コメントルール等に対応。
  - 環境変数必須チェック用の _require() と Settings クラスを提供。J-Quants / kabuステーション / LINE / DB /監視 関連の設定プロパティを公開（デフォルト値を含む）。
  - KABUSYS_ENV 値検証（development / paper_trading / live）や LOG_LEVEL の検証を実装。
- ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI (gpt-4o-mini) の JSON モードでバッチ評価。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で算出。
  - 1 銘柄あたりの記事数・文字数上限、チャンク単位（最大 20 銘柄）での API コール、JSON バリデーション、スコア ±1 にクリップ。
  - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライを実装。失敗時は個別チャンクをスキップして処理継続するフェイルセーフ設計。
  - 書き込みはトランザクションで実行（DELETE → INSERT、部分失敗時に既存スコアを保護するため該当コードのみ置換）。
  - テスト容易性のため OpenAI 呼び出し部分は _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - マクロニュース抽出のキーワードセット、OpenAI 呼び出し、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
  - レジームスコア合成・閾値判定・market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- リサーチ機能 (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials を参照してモメンタム・バリュー・ボラティリティを算出。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（基本統計）を実装。
  - DuckDB 上の SQL + Python で完結する実装、外部ライブラリに依存しない設計。
- データ基盤ユーティリティ (kabusys.data)
  - calendar_management: market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と、J-Quants からの夜間バッチ更新 job（calendar_update_job）を実装。DB 未取得時は曜日ベースのフォールバックあり。
  - pipeline / etl: ETLResult データクラスを公開。差分更新・バックフィル・品質チェック設計（quality モジュールと連携）を想定する ETL パイプライン骨格を実装。
  - jquants_client 経由での取得・保存処理（差分取得・冪等保存）を想定。
- DB とトランザクション設計
  - DuckDB を主要な一時・分析 DB として利用。テーブル書き換え時は明示的に BEGIN/COMMIT/ROLLBACK を使用して安全性を確保。
  - DuckDB の executemany に関する注意（空リスト不可）に対する防護実装あり。

### 変更 (Changed)
- 設計上の基本方針（プロジェクト横断的）
  - すべての「日付ベース」処理で datetime.today()/date.today() を直接参照しない方針を採用（ルックアヘッドバイアス防止）。関数は target_date を受け取りその範囲のデータのみを参照する。
  - LLM 呼び出しの堅牢化：API の一時的障害をリトライ＋ログで扱い、最終的にフェイルセーフ値（0.0 等）へフォールバックする設計。
  - テスト容易性のため外部呼び出し点（OpenAI API 呼び出し等）は差し替え可能（モック可能）に実装。

### 修正 (Fixed)
- DB 操作・エラー処理の堅牢化
  - トランザクション失敗時に ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告ログを出すように実装。
  - DuckDB 互換性考慮（executemany の空パラメータ回避、配列バインド不安定性回避）を実装。
- .env 読み込み時の I/O エラーを warnings.warn で通知して処理継続するように実装。

### 注記 / 既知の設計選択
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出して呼び出し側へ明確に通知する設計（api_key 引数または環境変数 OPENAI_API_KEY が必須）。
- LLM のレスポンスは JSON モードを期待するが、稀に余計な前後テキストが混入するケースに備えて復元ロジック（最外側の {} を抽出）を実装している。
- market_calendar がまばら（部分登録）の場合でも next_trading_day / prev_trading_day / get_trading_days が一貫した結果を返すよう DB 値優先・未登録は曜日フォールバックのルールを採用。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計（結合度低減）。
- 現時点では一部外部依存やモジュール（例: monitoring, strategy, execution 内部実装）の実装がパッケージ公開 API に示唆されているが、CHANGELOG は現行ソースに基づく機能を中心に記述。

---

今後のリリースでは以下のような追記・改善が想定されます:
- strategy / execution / monitoring の実装（発注・監視ランナー等）の追加
- テストカバレッジ拡充・ユニットテスト向けのモックユーティリティ
- パフォーマンス改善（DuckDB クエリ最適化、バッチ設計の改善）
- セキュリティ周りのドキュメント（機密情報の取り扱い、トークン回転など）

もし特定の変更点（例えばコミット履歴や差分）からより詳細な CHANGELOG を生成したい場合は、その差分やバージョンごとのソース一覧を提供してください。