# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

最初のリリース。日本株自動売買／研究プラットフォームのコア機能群を実装しています。設計方針として「ルックアヘッドバイアスを避ける」「DB への冪等書き込み」「外部 API 呼び出し時のフォールバック/フェイルセーフ」「DuckDB を中心としたオフライン分析」を重視しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0、公開モジュールの __all__ を定義）。
- 設定管理
  - 環境変数/.env 読み込みユーティリティ（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の優先度と上書きルール（OS 環境変数保護）。
    - export プレフィックス、クォート処理、インラインコメントなどを考慮した .env パース実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数未設定時に明確なエラーメッセージを出す _require 関数。
    - 各種設定プロパティ（J-Quants トークン、kabu API、Slack、データベースパス、監視閾値、環境判定等）。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を利用して銘柄毎のセンチメントスコアを ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数制限（デグロース対策）。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。その他エラーはスキップしてフェイルセーフで継続。
    - レスポンスの厳格なバリデーション（JSON 抽出・results リスト・code/score の検証・数値チェック）と ±1.0 でのクリップ。
    - JST ベースのニュース収集ウィンドウ計算（calc_news_window）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードリスト）・OpenAI 呼び出し（gpt-4o-mini）・リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - ルックアヘッド防止のため target_date 未満のみ参照する設計。
- データモジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの優先利用、未取得日は曜日ベースのフォールバック（週末除外）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日ユーティリティ。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを定義して ETL の集計結果・品質問題・エラーを構造化して返却。
    - 差分取得・バックフィル・品質チェックを行う設計方針（jquants_client を利用した保存処理を想定）。
  - ETL の公開インターフェース（etl モジュール）で ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）を DuckDB 上で計算。
    - データ不足時は None を返す等の堅牢化。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応、ホライズン検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランクは同順位を平均ランクへ）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median の算出。
    - ユーティリティ rank 関数。
- ドキュメントと設計注釈
  - 各モジュールに詳細な docstring と設計方針（ルックアヘッド防止・冪等性・フェイルセーフ等）を記載。

### Fixed / Robustness
- 外部 API 呼び出しに対する堅牢性向上
  - OpenAI 呼び出しのリトライ戦略（429/ネットワーク/タイムアウト/5xx）と、失敗時の安全なフォールバック（多くの場合スコア 0.0 を使用）。
  - JSON パース失敗時の復元ロジック（最外側の {} を抽出して復元を試みる）。
- DB 書き込みの冪等化
  - market_regime / ai_scores などへの書き込みは DELETE→INSERT または ON CONFLICT 相当の挙動で部分失敗時に既存データを不要に消さない実装。
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメントの取り扱い等に対応。

### Security
- 必須の機密情報（OpenAI API キー、J-Quants / kabu API のトークン等）は Settings 経由で必須チェックを行い、未設定時には明示的に ValueError を発生させる。
- OS 環境変数を保護するため .env ロード時に既存の環境変数を保護するオプションを実装。

### Known limitations / Notes
- DuckDB を前提としている（接続オブジェクトは duckdb.DuckDBPyConnection 型想定）。
- OpenAI との統合は gpt-4o-mini を想定している。API のレスポンスフォーマットや SDK の仕様変更に依存する箇所は将来の影響を受け得る（例: APIError の status_code の扱いを防御的に実装済み）。
- 一部の ETL / jquants_client / quality モジュールの具体的実装（API クライアントや保存処理の内部）はこのリリースで参照される設計に基づいており、外部実装に依存する。
- 現時点で PBR や配当利回りなどの一部ファクターは未実装（calc_value の注記参照）。
- DuckDB の executemany に空リストを渡せない制約を考慮した実装がある（互換性対応）。

---

今後の予定（例）
- モデルやプロンプト改善、LLM 呼び出しの抽象化によるテスト性向上
- 追加ファクター（PBR、配当利回り等）、ファクター合成ロジック
- jquants_client の具象実装／テストヘルパーの整備
- モニタリング・アラートの強化（Slack 通知等）の正式実装

（以上）